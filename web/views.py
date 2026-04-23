import json
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import urlencode

import pandas as pd
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ai_search.services import AssetSearchService
from assets.infra_sync import build_appl_owner_names
from assets.models import InfraAsset
from core.models import AuditLog, Code
from masters.models import Component, PersonMaster, ServiceMaster

PERSON_ROLE_CODES = [
    "고객사 담당자",
    "Appl. 담당자",
    "Appl. 운영자",
    "서버 담당자",
    "DB 담당자",
]
RESIDENT_CODES = ["상주", "비상주"]
PERSON_ROLE_ALIASES = {
    "customer": "고객사 담당자",
    "customer_owner": "고객사 담당자",
    "appl": "Appl. 담당자",
    "app": "Appl. 담당자",
    "application": "Appl. 담당자",
    "developer": "Appl. 담당자",
    "partner": "Appl. 운영자",
    "partner_operator": "Appl. 운영자",
    "협력사 운영자": "Appl. 운영자",
    "server": "서버 담당자",
    "server_owner": "서버 담당자",
    "db": "DB 담당자",
    "db_owner": "DB 담당자",
}


def build_code_label_maps(group_keys):
    rows = (
        Code.objects.filter(group__key__in=group_keys, group__is_active=True, is_active=True)
        .select_related("group")
        .order_by("group__sort_order", "sort_order", "code")
    )
    maps = {key: {} for key in group_keys}
    for row in rows:
        maps[row.group.key][row.code] = row.name
    return maps


def build_code_options(group_key, include_blank=True):
    rows = (
        Code.objects.filter(group__key=group_key, group__is_active=True, is_active=True)
        .select_related("group")
        .order_by("group__sort_order", "sort_order", "code")
    )
    options = [("", "---------")] if include_blank else []
    options.extend([(r.code, r.name) for r in rows])
    return options


def parse_bool(val):
    return str(val).strip().lower() in {"1", "y", "yes", "true", "t"}


def parse_decimal(val):
    if val in (None, ""):
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return None


