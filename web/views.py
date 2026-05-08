import json
from io import BytesIO
from urllib.parse import urlencode

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ai_search.services import AssetSearchService
from assets.models import InfraAsset
from core.models import AuditLog, Code
from masters.models import (
    Component,
    ConfigurationMaster,
    PersonMaster,
    ServiceAttribute,
    ServiceMaster,
)
from masters.service_person_grid import SERVICE_PERSON_GRID_COLUMNS, attribute_codes_for_grid


def split_csv_tokens(raw):
    return [t.strip() for t in str(raw or "").split(",") if t.strip()]


def join_csv_tokens(values):
    return ", ".join(v for v in values if str(v or "").strip())


def parse_person_ids_from_attr_value(raw):
    ids = []
    for token in split_csv_tokens(raw):
        if token.isdigit():
            ids.append(int(token))
    return ids


def person_option_map_by_role():
    from collections import defaultdict

    grouped = defaultdict(list)
    role_codes_needed = [c["role_code"] for c in SERVICE_PERSON_GRID_COLUMNS]
    qs = PersonMaster.objects.select_related("role_code").order_by("name", "employee_no")
    for p in qs:
        rc = getattr(p.role_code, "code", None) if p.role_code else None
        if rc not in role_codes_needed:
            continue
        grouped[rc].append({"id": p.pk, "label": f"{p.name} ({p.employee_no})"})
    return grouped


def service_person_columns_with_options():
    grouped = person_option_map_by_role()
    return [{**col, "options": list(grouped[col["role_code"]])} for col in SERVICE_PERSON_GRID_COLUMNS]


def person_label_map():
    return {p.pk: (p.name or "").strip() for p in PersonMaster.objects.all().order_by("name", "employee_no")}


def service_lookup_maps():
    by_name = {}
    by_mgmt = {}
    for s in ServiceMaster.objects.all().order_by("service_mgmt_no"):
        by_name[s.name] = s
        by_mgmt[s.service_mgmt_no] = s
    return by_name, by_mgmt


def set_service_attr_person_ids(service_obj, acode, person_ids):
    clean_ids = sorted({int(x) for x in person_ids if str(x).isdigit() or isinstance(x, int)})
    if clean_ids:
        ServiceAttribute.objects.update_or_create(
            service=service_obj,
            attribute_code_id=acode,
            defaults={"value": join_csv_tokens([str(i) for i in clean_ids])},
        )
    else:
        ServiceAttribute.objects.filter(service=service_obj, attribute_code_id=acode).delete()


def sync_service_person_attributes_from_service_grid_row(service_obj, row):
    p_qs = PersonMaster.objects.all().order_by("name", "employee_no")
    label_to_id = {f"{p.name}({p.employee_no})": p.pk for p in p_qs}
    name_to_id = {p.name: p.pk for p in p_qs}
    emp_to_id = {p.employee_no: p.pk for p in p_qs}
    for col in SERVICE_PERSON_GRID_COLUMNS:
        acode = col["attribute_code"]
        key = f"attr_{acode}"
        parsed_ids = []
        for token in split_csv_tokens(row.get(key)):
            if token.isdigit() and PersonMaster.objects.filter(pk=int(token)).exists():
                parsed_ids.append(int(token))
            elif token in label_to_id:
                parsed_ids.append(label_to_id[token])
            elif token in name_to_id:
                parsed_ids.append(name_to_id[token])
            elif token in emp_to_id:
                parsed_ids.append(emp_to_id[token])
        set_service_attr_person_ids(service_obj, acode, parsed_ids)


