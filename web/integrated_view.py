"""시스템 통합정보 화면.

좌측 트리에서 선택한 마스터(구성정보/서비스/담당자/컴포넌트)의 컬럼·속성을 조합해
개인화된 통합 View를 만들어 보여준다.

설계 원칙
- 보안: 로그인 필요. 엑셀 export는 staff 권한자만 허용. 화이트리스트 메타에 등록된
  field_id 만 허용해 임의 컬럼 노출/필터를 차단.
- 성능: select_related/prefetch_related 적용. 조회 결과는 페이징 없이 전체 반환.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from typing import Any, Callable

import pandas as pd
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q, QuerySet
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from masters.models import (
    AttributeCode,
    Component,
    ConfigurationAttribute,
    ConfigurationComponentMapping,
    ConfigurationMaster,
    PersonMaster,
    ServiceAttribute,
    ServiceConfigurationMapping,
    ServiceMaster,
)
from web.models import IntegratedViewPreset
from web.views import normalize_service_search_key
from masters.service_person_grid import (
    SERVICE_DUTY_ATTRIBUTE_CODE,
    SERVICE_DUTY_ATTRIBUTE_LABEL,
    SERVICE_PERSON_GRID_COLUMNS,
)

# 서비스 마스터 검색과 동일한 `키:값` 토큰 + `키=값` 지원 (값은 공백 없는 토큰)
INTEGRATED_TERM_PATTERN = re.compile(r"([^\s:=][^:=]*?)\s*(?:[:=])\s*([^\s]+)")
TEXT_FILTER_SLOT_COUNT = 5


# 서비스의 역할 슬롯 ServiceAttribute attribute_code 집합 (값이 PersonMaster.pk CSV)
SERVICE_PERSON_ATTRIBUTE_CODES: set[str] = {c["attribute_code"] for c in SERVICE_PERSON_GRID_COLUMNS}
_SERVICE_PERSON_LABEL_BY_CODE: dict[str, str] = {c["attribute_code"]: c["label"] for c in SERVICE_PERSON_GRID_COLUMNS}
_SERVICE_ATTR_LABEL_OVERRIDE: dict[str, str] = {SERVICE_DUTY_ATTRIBUTE_CODE: SERVICE_DUTY_ATTRIBUTE_LABEL}
_SERVICE_PERSON_ORDER: list[str] = [c["attribute_code"] for c in SERVICE_PERSON_GRID_COLUMNS]


def _canonical_service_person_field_order(selected_fields: list[FieldDef]) -> list[FieldDef]:
    """선택 필드 중 서비스 속성: 담당현업 → 담당자 4종 순으로 한 덩어리로 묶어 정렬."""
    duty_fs = {
        f
        for f in selected_fields
        if f.group == "service" and f.source == "attribute" and f.attribute_code == SERVICE_DUTY_ATTRIBUTE_CODE
    }
    person_set = {
        f
        for f in selected_fields
        if f.group == "service" and f.source == "attribute" and f.attribute_code in SERVICE_PERSON_ATTRIBUTE_CODES
    }
    if not duty_fs and not person_set:
        return selected_fields
    by_code = {f.attribute_code: f for f in person_set}
    persons_sorted = [by_code[c] for c in _SERVICE_PERSON_ORDER if c in by_code]
    duty_sorted = sorted(duty_fs, key=lambda f: f.attribute_code)
    special = duty_fs | person_set
    first_special_idx = next(i for i, f in enumerate(selected_fields) if f in special)
    out: list[FieldDef] = []
    for i, f in enumerate(selected_fields):
        if i == first_special_idx:
            out.extend(duty_sorted)
            out.extend(persons_sorted)
        if f not in special:
            out.append(f)
    return out


# 그룹 키 → (라벨, base 모델). 화면 트리 순서.
GROUPS: list[tuple[str, str]] = [
    ("configuration", "구성정보"),
    ("service", "서비스"),
    ("person", "담당자"),
    ("component", "컴포넌트"),
]


@dataclass(frozen=True)
class FieldDef:
    field_id: str  # 예: service.name
    group: str  # service|configuration|component|person
    label: str  # 화면 표시 라벨
    data_type: str  # string|code|number|date|version|bool|text
    source: str  # column|attribute
    accessor: str = ""  # ORM lookup (column일 때)
    attribute_code: str = ""  # 속성 코드 (source==attribute일 때)


def _fk_code_field(group: str, attr: str, label: str) -> FieldDef:
    return FieldDef(
        field_id=f"{group}.{attr}",
        group=group,
        label=label,
        data_type="code",
        source="column",
        accessor=f"{attr}__name",
    )


def _str_field(group: str, attr: str, label: str, data_type: str = "string") -> FieldDef:
    return FieldDef(
        field_id=f"{group}.{attr}",
        group=group,
        label=label,
        data_type=data_type,
        source="column",
        accessor=attr,
    )


def _date_field(group: str, attr: str, label: str) -> FieldDef:
    return FieldDef(
        field_id=f"{group}.{attr}",
        group=group,
        label=label,
        data_type="date",
        source="column",
        accessor=attr,
    )


# 마스터 별 기본 컬럼 정의 (화면 그리드와 표시 의미가 동일하도록 코드 → name 표시).
SERVICE_FIELDS: list[FieldDef] = [
    _str_field("service", "service_mgmt_no", "서비스ID"),
    _str_field("service", "name", "서비스명"),
    _fk_code_field("service", "category_code", "분류"),
    _fk_code_field("service", "ito_code", "ITO"),
    _fk_code_field("service", "build_type_code", "구축"),
    _fk_code_field("service", "itgc_code", "ITGC"),
    _fk_code_field("service", "service_grade_code", "등급"),
    _fk_code_field("service", "status_code", "상태"),
    _date_field("service", "opened_at", "오픈일"),
    _date_field("service", "ended_at", "종료일"),
    _str_field("service", "description", "설명", data_type="text"),
]

CONFIG_FIELDS: list[FieldDef] = [
    _str_field("configuration", "asset_mgmt_no", "구성ID"),
    _str_field("configuration", "hostname", "구성명"),
    _str_field("configuration", "connected_services_label", "연결서비스"),
    _fk_code_field("configuration", "server_type_code", "구성유형"),
    _fk_code_field("configuration", "operation_dev_code", "운영/개발"),
    _fk_code_field("configuration", "infra_type_code", "인프라구분"),
    _fk_code_field("configuration", "location_code", "위치"),
    _fk_code_field("configuration", "network_zone_code", "네트웍구분"),
    _str_field("configuration", "ip", "IP"),
    _str_field("configuration", "port", "Port"),
    _str_field("configuration", "url", "URL"),
]

COMPONENT_FIELDS: list[FieldDef] = [
    _str_field("component", "component_mgmt_no", "컴포넌트ID"),
    _str_field("component", "product_name", "컴포넌트명"),
    _str_field("component", "version", "버전", data_type="version"),
    _fk_code_field("component", "component_type_code", "유형"),
    _str_field("component", "vendor_name", "벤더명"),
    _str_field("component", "cpe_name", "CPE"),
    _date_field("component", "eos_date", "EOS"),
    _date_field("component", "eol_date", "EOL"),
    _fk_code_field("component", "support_status_code", "지원여부"),
]

PERSON_FIELDS: list[FieldDef] = [
    _str_field("person", "person_mgmt_no", "담당자ID"),
    _str_field("person", "employee_no", "사번"),
    _str_field("person", "name", "성명"),
    _fk_code_field("person", "role_code", "역할"),
    FieldDef(
        field_id="person.assigned_services",
        group="person",
        label="담당업무",
        data_type="string",
        source="person_services",
    ),
    _fk_code_field("person", "resident_type_code", "상주여부"),
    _fk_code_field("person", "affiliation_code", "소속"),
    _str_field("person", "company", "회사명"),
    _str_field("person", "phone", "전화번호"),
    _str_field("person", "email", "내부메일"),
    _str_field("person", "external_email", "외부메일"),
    _fk_code_field("person", "gender_code", "성별"),
    _fk_code_field("person", "status_code", "상태"),
    _date_field("person", "deployed_at", "투입일"),
    _date_field("person", "ended_at", "종료일"),
]


GROUP_BASE_FIELDS: dict[str, list[FieldDef]] = {
    "service": SERVICE_FIELDS,
    "configuration": CONFIG_FIELDS,
    "component": COMPONENT_FIELDS,
    "person": PERSON_FIELDS,
}


# AttributeCode.target_code(group_key="attribute_target") 의 값 → 통합 view 그룹 매핑
_ATTR_TARGET_TO_GROUP = {
    "SERVICE": "service",
    "CONFIG": "configuration",
}


def _attribute_data_type(ac: AttributeCode) -> str:
    """AttributeCode.data_type_code → integrated view data_type 변환."""
    code = getattr(ac.data_type_code, "code", "") if ac.data_type_code else ""
    return {
        "STRING": "string",
        "NUMBER": "number",
        "DATE": "date",
        "BOOL": "bool",
    }.get(code, "string")


def build_attribute_fields() -> dict[str, list[FieldDef]]:
    """등록된 AttributeCode + 구성정보의 컴포넌트 유형 가상 컬럼을 그룹별 FieldDef 로 변환."""
    out: dict[str, list[FieldDef]] = {g: [] for g, _ in GROUPS}
    service_attrs: list[FieldDef] = []
    for ac in AttributeCode.objects.select_related("data_type_code", "target_code").all():
        target = getattr(ac.target_code, "code", "") if ac.target_code else ""
        group = _ATTR_TARGET_TO_GROUP.get(target)
        if not group:
            continue
        label = (
            _SERVICE_ATTR_LABEL_OVERRIDE.get(ac.attribute_code)
            or _SERVICE_PERSON_LABEL_BY_CODE.get(ac.attribute_code)
            or ac.name
            or ac.attribute_code
        )
        fd = FieldDef(
            field_id=f"{group}.attr.{ac.attribute_code}",
            group=group,
            label=label,
            data_type=_attribute_data_type(ac),
            source="attribute",
            attribute_code=ac.attribute_code,
        )
        if group == "service":
            service_attrs.append(fd)
        else:
            out[group].append(fd)
    order_idx = {c: i for i, c in enumerate(_SERVICE_PERSON_ORDER)}
    persons = [f for f in service_attrs if f.attribute_code in SERVICE_PERSON_ATTRIBUTE_CODES]
    duty_fields = [f for f in service_attrs if f.attribute_code == SERVICE_DUTY_ATTRIBUTE_CODE]
    others = [
        f
        for f in service_attrs
        if f.attribute_code not in SERVICE_PERSON_ATTRIBUTE_CODES and f.attribute_code != SERVICE_DUTY_ATTRIBUTE_CODE
    ]
    persons.sort(key=lambda f: order_idx.get(f.attribute_code, 999))
    others.sort(key=lambda f: f.attribute_code)
    out["service"] = duty_fields + persons + others
    from core.models import Code as _Code

    type_codes = list(
        _Code.objects.filter(group__key="component_type", group__is_active=True, is_active=True)
        .order_by("sort_order", "code")
        .values_list("code", flat=True)
    )
    for tc in type_codes:
        out["configuration"].append(
            FieldDef(
                field_id=f"configuration.component_type.{tc}",
                group="configuration",
                label=tc,
                data_type="string",
                source="component_type",
                attribute_code=tc,
            )
        )
    return out


def get_view_field_meta() -> dict[str, Any]:
    """프론트로 내려줄 그룹·필드 메타. 모든 field_id 화이트리스트 역할."""
    attr_by_group = build_attribute_fields()
    groups: list[dict[str, Any]] = []
    for key, label in GROUPS:
        items: list[FieldDef] = list(GROUP_BASE_FIELDS.get(key, [])) + attr_by_group.get(key, [])
        fields = [
            {
                "field_id": f.field_id,
                "label": f.label,
                "data_type": f.data_type,
                "source": f.source,
            }
            for f in items
        ]
        groups.append({"key": key, "label": label, "fields": fields})
    operators_by_data_type = {
        "string": ["contains", "equals", "startswith", "endswith"],
        "text": ["contains", "equals", "startswith", "endswith"],
        "code": ["equals", "in"],
        "number": ["equals", "gte", "lte", "between"],
        "date": ["equals", "after", "before", "between"],
        "version": ["equals", "gte", "lte", "lt"],
        "bool": ["equals"],
    }
    return {"groups": groups, "operators_by_data_type": operators_by_data_type}


# ──────────────────────────────────────────────────────────────────
# field_id → FieldDef 인덱스
# ──────────────────────────────────────────────────────────────────
def _build_field_index() -> dict[str, FieldDef]:
    idx: dict[str, FieldDef] = {}
    for fields in GROUP_BASE_FIELDS.values():
        for f in fields:
            idx[f.field_id] = f
    for fields in build_attribute_fields().values():
        for f in fields:
            idx[f.field_id] = f
    return idx


# ──────────────────────────────────────────────────────────────────
# 베이스 그룹 별 base queryset / row 추출
# ──────────────────────────────────────────────────────────────────
def _service_base_qs() -> QuerySet:
    return ServiceMaster.objects.select_related(
        "category_code",
        "ito_code",
        "status_code",
        "build_type_code",
        "itgc_code",
        "service_grade_code",
    ).prefetch_related("service_attributes__attribute_code")


def _config_base_qs() -> QuerySet:
    return ConfigurationMaster.objects.select_related(
        "server_type_code", "operation_dev_code", "infra_type_code", "location_code", "network_zone_code"
    ).prefetch_related(
        "configuration_attributes__attribute_code",
        Prefetch(
            "service_configuration_mappings",
            queryset=ServiceConfigurationMapping.objects.select_related("service"),
        ),
        Prefetch(
            "configuration_component_mappings",
            queryset=ConfigurationComponentMapping.objects.select_related("component"),
        ),
    )


def _component_base_qs() -> QuerySet:
    return Component.objects.select_related("component_type_code", "support_status_code").prefetch_related(
        Prefetch(
            "configuration_component_mappings",
            queryset=ConfigurationComponentMapping.objects.select_related("configuration"),
        )
    )


def _person_base_qs() -> QuerySet:
    return PersonMaster.objects.select_related(
        "role_code", "resident_type_code", "affiliation_code", "gender_code", "status_code"
    )


BASE_QS_BUILDERS: dict[str, Callable[[], QuerySet]] = {
    "service": _service_base_qs,
    "configuration": _config_base_qs,
    "component": _component_base_qs,
    "person": _person_base_qs,
}


# ──────────────────────────────────────────────────────────────────
# 정규화: ORM row → 사용자 표시 값
# ──────────────────────────────────────────────────────────────────
def _column_value(obj: Any, accessor: str) -> Any:
    """예: 'category_code__name' → obj.category_code.name. None safe."""
    cur = obj
    for part in accessor.split("__"):
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    if isinstance(cur, (date, datetime)):
        return cur.isoformat() if isinstance(cur, date) else cur.isoformat()
    return cur


def _attr_value_for(obj: Any, group: str, attribute_code: str) -> str:
    """소속 마스터의 *_attributes 에서 attribute_code 값을 조회.

    ServiceAttribute 의 역할 슬롯(SERVICE_PERSON_ATTRIBUTE_CODES) 은 PersonMaster.pk CSV 를
    저장하므로, 화면 표시 시 담당자 이름(콤마 결합)으로 변환한다.
    """
    if group == "service":
        for sa in getattr(obj, "service_attributes", []).all():
            if sa.attribute_code_id == attribute_code:
                value = sa.value or ""
                if attribute_code in SERVICE_PERSON_ATTRIBUTE_CODES:
                    return _persons_label_from_id_csv(value)
                return value
    elif group == "configuration":
        for ca in getattr(obj, "configuration_attributes", []).all():
            if ca.attribute_code_id == attribute_code:
                return ca.value or ""
    return ""


_PERSON_LABEL_CACHE: dict[int, str] = {}


def _persons_label_from_id_csv(value: str) -> str:
    ids: list[int] = []
    for tok in (value or "").split(","):
        tok = tok.strip()
        if tok.isdigit():
            ids.append(int(tok))
    if not ids:
        return ""
    missing = [i for i in ids if i not in _PERSON_LABEL_CACHE]
    if missing:
        for p in PersonMaster.objects.filter(pk__in=missing).only("pk", "name"):
            _PERSON_LABEL_CACHE[p.pk] = (p.name or "").strip() or str(p.pk)
        for i in missing:
            _PERSON_LABEL_CACHE.setdefault(i, str(i))
    return ", ".join(_PERSON_LABEL_CACHE.get(i, str(i)) for i in ids)


def _component_type_value(obj: Any, type_code: str) -> str:
    """ConfigurationMaster row 에 매핑된 컴포넌트 중 해당 유형의 컴포넌트 라벨(콤마 결합)."""
    parts: list[str] = []
    for cm in getattr(obj, "configuration_component_mappings", []).all():
        comp = cm.component
        if not comp:
            continue
        tc = getattr(comp.component_type_code, "code", "") or ""
        if tc != type_code:
            continue
        label = " ".join(p for p in (comp.product_name or "", comp.version or "") if p.strip()).strip()
        parts.append(label or comp.component_mgmt_no)
    return ", ".join(parts)


def _value_within_obj(group: str, obj: Any, field: FieldDef) -> Any:
    """obj 가 group 의 단일 row 일 때, 해당 row 에서 field 값을 추출."""
    if field.source == "column":
        return _column_value(obj, field.accessor)
    if field.source == "attribute":
        return _attr_value_for(obj, group, field.attribute_code)
    if field.source == "component_type" and group == "configuration":
        return _component_type_value(obj, field.attribute_code)
    if field.source == "person_services" and group == "person":
        return ", ".join((s.name or "").strip() for s in _person_services(obj) if s.name)
    return ""


# 베이스 그룹이 아닌 다른 그룹의 필드를 베이스 row 에서 어떻게 취득할지(요약 텍스트)
def _related_value(base_group: str, obj: Any, target_field: FieldDef) -> Any:
    tg = target_field.group
    if tg == base_group:
        return _value_within_obj(base_group, obj, target_field)

    related_objs = _related_objects(base_group, obj, tg)
    if not related_objs:
        return ""
    parts: list[str] = []
    for r in related_objs:
        v = _value_within_obj(tg, r, target_field)
        if v in (None, ""):
            continue
        parts.append(str(v))
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return ", ".join(uniq)


def _related_objects(base_group: str, obj: Any, target_group: str) -> list[Any]:
    """베이스 row 에 연결된 target_group 의 객체 리스트.

    매핑이 단순/명시적이지 않은 경로(예: component → person)는 빈 리스트로 반환한다.
    """
    if base_group == "service":
        if target_group == "configuration":
            return [m.configuration for m in obj.service_configuration_mappings.all() if m.configuration]
        if target_group == "component":
            seen: dict[int, Any] = {}
            for sm in obj.service_configuration_mappings.all():
                if not sm.configuration:
                    continue
                for cm in sm.configuration.configuration_component_mappings.all():
                    if cm.component and cm.component_id not in seen:
                        seen[cm.component_id] = cm.component
            return list(seen.values())
        if target_group == "person":
            return _service_persons(obj)
    if base_group == "configuration":
        if target_group == "service":
            return [m.service for m in obj.service_configuration_mappings.all() if m.service]
        if target_group == "component":
            return [m.component for m in obj.configuration_component_mappings.all() if m.component]
        if target_group == "person":
            seen: dict[int, Any] = {}
            for sc in obj.service_configuration_mappings.all():
                if not sc.service:
                    continue
                for p in _service_persons(sc.service):
                    if p.pk not in seen:
                        seen[p.pk] = p
            return list(seen.values())
    if base_group == "component":
        if target_group == "configuration":
            return [m.configuration for m in obj.configuration_component_mappings.all() if m.configuration]
    if base_group == "person":
        if target_group == "service":
            return _person_services(obj)
        if target_group == "configuration":
            seen: dict[int, Any] = {}
            for svc in _person_services(obj):
                for sc in svc.service_configuration_mappings.all():
                    if sc.configuration and sc.configuration_id not in seen:
                        seen[sc.configuration_id] = sc.configuration
            return list(seen.values())
    return []


def _service_persons(svc: ServiceMaster) -> list[PersonMaster]:
    """서비스의 역할 슬롯(ServiceAttribute) value(CSV) → PersonMaster 리스트."""
    person_ids: set[int] = set()
    for sa in svc.service_attributes.all():
        for tok in (sa.value or "").split(","):
            tok = tok.strip()
            if tok.isdigit():
                person_ids.add(int(tok))
    if not person_ids:
        return []
    return list(PersonMaster.objects.filter(pk__in=person_ids))


def _person_services(p: PersonMaster) -> list[ServiceMaster]:
    """담당자 ID 가 포함된 ServiceAttribute 가 있는 서비스 목록."""
    sas = ServiceAttribute.objects.filter(value__contains=str(p.pk)).select_related("service")
    seen: dict[int, ServiceMaster] = {}
    for sa in sas:
        for tok in (sa.value or "").split(","):
            if tok.strip() == str(p.pk) and sa.service_id not in seen:
                seen[sa.service_id] = sa.service
                break
    return list(seen.values())


# ──────────────────────────────────────────────────────────────────
# 필터 (베이스 그룹의 필드만 효율적 ORM 필터, 그 외는 후처리)
# ──────────────────────────────────────────────────────────────────
def _orm_filter_for_field(field: FieldDef, op: str, value: Any) -> Q | None:
    if field.source != "column":
        return None
    accessor = field.accessor
    # ConfigurationMaster.connected_services_label — DB 컬럼이 아닌 프로퍼티
    if accessor == "connected_services_label":
        return None
    base = accessor.split("__")[0]
    is_fk_code = accessor.endswith("__name")
    target = accessor if is_fk_code else accessor

    sval = "" if value is None else str(value).strip()
    if op == "contains":
        return Q(**{f"{target}__icontains": sval})
    if op == "equals":
        return Q(**{f"{target}": sval}) if not is_fk_code else (Q(**{base + "__name": sval}) | Q(**{base + "__code": sval}))
    if op == "startswith":
        return Q(**{f"{target}__istartswith": sval})
    if op == "endswith":
        return Q(**{f"{target}__iendswith": sval})
    if op == "in":
        vals = [v.strip() for v in (sval.split(",") if isinstance(sval, str) else list(sval)) if v.strip()]
        if not vals:
            return None
        if is_fk_code:
            return Q(**{base + "__name__in": vals}) | Q(**{base + "__code__in": vals})
        return Q(**{f"{target}__in": vals})
    if op in {"gte", "lte", "lt"}:
        django_op = {"gte": "gte", "lte": "lte", "lt": "lt"}[op]
        return Q(**{f"{target}__{django_op}": value})
    if op == "between":
        if isinstance(value, (list, tuple)) and len(value) == 2 and value[0] not in (None, "") and value[1] not in (None, ""):
            return Q(**{f"{target}__gte": value[0], f"{target}__lte": value[1]})
        return None
    if op in {"after", "before"}:
        return Q(**{f"{target}__{'gt' if op == 'after' else 'lt'}": value})
    return None


def _python_filter(value_for_field: Any, op: str, value: Any) -> bool:
    """베이스 외 그룹 필드 또는 attribute 필드의 값을 row 단위로 필터.

    value_for_field 는 _related_value 결과(스칼라 또는 콤마 문자열)이다.
    """
    if value_for_field is None:
        value_for_field = ""
    s = str(value_for_field)
    sval = "" if value is None else str(value).strip()
    if op == "contains":
        return sval.lower() in s.lower()
    if op == "equals":
        return s == sval
    if op == "startswith":
        return s.lower().startswith(sval.lower())
    if op == "endswith":
        return s.lower().endswith(sval.lower())
    if op == "in":
        vals = [v.strip() for v in (sval.split(",") if isinstance(sval, str) else list(sval)) if v.strip()]
        return any(v == s or v in s.split(", ") for v in vals)
    return True


# ──────────────────────────────────────────────────────────────────
# 검색 본체
# ──────────────────────────────────────────────────────────────────
def _normalize_text_filter_cells(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raw = []
    cells = [("" if x is None else str(x)) for x in raw]
    while len(cells) < TEXT_FILTER_SLOT_COUNT:
        cells.append("")
    return cells[:TEXT_FILTER_SLOT_COUNT]


def _parse_text_filters(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("text_filters")
    if raw is None:
        raw = payload.get("conditions")
    return _normalize_text_filter_cells(raw)


def _parse_condition_cell(query: str) -> tuple[list[tuple[str, str]], str]:
    """한 칸 문자열에서 구조화 토큰(컬럼명:값 / 컬럼명=값)과 나머지 자유 텍스트를 분리."""
    terms: list[tuple[str, str]] = []
    spans: list[tuple[int, int]] = []
    for m in INTEGRATED_TERM_PATTERN.finditer(query or ""):
        key = normalize_service_search_key(m.group(1))
        value = (m.group(2) or "").strip()
        if key and value:
            terms.append((key, value))
            spans.append(m.span())
    if not spans:
        return [], (query or "").strip()
    rest = query or ""
    for s, e in reversed(spans):
        rest = rest[:s] + " " + rest[e:]
    return terms, " ".join(rest.split())


def _column_search_key_index(selected_fields: list[FieldDef]) -> dict[str, str]:
    """normalize된 검색 키 → field_id (그리드 컬럼 라벨·필드 접미사 등)."""
    idx: dict[str, str] = {}
    for f in selected_fields:
        nk = normalize_service_search_key(f.label)
        if nk:
            idx[nk] = f.field_id
        tail = f.field_id.split(".")[-1]
        for variant in (tail, tail.replace("_", "")):
            tk = normalize_service_search_key(variant)
            if tk:
                idx[tk] = f.field_id
        if "_" in tail:
            prefix = tail.rsplit("_", 1)[0]
            pk = normalize_service_search_key(prefix)
            if pk:
                idx[pk] = f.field_id
        full = normalize_service_search_key(f.field_id.replace(".", ""))
        if full:
            idx[full] = f.field_id
    return idx


def _row_matches_condition_cell(
    row: dict[str, Any], cell: str, col_index: dict[str, str], haystack: str
) -> bool:
    cell_st = (cell or "").strip()
    if not cell_st:
        return True
    structured, free = _parse_condition_cell(cell_st)
    for k, v in structured:
        fid = col_index.get(k)
        v_l = v.lower()
        if fid is not None:
            cell_display = str(row.get(fid, "") or "").lower()
            if v_l not in cell_display:
                return False
        else:
            frag1 = f"{k}:{v}".lower()
            frag2 = f"{k}={v}".lower()
            if frag1 not in haystack and frag2 not in haystack and v_l not in haystack:
                return False
    ft = free.strip()
    if ft and ft.lower() not in haystack:
        return False
    return True


def _row_matches_integrated_cells(row: dict[str, Any], text_cells: list[str], col_index: dict[str, str]) -> bool:
    hay = _row_text_haystack(row)
    for cell in text_cells:
        if not (cell or "").strip():
            continue
        if not _row_matches_condition_cell(row, cell, col_index, hay):
            return False
    return True


def _resolve_request(payload: dict[str, Any]) -> tuple[str, list[FieldDef], list[str]]:
    selected_ids: list[str] = list(payload.get("selected_fields") or [])

    field_index = _build_field_index()
    selected_fields = [field_index[fid] for fid in selected_ids if fid in field_index]
    selected_fields = _canonical_service_person_field_order(selected_fields)
    if not selected_fields:
        raise ValueError("선택된 항목이 없습니다.")

    text_cells = _parse_text_filters(payload)
    base_group = selected_fields[0].group
    return base_group, selected_fields, text_cells


def _row_text_haystack(row: dict[str, Any]) -> str:
    return " ".join("" if v is None else str(v) for v in row.values()).lower()


def _execute_search(payload: dict[str, Any]) -> dict[str, Any]:
    base_group, selected_fields, text_cells = _resolve_request(payload)
    qs = BASE_QS_BUILDERS[base_group]()

    qs = qs.distinct()

    objects = list(qs)

    rows_with_obj: list[tuple[Any, dict[str, Any]]] = []
    for obj in objects:
        row: dict[str, Any] = {}
        for f in selected_fields:
            row[f.field_id] = _related_value(base_group, obj, f)
        rows_with_obj.append((obj, row))

    if any((c or "").strip() for c in text_cells):
        col_index = _column_search_key_index(selected_fields)
        rows_with_obj = [
            (obj, row)
            for obj, row in rows_with_obj
            if _row_matches_integrated_cells(row, text_cells, col_index)
        ]

    total = len(rows_with_obj)
    columns = [{"field_id": f.field_id, "label": f.label, "data_type": f.data_type} for f in selected_fields]
    rows = [row for _, row in rows_with_obj]

    return {
        "base_group": base_group,
        "columns": columns,
        "rows": rows,
        "total": total,
        "page": 1,
        "page_size": total,
        "page_count": 1,
    }


# ──────────────────────────────────────────────────────────────────
# 뷰 진입점
# ──────────────────────────────────────────────────────────────────
@login_required
def integrated_view(request):
    import json as _json

    from django.utils.safestring import mark_safe

    meta = get_view_field_meta()
    meta_json = _json.dumps(meta, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    return render(
        request,
        "web/integrated_view.html",
        {
            "view_field_meta": mark_safe(meta_json),
            "can_export": _can_export(request),
        },
    )


def _can_export(request) -> bool:
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def _parse_json_body(request) -> dict[str, Any]:
    import json

    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


@login_required
@require_POST
def integrated_view_search(request):
    try:
        payload = _parse_json_body(request)
        result = _execute_search(payload)
        return JsonResponse({"ok": True, "result": result})
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"검색 중 오류가 발생했습니다: {e}"}, status=500)


@login_required
@require_POST
def integrated_view_export(request):
    if not _can_export(request):
        return JsonResponse({"ok": False, "error": "엑셀 다운로드 권한이 없습니다."}, status=403)
    try:
        payload = _parse_json_body(request)
        payload = dict(payload or {})
        result = _execute_search(payload)
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    columns = result["columns"]
    rows = result["rows"]
    df_rows = [{c["label"]: r.get(c["field_id"], "") for c in columns} for r in rows]
    df = pd.DataFrame(df_rows)

    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="통합View")
    res = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    res["Content-Disposition"] = 'attachment; filename="integrated_view.xlsx"'
    return res


@login_required
@require_GET
def integrated_view_meta(request):
    return JsonResponse({"ok": True, "meta": get_view_field_meta()})


def _preset_text_filter_cells(conditions_val: Any) -> list[str]:
    """JSON conditions 필드: 신규는 문자열 리스트, 구버전은 필드조건 dict 리스트(무시). 항상 5칸."""
    if isinstance(conditions_val, list) and (not conditions_val or isinstance(conditions_val[0], str)):
        return _normalize_text_filter_cells(conditions_val)
    return _normalize_text_filter_cells([])


@login_required
@require_GET
def integrated_view_presets(request):
    presets = {}
    for p in IntegratedViewPreset.objects.filter(user=request.user, slot__in=[1, 2, 3]):
        tf = _preset_text_filter_cells(p.conditions)
        presets[p.slot] = {
            "name": p.name,
            "selected_fields": p.selected_fields,
            "text_filters": tf,
            "updated_at": p.updated_at.isoformat(),
        }
    result = {}
    for slot in (1, 2, 3):
        result[str(slot)] = presets.get(slot) or None
    return JsonResponse({"ok": True, "presets": result})


@login_required
@require_POST
def integrated_view_presets_save(request):
    try:
        payload = _parse_json_body(request)
        slot = int(payload.get("slot") or 0)
        if slot not in (1, 2, 3):
            return JsonResponse({"ok": False, "error": "slot은 1~3만 허용됩니다."}, status=400)
        selected_fields = list(payload.get("selected_fields") or [])
        raw_tf = payload.get("text_filters", payload.get("conditions"))
        text_cells = _normalize_text_filter_cells(raw_tf)
        name = str(payload.get("name") or "").strip()

        obj, _ = IntegratedViewPreset.objects.update_or_create(
            user=request.user,
            slot=slot,
            defaults={"name": name, "selected_fields": selected_fields, "conditions": text_cells},
        )
        return JsonResponse(
            {
                "ok": True,
                "preset": {
                    "slot": obj.slot,
                    "name": obj.name,
                    "selected_fields": obj.selected_fields,
                    "text_filters": _preset_text_filter_cells(obj.conditions),
                    "updated_at": obj.updated_at.isoformat(),
                },
            }
        )
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"프리셋 저장 중 오류가 발생했습니다: {e}"}, status=500)


@login_required
@require_POST
def integrated_view_presets_clear(request):
    try:
        payload = _parse_json_body(request)
        slot = int(payload.get("slot") or 0)
        if slot not in (1, 2, 3):
            return JsonResponse({"ok": False, "error": "slot은 1~3만 허용됩니다."}, status=400)
        IntegratedViewPreset.objects.filter(user=request.user, slot=slot).delete()
        return JsonResponse({"ok": True, "slot": slot})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