def parse_date(val):
    if val in (None, ""):
        return None
    dt = pd.to_datetime(val, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.date()


def split_owner_names(raw):
    value = str(raw or "").strip()
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def parse_resident_code(val):
    if isinstance(val, bool):
        return val
    text = str(val).strip()
    if not text:
        return None
    if text == "상주":
        return True
    if text == "비상주":
        return False
    lowered = text.lower()
    if lowered in {"1", "y", "yes", "true", "t"}:
        return True
    if lowered in {"0", "n", "no", "false", "f"}:
        return False
    return None


def normalize_person_role(val):
    text = str(val or "").strip()
    if not text:
        return ""
    if text in PERSON_ROLE_CODES:
        return text
    return PERSON_ROLE_ALIASES.get(text.lower(), text)


def sync_legacy_person_roles():
    changed_people = []
    for person in PersonMaster.objects.exclude(role="").only("pk", "role"):
        normalized = normalize_person_role(person.role)
        if normalized != person.role and normalized in PERSON_ROLE_CODES:
            person.role = normalized
            changed_people.append(person)
    if changed_people:
        PersonMaster.objects.bulk_update(changed_people, ["role"])


def to_excel_response(df, filename):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    out.seek(0)
    res = HttpResponse(
        out.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    res["Content-Disposition"] = f'attachment; filename="{filename}"'
    return res


def build_list_redirect(path, query="", page="", failed_ids=None):
    params = {}
    if query:
        params["q"] = query
    if page:
        params["page"] = page
    if failed_ids:
        params["failed_ids"] = ",".join(str(x) for x in failed_ids)
    return f"{path}?{urlencode(params)}" if params else path


def build_error_message(exc):
    msg = str(exc)
    if "UNIQUE constraint failed" in msg:
        return "중복 KEY 또는 유니크 제약 오류"
    if "NOT NULL constraint failed" in msg:
        return "필수값 누락"
    return "저장 실패"


def summarize_row_errors(row_errors):
    if not row_errors:
        return []
    counts = {}
    for msg in row_errors.values():
        if not msg:
            continue
        counts[msg] = counts.get(msg, 0) + 1
    return [f"{msg} ({count}건)" for msg, count in counts.items()]


def get_row_value(row, candidates, default=""):
    for key in candidates:
        if key in row.index:
            value = row.get(key)
            if pd.isna(value):
                continue
            return value
    return default


_TEXT_SEARCH_FIELD_TYPES = frozenset(
    {
        "CharField",
        "TextField",
        "EmailField",
        "URLField",
        "SlugField",
        "GenericIPAddressField",
    }
)


def build_model_text_search_q(model_class, query):
    """리스트 검색: 모델의 문자열 계열 컬럼 전부에 대해 OR(icontains) 조건을 만든다."""
    text = (query or "").strip()
    if not text:
        return Q()
    combined = Q()
    for field in model_class._meta.get_fields():
        if not getattr(field, "concrete", True):
            continue
        if getattr(field, "many_to_many", False) or getattr(field, "one_to_many", False):
            continue
        if field.get_internal_type() == "JSONField":
            continue
        if field.get_internal_type() not in _TEXT_SEARCH_FIELD_TYPES:
            continue
        combined |= Q(**{f"{field.attname}__icontains": text})
    return combined


@login_required
def dashboard(request):
    context = {
        "counts": {
            "infra": InfraAsset.objects.count(),
            "service": ServiceMaster.objects.count(),
            "person": PersonMaster.objects.count(),
            "component": Component.objects.count(),
            "audit": AuditLog.objects.count(),
        }
    }
    return render(request, "web/dashboard.html", context)


@login_required
@permission_required("assets.view_infraasset", raise_exception=True)
def asset_list(request):
    query = request.GET.get("q", "").strip()
    qs = InfraAsset.objects.all().order_by("service_mgmt_no", "asset_mgmt_no")
    if query:
        qs = qs.filter(build_model_text_search_q(InfraAsset, query))

    if request.GET.get("export") == "1":
        cols = [
            "system_mgmt_no",
            "service_name",
            "hostname",
            "customer_owner_name",
            "appl_owner_name",
            "partner_operator_name",
            "server_type",
            "operation_dev",
            "network_zone",
            "platform_type",
            "ip",
            "port",
            "location",
            "mw",
            "os_dbms",
            "url_or_db_name",
            "ssl_domain",
            "cert_format",
            "remark1",
            "remark2",
        ]
        rename_map = {
            "system_mgmt_no": "시스템 관리번호",
            "service_name": "서비스명",
            "customer_owner_name": "고객사 담당자",
            "appl_owner_name": "Appl. 담당자",
            "partner_operator_name": "Appl. 운영자",
            "hostname": "Hostname",
            "server_type": "서버 구분",
            "operation_dev": "운영/개발",
            "network_zone": "네트웍 구분",
            "platform_type": "플랫폼 구분",
            "ip": "IP",
            "port": "Port",
            "location": "위치",
            "mw": "MW",
            "os_dbms": "OS/DBMS",
            "url_or_db_name": "URL/DB명",
            "ssl_domain": "SSL 도메인",
            "cert_format": "인증서 포맷",
            "remark1": "비고1",
            "remark2": "비고2",
        }
        rows = list(qs.values(*cols))
        df = pd.DataFrame(rows, columns=cols).rename(columns=rename_map)
        df = df[[rename_map[c] for c in cols]]
        return to_excel_response(df, "system_integrated_info.xlsx")

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "web/asset_list.html",
        {
            "assets": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
        },
    )


@login_required
@permission_required("assets.view_infraasset", raise_exception=True)
def asset_detail(request, pk):
    obj = get_object_or_404(InfraAsset, pk=pk)
    return render(request, "web/asset_detail.html", {"asset": obj})


@login_required
@permission_required("masters.view_servicemaster", raise_exception=True)
def service_master_list(request):
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page", "").strip()
    failed_ids = {int(x) for x in request.GET.get("failed_ids", "").split(",") if x.isdigit()}
    row_errors = request.session.pop("row_errors_service", {})
    qs = ServiceMaster.objects.all().order_by("service_mgmt_no", "name")
    if query:
        qs = qs.filter(build_model_text_search_q(ServiceMaster, query))

    if request.GET.get("export") == "1":
        cols = [
            "service_mgmt_no",
            "name",
            "system_type",
            "description",
            "operation_type",
            "service_grade",
            "service_level",
            "itgc",
            "customer_owner",
            "partner_operator",
            "appl_owner",
            "server_owner",
            "db_owner",
            "opened_at",
            "build_type",
            "dev_language",
            "dev_framework",
            "cloud_type",
            "dbms",
            "scm_tool",
            "deploy_tool",
            "monitoring_tool",
            "gc",
            "pharma",
            "plasma",
            "mu",
            "entis",
            "daejung",
            "dy",
            "bs",
            "bs_share_ratio",
            "bs_share_note",
            "notes",
        ]
        rename_map = {
            "service_mgmt_no": "서비스관리번호",
            "name": "서비스명",
            "system_type": "시스템 구분",
            "description": "설명",
            "operation_type": "운영구분",
            "service_grade": "서비스 등급",
            "service_level": "서비스 수준",
            "itgc": "ITGC 여부",
            "customer_owner": "고객사 담당자",
            "partner_operator": "Appl. 담당자",
            "appl_owner": "Appl. 운영자",
            "server_owner": "서버 담당자",
            "db_owner": "DB 담당자",
            "opened_at": "서비스 오픈일",
            "build_type": "구축 구분",
            "dev_language": "개발 언어",
            "dev_framework": "개발 F/W",
            "cloud_type": "Cloud 구분",
            "dbms": "DBMS",
            "scm_tool": "형상관리",
            "deploy_tool": "배포도구",
            "monitoring_tool": "모니터링도구",
            "gc": "GC",
            "pharma": "파마",
            "plasma": "플라즈마",
            "mu": "MU",
            "entis": "엔티스",
            "daejung": "대정",
            "dy": "DY",
            "bs": "BS",
            "bs_share_ratio": "BS Share 비율",
            "bs_share_note": "BS Share 비고",
            "notes": "비고",
        }
        df = pd.DataFrame(list(qs.values(*cols)), columns=cols).rename(columns=rename_map)
        df = df[[rename_map[c] for c in cols]]
        return to_excel_response(df, "service_master.xlsx")

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "import" and request.FILES.get("excel_file"):
            df = pd.read_excel(request.FILES["excel_file"])
            updated_count = 0
            created_count = 0
            skipped_count = 0
            import_row_errors = {}
            for excel_row_no, (_, row) in enumerate(df.iterrows(), start=2):
                mgmt_no = str(get_row_value(row, ["service_mgmt_no", "서비스관리번호"], "")).strip()
                service_name = str(get_row_value(row, ["name", "서비스명", "시스템명"], "")).strip()
                if not service_name:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = f"{excel_row_no}행: 필수값 누락: 서비스명"
                    continue
                defaults = {
                    "name": service_name,
                    "system_type": str(get_row_value(row, ["system_type", "시스템 구분"], "")).strip(),
                    "description": str(get_row_value(row, ["description", "설명"], "")).strip(),
                    "operation_type": str(get_row_value(row, ["operation_type", "운영구분"], "")).strip(),
                    "service_grade": str(get_row_value(row, ["service_grade", "서비스 등급"], "")).strip(),
                    "service_level": str(get_row_value(row, ["service_level", "서비스 수준"], "")).strip(),
                    "itgc": parse_bool(get_row_value(row, ["itgc", "ITGC 여부"], "")),
                    "customer_owner": str(get_row_value(row, ["customer_owner", "고객사 담당자"], "")).strip(),
                    "partner_operator": str(
                        get_row_value(row, ["partner_operator", "Appl. 담당자", "협력사 운영자"], "")
                    ).strip(),
                    "appl_owner": build_appl_owner_names(service_name),
                    "server_owner": str(get_row_value(row, ["server_owner", "서버 담당자"], "")).strip(),
                    "db_owner": str(get_row_value(row, ["db_owner", "DB 담당자"], "")).strip(),
                    "opened_at": parse_date(get_row_value(row, ["opened_at", "서비스 오픈일"], "")),
                    "build_type": str(get_row_value(row, ["build_type", "구축 구분"], "")).strip(),
                    "dev_language": str(get_row_value(row, ["dev_language", "개발 언어"], "")).strip(),
                    "dev_framework": str(get_row_value(row, ["dev_framework", "개발 F/W"], "")).strip(),
                    "cloud_type": str(get_row_value(row, ["cloud_type", "Cloud 구분"], "")).strip(),
                    "dbms": str(get_row_value(row, ["dbms", "DBMS"], "")).strip(),
                    "scm_tool": str(get_row_value(row, ["scm_tool", "형상관리"], "")).strip(),
                    "deploy_tool": str(get_row_value(row, ["deploy_tool", "배포도구"], "")).strip(),
                    "monitoring_tool": str(get_row_value(row, ["monitoring_tool", "모니터링도구"], "")).strip(),
                    "gc": parse_bool(get_row_value(row, ["gc", "GC"], "")),
                    "pharma": parse_bool(get_row_value(row, ["pharma", "파마"], "")),
                    "plasma": parse_bool(get_row_value(row, ["plasma", "플라즈마"], "")),
                    "mu": parse_bool(get_row_value(row, ["mu", "MU"], "")),
                    "entis": parse_bool(get_row_value(row, ["entis", "엔티스"], "")),
                    "daejung": parse_bool(get_row_value(row, ["daejung", "대정"], "")),
                    "dy": parse_bool(get_row_value(row, ["dy", "DY"], "")),
                    "bs": parse_bool(get_row_value(row, ["bs", "BS"], "")),
                    "bs_share_ratio": parse_decimal(get_row_value(row, ["bs_share_ratio", "BS Share 비율"], "")),
                    "bs_share_note": str(get_row_value(row, ["bs_share_note", "BS Share 비고"], "")).strip(),
                    "notes": str(get_row_value(row, ["notes", "비고"], "")).strip(),
                }
                owner_names = []
                owner_names.extend(split_owner_names(defaults["appl_owner"]))
                if any(name and not PersonMaster.objects.filter(name=name).exists() for name in owner_names):
                    skipped_count += 1
                    invalid_names = sorted(
                        {name for name in owner_names if name and not PersonMaster.objects.filter(name=name).exists()}
                    )
                    import_row_errors[f"import_{excel_row_no}"] = (
                        f"{excel_row_no}행: 담당자 마스터 미등록 성명: {', '.join(invalid_names)}"
                    )
                    continue
                if mgmt_no:
                    existing = ServiceMaster.objects.filter(service_mgmt_no=mgmt_no).first()
                    if existing:
                        for key, val in defaults.items():
                            setattr(existing, key, val)
                        existing.save()
                        updated_count += 1
                    elif defaults["name"]:
                        ServiceMaster.objects.create(service_mgmt_no=mgmt_no, **defaults)
                        created_count += 1
                    else:
                        skipped_count += 1
                elif defaults["name"]:
                    ServiceMaster.objects.create(**defaults)
                    created_count += 1
                else:
                    skipped_count += 1
            messages.success(
                request,
                f"엑셀 import 완료: 업데이트 {updated_count}건 / 인서트 {created_count}건 / 스킵 {skipped_count}건",
            )
            if import_row_errors:
                request.session["row_errors_service"] = import_row_errors
            return redirect(build_list_redirect(request.path, query=query, page=page))

        if action == "save":
            rows = json.loads(request.POST.get("rows_json", "[]"))
            deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
            failed_ids = []
            row_errors = {}
            invalid_person_names = set()
            if deleted_ids:
                try:
                    ServiceMaster.objects.filter(pk__in=deleted_ids).delete()
                except Exception as exc:
                    for xid in [x for x in deleted_ids if str(x).isdigit()]:
                        failed_ids.append(xid)
                        row_errors[str(xid)] = f"삭제 실패: {build_error_message(exc)}"

            for row in rows:
                pk = str(row.get("id", "")).strip()
                service_mgmt_no = str(row.get("service_mgmt_no", "")).strip()
                name = str(row.get("name", "")).strip()
                if not pk and not name:
                    continue
                opened_at_raw = str(row.get("opened_at") or "").strip()
                opened_at = parse_date(opened_at_raw)
                if opened_at_raw and opened_at is None:
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "유효하지 않은 날짜"
                    continue
                payload = {
                    "name": name,
                    "system_type": (row.get("system_type") or "").strip(),
                    "description": (row.get("description") or "").strip(),
                    "operation_type": (row.get("operation_type") or "").strip(),
                    "service_grade": (row.get("service_grade") or "").strip(),
                    "service_level": (row.get("service_level") or "").strip(),
                    "itgc": parse_bool(row.get("itgc")),
                    "customer_owner": (row.get("customer_owner") or "").strip(),
                    "partner_operator": (row.get("partner_operator") or "").strip(),
                    "appl_owner": build_appl_owner_names(name),
                    "server_owner": (row.get("server_owner") or "").strip(),
                    "db_owner": (row.get("db_owner") or "").strip(),
                    "opened_at": opened_at,
                    "build_type": (row.get("build_type") or "").strip(),
                    "dev_language": (row.get("dev_language") or "").strip(),
                    "dev_framework": (row.get("dev_framework") or "").strip(),
                    "cloud_type": (row.get("cloud_type") or "").strip(),
                    "dbms": (row.get("dbms") or "").strip(),
                    "scm_tool": (row.get("scm_tool") or "").strip(),
                    "deploy_tool": (row.get("deploy_tool") or "").strip(),
                    "monitoring_tool": (row.get("monitoring_tool") or "").strip(),
                    "gc": parse_bool(row.get("gc")),
                    "pharma": parse_bool(row.get("pharma")),
                    "plasma": parse_bool(row.get("plasma")),
                    "mu": parse_bool(row.get("mu")),
                    "entis": parse_bool(row.get("entis")),
                    "daejung": parse_bool(row.get("daejung")),
                    "dy": parse_bool(row.get("dy")),
                    "bs": parse_bool(row.get("bs")),
                    "bs_share_ratio": parse_decimal(row.get("bs_share_ratio")),
                    "bs_share_note": (row.get("bs_share_note") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                }
                owner_names = []
                owner_names.extend(split_owner_names(payload["appl_owner"]))
                if any(name and not PersonMaster.objects.filter(name=name).exists() for name in owner_names):
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "담당자 마스터에 등록된 성명만 입력 가능합니다."
                    else:
                        for owner_part in owner_names:
                            if owner_part and not PersonMaster.objects.filter(name=owner_part).exists():
                                invalid_person_names.add(owner_part)
                    continue
                if pk:
                    try:
                        obj = ServiceMaster.objects.get(pk=pk)
                        for key, val in payload.items():
                            setattr(obj, key, val)
                        obj.save()
                    except Exception as exc:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = build_error_message(exc)
                elif payload["name"]:
                    try:
                        ServiceMaster.objects.create(service_mgmt_no=service_mgmt_no or None, **payload)
                    except Exception as exc:
                        if service_mgmt_no:
                            dup = ServiceMaster.objects.filter(service_mgmt_no=service_mgmt_no).values_list("pk", flat=True).first()
                            if dup:
                                failed_ids.append(dup)
                                row_errors[str(dup)] = build_error_message(exc)
            if invalid_person_names:
                messages.error(
                    request,
                    "담당자 마스터 미등록 성명으로 저장할 수 없습니다: " + ", ".join(sorted(invalid_person_names)),
                )
                row_errors["__global_person__"] = "담당자 마스터 미등록 성명 입력"
            request.session["row_errors_service"] = row_errors
            return redirect(build_list_redirect(request.path, query=query, page=page, failed_ids=failed_ids))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "web/service_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "failed_ids": failed_ids,
            "row_errors": row_errors,
            "popup_error_summary": summarize_row_errors(row_errors),
        },
    )