def sync_person_service_assignments_from_row(person_obj, row):
    by_name, by_mgmt = service_lookup_maps()
    role_to_acode = {c["role_code"]: c["attribute_code"] for c in SERVICE_PERSON_GRID_COLUMNS}
    target_role = getattr(person_obj.role_code, "code", "") if person_obj.role_code else ""
    target_acode = role_to_acode.get(target_role)

    selected_service_ids = set()
    for token in split_csv_tokens(row.get("assigned_service_names")):
        svc = by_name.get(token) or by_mgmt.get(token)
        if svc:
            selected_service_ids.add(svc.pk)

    all_services = list(ServiceMaster.objects.all())
    all_acodes = list(role_to_acode.values())

    # 역할 변경/서비스 해제 케이스 포함: 먼저 모든 역할 속성에서 현재 담당자 제거
    for svc in all_services:
        for acode in all_acodes:
            curr = ServiceAttribute.objects.filter(service=svc, attribute_code_id=acode).first()
            curr_set = set(parse_person_ids_from_attr_value(curr.value if curr else ""))
            if person_obj.pk in curr_set:
                curr_set.discard(person_obj.pk)
                set_service_attr_person_ids(svc, acode, sorted(curr_set))

    # 현재 선택 역할의 서비스 목록에만 다시 추가
    if target_acode:
        for svc in all_services:
            if svc.pk not in selected_service_ids:
                continue
            curr = ServiceAttribute.objects.filter(service=svc, attribute_code_id=target_acode).first()
            curr_set = set(parse_person_ids_from_attr_value(curr.value if curr else ""))
            curr_set.add(person_obj.pk)
            set_service_attr_person_ids(svc, target_acode, sorted(curr_set))


