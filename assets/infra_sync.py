import re
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from masters.models import Component, ServiceMaster


def last_three_digits_from_code(code: str) -> str:
    """서비스/자산 관리번호 문자열에서 마지막 세 자리 숫자(연속 숫자 꼬리). 없으면 '000'."""
    digits = re.sub(r"\D", "", str(code or ""))
    if not digits:
        return "000"
    if len(digits) >= 3:
        return digits[-3:]
    return digits.zfill(3)


def compute_system_mgmt_no(service_mgmt_no: str, asset_mgmt_no: str) -> str:
    return f"SA{last_three_digits_from_code(service_mgmt_no)}{last_three_digits_from_code(asset_mgmt_no)}"


def map_service_owners_to_asset_fields(service_obj: "ServiceMaster | None"):
    if not service_obj:
        return {"customer_owner_name": "", "appl_owner_name": "", "partner_operator_name": ""}
    return {
        "customer_owner_name": service_obj.customer_owner or "",
        "appl_owner_name": service_obj.partner_operator or "",
        "partner_operator_name": service_obj.appl_owner or "",
    }


def build_appl_owner_names(service_name: str) -> str:
    from masters.models import PersonMaster

    target = str(service_name or "").strip()
    if not target:
        return ""
    names = list(
        PersonMaster.objects.filter(system_name=target)
        .order_by("person_mgmt_no", "name")
        .values_list("name", flat=True)
    )
    unique_names = list(dict.fromkeys([name.strip() for name in names if str(name).strip()]))
    return "; ".join(unique_names)


def resolve_infra_owner_fields(service_obj: "ServiceMaster | None"):
    """서비스 마스터 필드 + 담당자 마스터(동일 서비스명) 기반 Appl. 운영자 보강."""
    fields = map_service_owners_to_asset_fields(service_obj)
    if not service_obj:
        return fields
    live = build_appl_owner_names(service_obj.name)
    if live.strip():
        fields["partner_operator_name"] = live
    return fields


def copy_component_fields(comp: "Component"):
    """자산 마스터에서 system_name(조인 키)을 제외한 필드."""
    return {
        "hostname": comp.hostname or "",
        "server_type": comp.server_type or "",
        "operation_dev": comp.operation_dev or "",
        "network_zone": comp.network_zone or "",
        "platform_type": comp.platform_type or "",
        "ip": comp.ip,
        "port": comp.port or "",
        "location": comp.location or "",
        "mw": comp.mw or "",
        "os_dbms": comp.os_dbms or "",
        "url_or_db_name": comp.url_or_db_name or "",
        "ssl_domain": comp.ssl_domain or "",
        "cert_format": comp.cert_format or "",
        "remark1": comp.remark1 or "",
        "remark2": comp.remark2 or "",
        "extra": comp.extra if isinstance(comp.extra, dict) else {},
    }


def rebuild_infra_assets_from_masters():
    """서비스·자산 마스터 조인 결과로 InfraAsset 전량 재구성 (담당자 반영은 resolve_infra_owner_fields)."""
    from masters.models import Component, ServiceMaster

    from assets.models import InfraAsset

    svc_by_name = {}
    for s in ServiceMaster.objects.all():
        key = (s.name or "").strip()
        if key:
            svc_by_name[key] = s

    to_create = []
    for comp in Component.objects.exclude(system_name="").order_by("system_name", "asset_mgmt_no"):
        key = (comp.system_name or "").strip()
        svc = svc_by_name.get(key)
        if not svc:
            continue
        smn = compute_system_mgmt_no(svc.service_mgmt_no, comp.asset_mgmt_no)
        owners = resolve_infra_owner_fields(svc)
        comp_fields = copy_component_fields(comp)
        to_create.append(
            InfraAsset(
                system_mgmt_no=smn,
                service_mgmt_no=svc.service_mgmt_no,
                asset_mgmt_no=comp.asset_mgmt_no,
                service_name=svc.name,
                customer_owner_name=owners["customer_owner_name"],
                appl_owner_name=owners["appl_owner_name"],
                partner_operator_name=owners["partner_operator_name"],
                component=comp,
                **comp_fields,
            )
        )

    with transaction.atomic():
        InfraAsset.objects.all().delete()
        if to_create:
            InfraAsset.objects.bulk_create(to_create, batch_size=500)