@login_required
@permission_required("masters.view_personmaster", raise_exception=True)
def person_master_list(request):
    sync_legacy_person_roles()
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page", "").strip()
    failed_ids = {int(x) for x in request.GET.get("failed_ids", "").split(",") if x.isdigit()}
    row_errors = request.session.pop("row_errors_person", {})
    qs = PersonMaster.objects.all().order_by("person_mgmt_no", "name")
    if query:
        q = build_model_text_search_q(PersonMaster, query)
        if query.strip() == "상주":
            q |= Q(resident=True)
        elif query.strip() == "비상주":
            q |= Q(resident=False)
        qs = qs.filter(q)

    if request.GET.get("export") == "1":
        cols = [
            "person_mgmt_no",
            "name",
            "employee_no",
            "role",
            "system_name",
            "resident",
            "company",
            "phone",
            "email",
            "ext_email",
            "deployed_at",
            "notes",
        ]
        rename_map = {
            "person_mgmt_no": "담당자관리번호",
            "name": "성명",
            "employee_no": "사번",
            "role": "역할",
            "system_name": "담당 서비스",
            "resident": "상주 여부",
            "company": "소속 조직",
            "phone": "연락처",
            "email": "내부 메일",
            "ext_email": "외부 메일",
            "deployed_at": "투입 일자",
            "notes": "비고",
        }
        df = pd.DataFrame(list(qs.values(*cols)), columns=cols)
        df["resident"] = df["resident"].apply(lambda x: "상주" if bool(x) else "비상주")
        df = df.rename(columns=rename_map)
        df = df[[rename_map[c] for c in cols]]
        return to_excel_response(df, "person_master.xlsx")

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "import" and request.FILES.get("excel_file"):
            df = pd.read_excel(request.FILES["excel_file"])
            updated_count = 0
            created_count = 0
            skipped_count = 0
            import_row_errors = {}
            for excel_row_no, (_, row) in enumerate(df.iterrows(), start=2):
                mgmt_no = str(get_row_value(row, ["person_mgmt_no", "담당자관리번호"], "")).strip()
                person_name = str(get_row_value(row, ["name", "성명"], "")).strip()
                if not person_name:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = f"{excel_row_no}행: 필수값 누락: 성명"
                    continue
                defaults = {
                    "name": person_name,
                    "employee_no": str(get_row_value(row, ["employee_no", "사번"], "")).strip(),
                    "role": normalize_person_role(get_row_value(row, ["role", "역할"], "")),
                    "system_name": str(
                        get_row_value(row, ["system_name", "담당 서비스", "담당 시스템"], "")
                    ).strip(),
                    "resident": parse_resident_code(get_row_value(row, ["resident", "상주 여부"], "")),
                    "company": str(get_row_value(row, ["company", "소속 조직"], "")).strip(),
                    "phone": str(get_row_value(row, ["phone", "연락처"], "")).strip(),
                    "email": str(get_row_value(row, ["email", "내부 메일"], "")).strip(),
                    "ext_email": str(get_row_value(row, ["ext_email", "외부 메일"], "")).strip(),
                    "deployed_at": parse_date(get_row_value(row, ["deployed_at", "투입 일자"], "")),
                    "notes": str(get_row_value(row, ["notes", "비고"], "")).strip(),
                }
                if defaults["role"] and defaults["role"] not in PERSON_ROLE_CODES:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = (
                        f"{excel_row_no}행: 유효하지 않은 역할 코드: {defaults['role']}"
                    )
                    continue
                if defaults["system_name"] and not ServiceMaster.objects.filter(name=defaults["system_name"]).exists():
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = (
                        f"{excel_row_no}행: 서비스 마스터 미등록 서비스명: {defaults['system_name']}"
                    )
                    continue
                if defaults["resident"] is None:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = (
                        f"{excel_row_no}행: 유효하지 않은 상주 여부 코드"
                    )
                    continue
                if mgmt_no:
                    existing = PersonMaster.objects.filter(person_mgmt_no=mgmt_no).first()
                    if existing:
                        for key, val in defaults.items():
                            setattr(existing, key, val)
                        existing.save()
                        updated_count += 1
                    elif defaults["name"]:
                        PersonMaster.objects.create(person_mgmt_no=mgmt_no, **defaults)
                        created_count += 1
                    else:
                        skipped_count += 1
                elif defaults["name"]:
                    PersonMaster.objects.create(**defaults)
                    created_count += 1
                else:
                    skipped_count += 1
            messages.success(
                request,
                f"엑셀 import 완료: 업데이트 {updated_count}건 / 인서트 {created_count}건 / 스킵 {skipped_count}건",
            )
            if import_row_errors:
                request.session["row_errors_person"] = import_row_errors
            return redirect(build_list_redirect(request.path, query=query, page=page))

        if action == "save":
            rows = json.loads(request.POST.get("rows_json", "[]"))
            deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
            failed_ids = []
            row_errors = {}
            invalid_roles = set()
            invalid_resident_values = set()
            invalid_service_names = set()
            if deleted_ids:
                try:
                    PersonMaster.objects.filter(pk__in=deleted_ids).delete()
                except Exception as exc:
                    for xid in [x for x in deleted_ids if str(x).isdigit()]:
                        failed_ids.append(xid)
                        row_errors[str(xid)] = f"삭제 실패: {build_error_message(exc)}"

            for row in rows:
                pk = str(row.get("id", "")).strip()
                person_mgmt_no = str(row.get("person_mgmt_no", "")).strip()
                name = str(row.get("name", "")).strip()
                if not pk and not name:
                    continue
                deployed_at_raw = str(row.get("deployed_at") or "").strip()
                deployed_at = parse_date(deployed_at_raw)
                if deployed_at_raw and deployed_at is None:
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "유효하지 않은 날짜"
                    continue
                payload = {
                    "name": name,
                    "employee_no": (row.get("employee_no") or "").strip(),
                    "role": normalize_person_role(row.get("role")),
                    "system_name": (row.get("system_name") or "").strip(),
                    "resident": parse_resident_code(row.get("resident")),
                    "company": (row.get("company") or "").strip(),
                    "phone": (row.get("phone") or "").strip(),
                    "email": (row.get("email") or "").strip(),
                    "ext_email": (row.get("ext_email") or "").strip(),
                    "deployed_at": deployed_at,
                    "notes": (row.get("notes") or "").strip(),
                }
                if payload["role"] and payload["role"] not in PERSON_ROLE_CODES:
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "유효하지 않은 역할 코드"
                    else:
                        invalid_roles.add(payload["role"])
                    continue
                if payload["system_name"] and not ServiceMaster.objects.filter(name=payload["system_name"]).exists():
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "서비스 마스터에 등록된 서비스명만 입력 가능합니다."
                    else:
                        invalid_service_names.add(payload["system_name"])
                    continue
                if payload["resident"] is None:
                    resident_value = str(row.get("resident") or "").strip()
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "유효하지 않은 상주 여부 코드"
                    else:
                        invalid_resident_values.add(resident_value or "(빈값)")
                    continue
                if pk:
                    try:
                        obj = PersonMaster.objects.get(pk=pk)
                        for key, val in payload.items():
                            setattr(obj, key, val)
                        obj.save()
                    except Exception as exc:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = build_error_message(exc)
                elif payload["name"]:
                    try:
                        PersonMaster.objects.create(person_mgmt_no=person_mgmt_no or None, **payload)
                    except Exception as exc:
                        if person_mgmt_no:
                            dup = PersonMaster.objects.filter(person_mgmt_no=person_mgmt_no).values_list("pk", flat=True).first()
                            if dup:
                                failed_ids.append(dup)
                                row_errors[str(dup)] = build_error_message(exc)
            if invalid_roles:
                messages.error(
                    request,
                    "유효하지 않은 역할 코드가 포함되어 저장할 수 없습니다: " + ", ".join(sorted(invalid_roles)),
                )
                row_errors["__global_role__"] = "유효하지 않은 역할 코드 입력"
            if invalid_resident_values:
                messages.error(
                    request,
                    "유효하지 않은 상주 여부 코드가 포함되어 저장할 수 없습니다: "
                    + ", ".join(sorted(invalid_resident_values)),
                )
                row_errors["__global_resident__"] = "유효하지 않은 상주 여부 코드 입력"
            if invalid_service_names:
                messages.error(
                    request,
                    "서비스 마스터 미등록 서비스명으로 저장할 수 없습니다: "
                    + ", ".join(sorted(invalid_service_names)),
                )
                row_errors["__global_service__"] = "서비스 마스터 미등록 서비스명 입력"
            request.session["row_errors_person"] = row_errors
            return redirect(build_list_redirect(request.path, query=query, page=page, failed_ids=failed_ids))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "web/person_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "person_role_codes": PERSON_ROLE_CODES,
            "resident_codes": RESIDENT_CODES,
            "service_names": list(ServiceMaster.objects.values_list("name", flat=True).order_by("name")),
            "failed_ids": failed_ids,
            "row_errors": row_errors,
            "popup_error_summary": summarize_row_errors(row_errors),
        },
    )