def parse_date(val):
    if val in (None, ""):
        return None
    dt = pd.to_datetime(val, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.date()


def to_excel_response(df, filename):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    content = out.getvalue()
    res = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    res["Content-Disposition"] = f'attachment; filename="{filename}"'
    return res


def to_excel_multi_response(sheet_map, filename):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for sheet_name, df in sheet_map.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    content = out.getvalue()
    res = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    res["Content-Disposition"] = f'attachment; filename="{filename}"'
    return res


def code_reference_df(group_keys):
    rows = []
    for gk in group_keys:
        for code, name in (
            Code.objects.filter(group__key=gk, group__is_active=True, is_active=True)
            .order_by("sort_order", "code")
            .values_list("code", "name")
        ):
            rows.append({"코드그룹": gk, "코드값": code, "코드명": name})
    return pd.DataFrame(rows, columns=["코드그룹", "코드값", "코드명"])


def build_model_text_search_q(model_class, query):
    text = (query or "").strip()
    if not text:
        return Q()
    q = Q()
    for field in model_class._meta.fields:
        if field.get_internal_type() in {
            "CharField",
            "TextField",
            "EmailField",
            "URLField",
            "GenericIPAddressField",
        }:
            q |= Q(**{f"{field.name}__icontains": text})
    return q


def build_list_redirect(path, query="", page="", failed_ids=None):
    params = {}
    if query:
        params["q"] = query
    if page:
        params["page"] = page
    if failed_ids:
        params["failed_ids"] = ",".join(str(x) for x in failed_ids)
    return f"{path}?{urlencode(params)}" if params else path


def code_values(group_key):
    return list(
        Code.objects.filter(group__key=group_key, group__is_active=True, is_active=True)
        .order_by("sort_order", "code")
        .values_list("code", flat=True)
    )


def code_choice_options(group_key):
    """그리드 셀렉트용: value는 code, 라벨은 Code.name(표시명)."""
    return list(
        Code.objects.filter(group__key=group_key, group__is_active=True, is_active=True)
        .order_by("sort_order", "code")
        .values("code", "name")
    )


# 담당자 역할 코드 개명 이전 코드값 → 현재 코드값 (엑셀 재업로드 등)
LEGACY_PERSON_ROLE_CODES = {"APPL_OPS": "OPERATOR", "INFRA_OPS": "INFRA_OPERATOR"}


def code_from_value(group_key, value):
    v = (value or "").strip()
    if not v:
        return None
    if group_key == "person_role" and v in LEGACY_PERSON_ROLE_CODES:
        v = LEGACY_PERSON_ROLE_CODES[v]
    return Code.objects.filter(group__key=group_key, code=v, group__is_active=True, is_active=True).first()


def audit_actor_label(request):
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        name = getattr(user, "username", "") or getattr(user, "get_username", lambda: "")()
        return (name or str(getattr(user, "pk", ""))).strip() or "unknown"
    return ""


@login_required
def dashboard(request):
    context = {
        "counts": {
            "infra": InfraAsset.objects.count(),
            "service": ServiceMaster.objects.count(),
            "person": PersonMaster.objects.count(),
            "component": Component.objects.count(),
            "configuration": ConfigurationMaster.objects.count(),
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
        df = pd.DataFrame(
            list(
                qs.values(
                    "system_mgmt_no",
                    "service_name",
                    "hostname",
                    "customer_owner_name",
                    "appl_owner_name",
                    "partner_operator_name",
                    "server_owner_name",
                    "db_owner_name",
                    "server_type",
                    "operation_dev",
                    "network_zone",
                    "platform_type",
                    "ip",
                    "port",
                    "location",
                    "mw",
                    "runtime",
                    "os_dbms",
                    "url_or_db_name",
                    "ssl_domain",
                    "cert_format",
                    "remark1",
                    "remark2",
                )
            )
        )
        return to_excel_response(df, "infra_assets.xlsx")
    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "web/asset_list.html", {"assets": page_obj.object_list, "page_obj": page_obj, "q": query})


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
    attr_codes = attribute_codes_for_grid()
    qs = (
        ServiceMaster.objects.select_related(
            "category_code", "status_code", "build_type_code", "itgc_code", "service_grade_code"
        )
        .prefetch_related(
            Prefetch(
                "service_attributes",
                queryset=ServiceAttribute.objects.filter(attribute_code_id__in=attr_codes),
            )
        )
        .order_by("service_mgmt_no")
    )
    if query:
        qs = qs.filter(build_model_text_search_q(ServiceMaster, query))

    if request.GET.get("export") == "1":
        p_label_map = person_label_map()
        rows = []
        for s in qs:
            role_map = {}
            for sa in s.service_attributes.all():
                role_map[sa.attribute_code_id] = join_csv_tokens(
                    [p_label_map.get(pid, str(pid)) for pid in parse_person_ids_from_attr_value(sa.value)]
                )
            row = {
                "서비스ID": s.service_mgmt_no,
                "서비스명": s.name,
                "분류": getattr(s.category_code, "code", ""),
                "상태": getattr(s.status_code, "code", ""),
                "구축": getattr(s.build_type_code, "code", ""),
                "ITGC": getattr(s.itgc_code, "code", ""),
                "등급": getattr(s.service_grade_code, "code", ""),
                "오픈일": s.opened_at,
                "종료일": s.ended_at,
                "설명": s.description,
            }
            for col in SERVICE_PERSON_GRID_COLUMNS:
                row[col["label"]] = role_map.get(col["attribute_code"], "")
            rows.append(row)
        main_df = pd.DataFrame(rows)
        ref_df = code_reference_df(["service_category", "service_status", "build_type", "yn_flag", "service_grade"])
        return to_excel_multi_response({"서비스마스터": main_df, "코드참조": ref_df}, "service_master.xlsx")

    if request.method == "POST" and request.POST.get("action") == "import":
        up = request.FILES.get("excel_file")
        if up:
            df = pd.read_excel(up)
            actor = audit_actor_label(request)
            for _, rec in df.fillna("").iterrows():
                payload = {
                    "name": str(rec.get("서비스명", "")).strip(),
                    "category_code": code_from_value("service_category", rec.get("분류")),
                    "status_code": code_from_value("service_status", rec.get("상태")),
                    "build_type_code": code_from_value("build_type", rec.get("구축")),
                    "itgc_code": code_from_value("yn_flag", rec.get("ITGC")),
                    "service_grade_code": code_from_value("service_grade", rec.get("등급")),
                    "opened_at": parse_date(rec.get("오픈일")),
                    "ended_at": parse_date(rec.get("종료일")),
                    "description": str(rec.get("설명", "")).strip(),
                }
                svc_id = str(rec.get("서비스ID", "")).strip()
                obj = ServiceMaster.objects.filter(service_mgmt_no=svc_id).first() if svc_id else None
                if obj:
                    for k, v in payload.items():
                        setattr(obj, k, v)
                    obj.updated_by = actor
                    obj.save()
                elif payload["name"]:
                    ServiceMaster.objects.create(**payload, created_by=actor, updated_by=actor)
            messages.success(request, "서비스 마스터 엑셀 업로드 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    if request.method == "POST" and request.POST.get("action") == "save":
        rows = json.loads(request.POST.get("rows_json", "[]"))
        deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
        actor = audit_actor_label(request)
        ServiceMaster.objects.filter(pk__in=deleted_ids).delete()
        for row in rows:
            pk = str(row.get("id", "")).strip()
            payload = {
                "name": (row.get("name") or "").strip(),
                "category_code": code_from_value("service_category", row.get("category_code")),
                "status_code": code_from_value("service_status", row.get("status_code")),
                "build_type_code": code_from_value("build_type", row.get("build_type_code")),
                "itgc_code": code_from_value("yn_flag", row.get("itgc_code")),
                "service_grade_code": code_from_value("service_grade", row.get("service_grade_code")),
                "opened_at": parse_date(row.get("opened_at")),
                "ended_at": parse_date(row.get("ended_at")),
                "description": (row.get("description") or "").strip(),
            }
            obj = None
            if pk:
                obj = ServiceMaster.objects.get(pk=pk)
                for k, v in payload.items():
                    setattr(obj, k, v)
                obj.updated_by = actor
                obj.save()
            elif payload["name"]:
                obj = ServiceMaster.objects.create(**payload, created_by=actor, updated_by=actor)
        messages.success(request, "서비스 마스터 저장 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    p_label_map = person_label_map()
    for s in page_obj.object_list:
        raw_sa = {}
        for sa in s.service_attributes.all():
            raw_sa[sa.attribute_code_id] = str(sa.value or "").strip()
        s.person_slot_values = {
            col["attribute_code"]: join_csv_tokens(
                [
                    p_label_map.get(pid, str(pid))
                    for pid in parse_person_ids_from_attr_value(raw_sa.get(col["attribute_code"], ""))
                ]
            )
            for col in SERVICE_PERSON_GRID_COLUMNS
        }
    return render(
        request,
        "web/service_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "service_category_codes": code_values("service_category"),
            "service_status_codes": code_values("service_status"),
            "build_type_codes": code_values("build_type"),
            "yn_flag_codes": code_values("yn_flag"),
            "service_grade_codes": code_values("service_grade"),
            "service_person_columns": service_person_columns_with_options(),
        },
    )


@login_required
@permission_required("masters.view_personmaster", raise_exception=True)
def person_master_list(request):
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page", "").strip()
    qs = PersonMaster.objects.select_related("role_code", "status_code").order_by("person_mgmt_no")
    if query:
        qs = qs.filter(build_model_text_search_q(PersonMaster, query))

    if request.GET.get("export") == "1":
        role_to_acode = {c["role_code"]: c["attribute_code"] for c in SERVICE_PERSON_GRID_COLUMNS}
        sa_lookup = {
            (sa.service_id, sa.attribute_code_id): set(parse_person_ids_from_attr_value(sa.value))
            for sa in ServiceAttribute.objects.filter(attribute_code_id__in=attribute_codes_for_grid())
        }
        services = list(ServiceMaster.objects.all().order_by("service_mgmt_no"))
        rows = []
        for p in qs:
            my_acode = role_to_acode.get(getattr(p.role_code, "code", "") if p.role_code else "")
            names = [svc.name for svc in services if my_acode and p.pk in sa_lookup.get((svc.pk, my_acode), set())]
            rows.append(
                {
                    "담당자ID": p.person_mgmt_no,
                    "성명": p.name,
                    "사번": p.employee_no,
                    "담당업무": join_csv_tokens(names),
                    "역할": getattr(p.role_code, "code", ""),
                    "회사명": p.company,
                    "전화번호": p.phone,
                    "내부메일": p.email,
                    "외부메일": p.external_email,
                    "상태": getattr(p.status_code, "code", ""),
                    "투입일": p.deployed_at,
                    "종료일": p.ended_at,
                }
            )
        main_df = pd.DataFrame(rows)
        ref_df = code_reference_df(["person_role", "person_status"])
        return to_excel_multi_response({"담당자마스터": main_df, "코드참조": ref_df}, "person_master.xlsx")

    if request.method == "POST" and request.POST.get("action") == "import":
        up = request.FILES.get("excel_file")
        if up:
            df = pd.read_excel(up)
            row_refs = []
            for _, rec in df.fillna("").iterrows():
                payload = {
                    "employee_no": str(rec.get("사번", "")).strip(),
                    "name": str(rec.get("성명", "")).strip(),
                    "role_code": code_from_value("person_role", rec.get("역할")),
                    "company": str(rec.get("회사명", "")).strip(),
                    "phone": str(rec.get("전화번호", "")).strip(),
                    "email": str(rec.get("내부메일", "")).strip(),
                    "external_email": str(rec.get("외부메일", "")).strip(),
                    "status_code": code_from_value("person_status", rec.get("상태")),
                    "deployed_at": parse_date(rec.get("투입일")),
                    "ended_at": parse_date(rec.get("종료일")),
                }
                person_id = str(rec.get("담당자ID", "")).strip()
                obj = PersonMaster.objects.filter(person_mgmt_no=person_id).first() if person_id else None
                if obj:
                    for k, v in payload.items():
                        setattr(obj, k, v)
                    obj.save()
                    row_refs.append((obj, {"assigned_service_names": str(rec.get("담당업무", "")).strip()}))
                elif payload["name"] and payload["employee_no"]:
                    obj = PersonMaster.objects.create(**payload)
                    row_refs.append((obj, {"assigned_service_names": str(rec.get("담당업무", "")).strip()}))
            for person_obj, row in row_refs:
                sync_person_service_assignments_from_row(person_obj, row)
            messages.success(request, "담당자 마스터 엑셀 업로드 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    if request.method == "POST" and request.POST.get("action") == "save":
        rows = json.loads(request.POST.get("rows_json", "[]"))
        deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
        PersonMaster.objects.filter(pk__in=deleted_ids).delete()
        row_refs = []
        for row in rows:
            pk = str(row.get("id", "")).strip()
            payload = {
                "employee_no": (row.get("employee_no") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "role_code": code_from_value("person_role", row.get("role_code")),
                "company": (row.get("company") or "").strip(),
                "phone": (row.get("phone") or "").strip(),
                "email": (row.get("email") or "").strip(),
                "external_email": (row.get("external_email") or "").strip(),
                "status_code": code_from_value("person_status", row.get("status_code")),
                "deployed_at": parse_date(row.get("deployed_at")),
                "ended_at": parse_date(row.get("ended_at")),
            }
            if pk:
                obj = PersonMaster.objects.get(pk=pk)
                for k, v in payload.items():
                    setattr(obj, k, v)
                obj.save()
                row_refs.append((obj, row))
            elif payload["name"]:
                obj = PersonMaster.objects.create(**payload)
                row_refs.append((obj, row))
        for person_obj, row in row_refs:
            sync_person_service_assignments_from_row(person_obj, row)
        messages.success(request, "담당자 마스터 저장 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    sa_by_service_role = {}
    for sa in ServiceAttribute.objects.filter(attribute_code_id__in=attribute_codes_for_grid()):
        sa_by_service_role[(sa.service_id, sa.attribute_code_id)] = set(parse_person_ids_from_attr_value(sa.value))

    service_rows = list(ServiceMaster.objects.all().order_by("service_mgmt_no"))
    role_to_acode = {c["role_code"]: c["attribute_code"] for c in SERVICE_PERSON_GRID_COLUMNS}
    for p in page_obj.object_list:
        my_services = []
        my_role = getattr(p.role_code, "code", "") if p.role_code else ""
        my_acode = role_to_acode.get(my_role)
        for svc in service_rows:
            if my_acode and p.pk in sa_by_service_role.get((svc.pk, my_acode), set()):
                my_services.append(svc.name)
        p.assigned_service_names = join_csv_tokens(my_services)

    return render(
        request,
        "web/person_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "person_role_options": code_choice_options("person_role"),
            "person_status_codes": code_values("person_status"),
            "service_name_options": [s.name for s in service_rows],
        },
    )


@login_required
@permission_required("masters.view_configurationmaster", raise_exception=True)
def configuration_master_list(request):
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page", "").strip()
    qs = ConfigurationMaster.objects.select_related(
        "server_type_code", "operation_dev_code", "infra_type_code", "location_code", "network_zone_code"
    ).order_by("asset_mgmt_no")
    if query:
        qs = qs.filter(build_model_text_search_q(ConfigurationMaster, query))

    if request.GET.get("export") == "1":
        rows = [
            {
                "구성ID": c.asset_mgmt_no,
                "구성명": c.hostname,
                "구성유형": getattr(c.server_type_code, "code", ""),
                "운영/개발": getattr(c.operation_dev_code, "code", ""),
                "인프라구분": getattr(c.infra_type_code, "code", ""),
                "위치": getattr(c.location_code, "code", ""),
                "네트워크": getattr(c.network_zone_code, "code", ""),
                "IP": c.ip or "",
                "Port": c.port,
                "URL": c.url,
            }
            for c in qs
        ]
        main_df = pd.DataFrame(rows)
        ref_df = code_reference_df(["config_type", "operation_type", "infra_type", "infra_location", "network_zone"])
        return to_excel_multi_response({"구성정보마스터": main_df, "코드참조": ref_df}, "configuration_master.xlsx")

    if request.method == "POST" and request.POST.get("action") == "import":
        up = request.FILES.get("excel_file")
        actor = audit_actor_label(request)
        if up:
            df = pd.read_excel(up)
            for _, rec in df.fillna("").iterrows():
                payload = {
                    "hostname": str(rec.get("구성명", "")).strip(),
                    "server_type_code": code_from_value("config_type", rec.get("구성유형")),
                    "operation_dev_code": code_from_value("operation_type", rec.get("운영/개발")),
                    "infra_type_code": code_from_value("infra_type", rec.get("인프라구분")),
                    "location_code": code_from_value("infra_location", rec.get("위치")),
                    "network_zone_code": code_from_value("network_zone", rec.get("네트워크")),
                    "ip": str(rec.get("IP", "")).strip() or None,
                    "port": str(rec.get("Port", "")).strip(),
                    "url": str(rec.get("URL", "")).strip(),
                }
                cfg_id = str(rec.get("구성ID", "")).strip()
                obj = ConfigurationMaster.objects.filter(asset_mgmt_no=cfg_id).first() if cfg_id else None
                if obj:
                    for k, v in payload.items():
                        setattr(obj, k, v)
                    obj.updated_by = actor
                    obj.save()
                elif payload["hostname"]:
                    ConfigurationMaster.objects.create(**payload, created_by=actor, updated_by=actor)
            messages.success(request, "구성정보 마스터 엑셀 업로드 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    if request.method == "POST" and request.POST.get("action") == "save":
        rows = json.loads(request.POST.get("rows_json", "[]"))
        deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
        actor = audit_actor_label(request)
        ConfigurationMaster.objects.filter(pk__in=deleted_ids).delete()
        for row in rows:
            pk = str(row.get("id", "")).strip()
            payload = {
                "hostname": (row.get("hostname") or "").strip(),
                "server_type_code": code_from_value("config_type", row.get("server_type_code")),
                "operation_dev_code": code_from_value("operation_type", row.get("operation_dev_code")),
                "infra_type_code": code_from_value("infra_type", row.get("infra_type_code")),
                "location_code": code_from_value("infra_location", row.get("location_code")),
                "network_zone_code": code_from_value("network_zone", row.get("network_zone_code")),
                "ip": (row.get("ip") or "").strip() or None,
                "port": (row.get("port") or "").strip(),
                "url": (row.get("url") or "").strip(),
            }
            if pk:
                obj = ConfigurationMaster.objects.get(pk=pk)
                for k, v in payload.items():
                    setattr(obj, k, v)
                obj.updated_by = actor
                obj.save()
            elif payload["hostname"]:
                ConfigurationMaster.objects.create(**payload, created_by=actor, updated_by=actor)
        messages.success(request, "구성정보 마스터 저장 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "web/configuration_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "config_type_codes": code_values("config_type"),
            "operation_type_codes": code_values("operation_type"),
            "infra_type_codes": code_values("infra_type"),
            "infra_location_codes": code_values("infra_location"),
            "network_zone_codes": code_values("network_zone"),
        },
    )


@login_required
@permission_required("masters.view_component", raise_exception=True)
def component_master_list(request):
    query = request.GET.get("q", "").strip()
    page = request.GET.get("page", "").strip()
    qs = Component.objects.select_related("component_type_code", "support_status_code").order_by("component_mgmt_no")
    if query:
        qs = qs.filter(build_model_text_search_q(Component, query))

    if request.GET.get("export") == "1":
        rows = [
            {
                "컴포넌트ID": c.component_mgmt_no,
                "컴포넌트명": c.product_name,
                "버전": c.version,
                "유형": getattr(c.component_type_code, "code", ""),
                "벤더명": c.vendor_name,
                "CPE": c.cpe_name,
                "EOS": c.eos_date,
                "EOL": c.eol_date,
                "지원여부": getattr(c.support_status_code, "code", ""),
            }
            for c in qs
        ]
        main_df = pd.DataFrame(rows)
        ref_df = code_reference_df(["component_type", "support_status"])
        return to_excel_multi_response({"컴포넌트마스터": main_df, "코드참조": ref_df}, "component_master.xlsx")

    if request.method == "POST" and request.POST.get("action") == "import":
        up = request.FILES.get("excel_file")
        actor = audit_actor_label(request)
        if up:
            df = pd.read_excel(up)
            for _, rec in df.fillna("").iterrows():
                payload = {
                    "product_name": str(rec.get("컴포넌트명", "")).strip(),
                    "version": str(rec.get("버전", "")).strip(),
                    "component_type_code": code_from_value("component_type", rec.get("유형")),
                    "vendor_name": str(rec.get("벤더명", "")).strip(),
                    "cpe_name": str(rec.get("CPE", "")).strip(),
                    "eos_date": parse_date(rec.get("EOS")),
                    "eol_date": parse_date(rec.get("EOL")),
                    "support_status_code": code_from_value("support_status", rec.get("지원여부")),
                }
                cmp_id = str(rec.get("컴포넌트ID", "")).strip()
                obj = Component.objects.filter(component_mgmt_no=cmp_id).first() if cmp_id else None
                if obj:
                    for k, v in payload.items():
                        setattr(obj, k, v)
                    obj.updated_by = actor
                    obj.save()
                elif payload["product_name"]:
                    Component.objects.create(**payload, created_by=actor, updated_by=actor)
            messages.success(request, "컴포넌트 마스터 엑셀 업로드 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    if request.method == "POST" and request.POST.get("action") == "save":
        rows = json.loads(request.POST.get("rows_json", "[]"))
        deleted_ids = json.loads(request.POST.get("deleted_ids_json", "[]"))
        actor = audit_actor_label(request)
        Component.objects.filter(pk__in=deleted_ids).delete()
        for row in rows:
            pk = str(row.get("id", "")).strip()
            payload = {
                "component_type_code": code_from_value("component_type", row.get("component_type_code")),
                "product_name": (row.get("product_name") or "").strip(),
                "version": (row.get("version") or "").strip(),
                "vendor_name": (row.get("vendor_name") or "").strip(),
                "cpe_name": (row.get("cpe_name") or "").strip(),
                "eos_date": parse_date(row.get("eos_date")),
                "eol_date": parse_date(row.get("eol_date")),
                "support_status_code": code_from_value("support_status", row.get("support_status_code")),
            }
            if pk:
                obj = Component.objects.get(pk=pk)
                for k, v in payload.items():
                    setattr(obj, k, v)
                obj.updated_by = actor
                obj.save()
            elif payload["product_name"]:
                Component.objects.create(**payload, created_by=actor, updated_by=actor)
        messages.success(request, "컴포넌트 마스터 저장 완료")
        return redirect(build_list_redirect(request.path, query=query, page=page))

    paginator = Paginator(qs, 100)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "web/component_master_list.html",
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "q": query,
            "component_type_codes": code_values("component_type"),
            "support_status_codes": code_values("support_status"),
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
    return render(request, "web/ai_asset_search.html", {"q": query, "results": results, "error": error})
