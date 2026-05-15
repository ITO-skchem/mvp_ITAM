"""서비스 마스터 그리드: 담당현업(문자열) + 역할별 담당자 매핑용 AttributeCode·컬럼 정의."""

from __future__ import annotations

# 서비스 마스터 그리드·통합정보에서 DT팀 담당자 열 직전에 두는 문자열 속성
SERVICE_DUTY_ATTRIBUTE_CODE = "SVC_ATTR_CURRENT_DUTY"
SERVICE_DUTY_ATTRIBUTE_LABEL = "담당현업"

SERVICE_PERSON_GRID_COLUMNS: list[dict[str, str]] = [
    {"role_code": "DT_TEAM", "attribute_code": "SVC_ATTR_PERSON_DT_TEAM", "label": "DT팀"},
    {"role_code": "ADMIN", "attribute_code": "SVC_ATTR_PERSON_ADMIN", "label": "관리자"},
    {"role_code": "OPERATOR", "attribute_code": "SVC_ATTR_PERSON_OPERATOR", "label": "운영자"},
    {"role_code": "INFRA_OPERATOR", "attribute_code": "SVC_ATTR_PERSON_INFRA_OPERATOR", "label": "Infra담당자"},
]


def attribute_codes_for_grid() -> list[str]:
    return [c["attribute_code"] for c in SERVICE_PERSON_GRID_COLUMNS]


def service_grid_prefetch_attribute_codes() -> list[str]:
    """그리드/엑셀에서 미리 불러올 서비스 속성 코드(담당현업 + 담당자 4종)."""
    return [SERVICE_DUTY_ATTRIBUTE_CODE, *attribute_codes_for_grid()]


def ensure_service_duty_attribute_code() -> None:
    """담당현업(문자열) 서비스 속성 AttributeCode 보장."""
    from core.models import Code
    from masters.models import AttributeCode

    data_type = Code.objects.filter(group__key="data_type", code="STRING").first()
    required = Code.objects.filter(group__key="required_flag", code="N").first()
    searchable = Code.objects.filter(group__key="searchable_flag", code="Y").first()
    target = Code.objects.filter(group__key="attribute_target", code="SERVICE").first()
    if not all([data_type, required, searchable, target]):
        return
    AttributeCode.objects.update_or_create(
        attribute_code=SERVICE_DUTY_ATTRIBUTE_CODE,
        defaults={
            "name": SERVICE_DUTY_ATTRIBUTE_LABEL,
            "data_type_code": data_type,
            "required_code": required,
            "searchable_code": searchable,
            "target_code": target,
        },
    )


def ensure_service_person_attribute_codes() -> None:
    """seed_codes 등에서 호출: 서비스 담당자 역할 속성(AttributeCode) 4건을 보장."""
    from core.models import Code
    from masters.models import AttributeCode

    data_type = Code.objects.filter(group__key="data_type", code="STRING").first()
    required = Code.objects.filter(group__key="required_flag", code="N").first()
    searchable = Code.objects.filter(group__key="searchable_flag", code="Y").first()
    target = Code.objects.filter(group__key="attribute_target", code="SERVICE").first()
    if not target:
        return
    for row in SERVICE_PERSON_GRID_COLUMNS:
        AttributeCode.objects.update_or_create(
            attribute_code=row["attribute_code"],
            defaults={
                "name": row["label"],
                "data_type_code": data_type,
                "required_code": required,
                "searchable_code": searchable,
                "target_code": target,
            },
        )