@login_required
@permission_required("masters.view_component", raise_exception=True)
def component_master_list(request):
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page", "").strip()
    failed_ids = {int(x) for x in request.GET.get("failed_ids", "").split(",") if x.isdigit()}
    row_errors = request.session.pop("row_errors_component", {})
    qs = Component.objects.all().order_by("asset_mgmt_no")
    if query:
        qs = qs.filter(build_model_text_search_q(Component, query))

    if request.GET.get("export") == "1":
        cols = [
            "asset_mgmt_no",
            "hostname",
            "system_name",
            "server_type",
            "operation_dev",
            "network_zone",
            "platform_type",
            "ip",
            "port",
            "location",
            "mw",
            "os_dbms",
            "url_or_db_name",
            "ssl_domain",
            "cert_format",
            "remark1",
            "remark2",
        ]
        rename_map = {
            "asset_mgmt_no": "자산관리번호",
            "hostname": "Hostname",
            "system_name": "시스템명",
            "server_type": "서버 구분",
            "operation_dev": "운영/개발",
            "network_zone": "네트웍 구분",
            "platform_type": "플랫폼 구분",
            "ip": "IP",
            "port": "Port",
            "location": "위치",
            "mw": "MW",
            "os_dbms": "OS/DBMS",
            "url_or_db_name": "URL/DB명",
            "ssl_domain": "SSL 도메인",
            "cert_format": "인증서 포맷",
            "remark1": "비고1",
            "remark2": "비고2",
        }
        df = pd.DataFrame(list(qs.values(*cols)), columns=cols).rename(columns=rename_map)
        df = df[[rename_map[c] for c in cols]]
        return to_excel_response(df, "component_master.xlsx")

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "import" and request.FILES.get("excel_file"):
            df = pd.read_excel(request.FILES["excel_file"])
            updated_count = 0
            created_count = 0
            skipped_count = 0
            import_row_errors = {}
            for excel_row_no, (_, row) in enumerate(df.iterrows(), start=2):
                mgmt_no = str(get_row_value(row, ["asset_mgmt_no", "자산관리번호"], "")).strip()
                system_name = str(get_row_value(row, ["system_name", "시스템명"], "")).strip()
                hostname = str(get_row_value(row, ["hostname", "Hostname"], "")).strip()
                if not system_name and not hostname:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = (
                        f"{excel_row_no}행: 필수값 누락: 시스템명, Hostname"
                    )
                    continue
                if not system_name:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = f"{excel_row_no}행: 필수값 누락: 시스템명"
                    continue
                if not hostname:
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = f"{excel_row_no}행: 필수값 누락: Hostname"
                    continue
                if system_name and not ServiceMaster.objects.filter(name=system_name).exists():
                    skipped_count += 1
                    import_row_errors[f"import_{excel_row_no}"] = (
                        f"{excel_row_no}행: 서비스 마스터 미등록 시스템명: {system_name}"
                    )
                    continue
                defaults = {
                    "hostname": hostname,
                    "system_name": system_name,
                    "server_type": str(get_row_value(row, ["server_type", "서버 구분"], "")).strip(),
                    "operation_dev": str(get_row_value(row, ["operation_dev", "운영/개발"], "")).strip(),
                    "network_zone": str(get_row_value(row, ["network_zone", "네트웍 구분"], "")).strip(),
                    "platform_type": str(get_row_value(row, ["platform_type", "플랫폼 구분"], "")).strip(),
                    "ip": (str(get_row_value(row, ["ip", "IP"], "")).strip() or None),
                    "port": str(get_row_value(row, ["port", "Port"], "")).strip(),
                    "location": str(get_row_value(row, ["location", "위치"], "")).strip(),
                    "mw": str(get_row_value(row, ["mw", "MW"], "")).strip(),
                    "os_dbms": str(get_row_value(row, ["os_dbms", "OS/DBMS"], "")).strip(),
                    "url_or_db_name": str(get_row_value(row, ["url_or_db_name", "URL/DB명"], "")).strip(),
                    "ssl_domain": str(get_row_value(row, ["ssl_domain", "SSL 도메인"], "")).strip(),
                    "cert_format": str(get_row_value(row, ["cert_format", "인증서 포맷"], "")).strip(),
                    "remark1": str(get_row_value(row, ["remark1", "비고1"], "")).strip(),
                    "remark2": str(get_row_value(row, ["remark2", "비고2"], "")).strip(),
                }
                if mgmt_no:
                    existing = Component.objects.filter(asset_mgmt_no=mgmt_no).first()
                    if existing:
                        for key, val in defaults.items():
                            setattr(existing, key, val)
                        existing.save()
                        updated_count += 1
                    elif defaults["hostname"]:
                        Component.objects.create(asset_mgmt_no=mgmt_no, **defaults)
                        created_count += 1
                    else:
                        skipped_count += 1
                elif defaults["hostname"]:
                    Component.objects.create(**defaults)
                    created_count += 1
                else:
                    skipped_count += 1
            messages.success(
                request,
                f"엑셀 import 완료: 업데이트 {updated_count}건 / 인서트 {created_count}건 / 스킵 {skipped_count}건",
            )
            if import_row_errors:
                request.session["row_errors_component"] = import_row_errors
            return redirect(build_list_redirect(request.path, query=query, page=page))

        if action == "save":
            rows = json.loads(request.POST.get("rows_json", "[]"))
            deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
            failed_ids = []
            row_errors = {}
            invalid_system_names = set()
            if deleted_ids:
                try:
                    Component.objects.filter(pk__in=deleted_ids).delete()
                except Exception as exc:
                    for xid in [x for x in deleted_ids if str(x).isdigit()]:
                        failed_ids.append(xid)
                        row_errors[str(xid)] = f"삭제 실패: {build_error_message(exc)}"

            for row in rows:
                pk = str(row.get("id", "")).strip()
                asset_mgmt_no = str(row.get("asset_mgmt_no", "")).strip()
                hostname = str(row.get("hostname", "")).strip()
                system_name = str(row.get("system_name", "")).strip()
                if not pk and not hostname:
                    continue
                if system_name and not ServiceMaster.objects.filter(name=system_name).exists():
                    if pk:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = "서비스 마스터에 등록된 시스템명만 입력 가능합니다."
                    else:
                        invalid_system_names.add(system_name)
                    continue
                payload = {
                    "hostname": hostname,
                    "system_name": system_name,
                    "server_type": (row.get("server_type") or "").strip(),
                    "operation_dev": (row.get("operation_dev") or "").strip(),
                    "network_zone": (row.get("network_zone") or "").strip(),
                    "platform_type": (row.get("platform_type") or "").strip(),
                    "ip": (row.get("ip") or "").strip() or None,
                    "port": (row.get("port") or "").strip(),
                    "location": (row.get("location") or "").strip(),
                    "mw": (row.get("mw") or "").strip(),
                    "os_dbms": (row.get("os_dbms") or "").strip(),
                    "url_or_db_name": (row.get("url_or_db_name") or "").strip(),
                    "ssl_domain": (row.get("ssl_domain") or "").strip(),
                    "cert_format": (row.get("cert_format") or "").strip(),
                    "remark1": (row.get("remark1") or "").strip(),
                    "remark2": (row.get("remark2") or "").strip(),
                }
                if pk:
                    try:
                        comp = Component.objects.get(pk=pk)
                        for key, val in payload.items():
                            setattr(comp, key, val)
                        comp.save()
                    except Exception as exc:
                        failed_ids.append(pk)
                        row_errors[str(pk)] = build_error_message(exc)
                elif payload["hostname"]:
                    try:
                        Component.objects.create(asset_mgmt_no=asset_mgmt_no or None, **payload)
                    except Exception as exc:
                        if asset_mgmt_no:
                            dup = Component.objects.filter(asset_mgmt_no=asset_mgmt_no).values_list("pk", flat=True).first()
                            if dup:
                                failed_ids.append(dup)
                                row_errors[str(dup)] = build_error_message(exc)
            if invalid_system_names:
                messages.error(
                    request,
                    "서비스 마스터 미등록 시스템명으로 저장할 수 없습니다: " + ", ".join(sorted(invalid_system_names)),
                )
                row_errors["__global__"] = "서비스 마스터 미등록 시스템명 입력"
            request.session["row_errors_component"] = row_errors
            return redirect(build_list_redirect(request.path, query=query, page=page, failed_ids=failed_ids))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "web/component_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "failed_ids": failed_ids,
            "row_errors": row_errors,
            "popup_error_summary": summarize_row_errors(row_errors),
            "service_names": list(ServiceMaster.objects.values_list("name", flat=True).order_by("name")),
        },
    )


@login_required
def ai_asset_search(request):
    query = request.GET.get("q", "").strip()
    results = []
    error = ""

    if query:
        try:
            svc = AssetSearchService()
            results = svc.search(query, k=10)
        except FileNotFoundError:
            error = "AI 인덱스가 없습니다. `python manage.py build_asset_index`를 먼저 실행하세요."

    return render(
        request,
        "web/ai_asset_search.html",
        {
            "q": query,
            "results": results,
            "error": error,
        },
    )
