import re
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from masters.models import ConfigurationMaster, ServiceMaster


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
    return {
        "customer_owner_name": "",
        "appl_owner_name": "",
        "partner_operator_name": "",
        "server_owner_name": "",
        "db_owner_name": "",
    }


def build_person_names_for_role(service_name: str, role: str) -> str:
    return ""


def build_appl_owner_names(service_name: str) -> str:
    """담당 시스템=서비스명이고 역할 표시명이 운영자(코드 OPERATOR)인 담당자 성명, person_mgmt_no 순."""
    return build_person_names_for_role(service_name, "운영자")


def resolve_infra_owner_fields(service_obj: "ServiceMaster | None"):
    """서비스 마스터 필드 + 담당자 마스터(동일 서비스명) 기반 partner_operator(운영자) 보강."""
    fields = map_service_owners_to_asset_fields(service_obj)
    if not service_obj:
        return fields
    live = build_appl_owner_names(service_obj.name)
    if live.strip():
        fields["partner_operator_name"] = live
    return fields


def copy_component_fields(comp: "ConfigurationMaster"):
    """구성정보 마스터 기반으로 InfraAsset 공통 필드를 채운다."""
    return {
        "hostname": comp.hostname or "",
        "server_type": comp.server_type_code.code if comp.server_type_code else "",
        "operation_dev": comp.operation_dev_code.code if comp.operation_dev_code else "",
        "network_zone": comp.network_zone_code.code if comp.network_zone_code else "",
        "platform_type": comp.infra_type_code.code if comp.infra_type_code else "",
        "ip": comp.ip,
        "port": comp.port or "",
        "location": comp.location_code.code if comp.location_code else "",
        "mw": "",
        "runtime": "",
        "os_dbms": "",
        "url_or_db_name": comp.url or "",
        "ssl_domain": "",
        "cert_format": "",
        "remark1": "",
        "remark2": "",
        "extra": {},
    }


def rebuild_infra_assets_from_masters():
    """서비스·자산 마스터 조인 결과로 InfraAsset 전량 재구성 (담당자 반영은 resolve_infra_owner_fields)."""
    from masters.models import ConfigurationMaster, ServiceMaster

    from assets.models import InfraAsset

    to_create = []
    for comp in ConfigurationMaster.objects.all().order_by("asset_mgmt_no"):
        link = comp.service_configuration_mappings.select_related("service").first()
        svc = link.service if link else None
        service_mgmt_no = svc.service_mgmt_no if svc else "UNMAPPED"
        service_name = svc.name if svc else "미매핑"
        smn = compute_system_mgmt_no(service_mgmt_no, comp.asset_mgmt_no)
        owners = resolve_infra_owner_fields(svc if svc else None)
        comp_fields = copy_component_fields(comp)
        to_create.append(
            InfraAsset(
                system_mgmt_no=smn,
                service_mgmt_no=service_mgmt_no,
                asset_mgmt_no=comp.asset_mgmt_no,
                service_name=service_name,
                customer_owner_name=owners["customer_owner_name"],
                appl_owner_name=owners["appl_owner_name"],
                partner_operator_name=owners["partner_operator_name"],
                server_owner_name=owners["server_owner_name"],
                db_owner_name=owners["db_owner_name"],
                component=comp,
                **comp_fields,
            )
        )

    with transaction.atomic():
        InfraAsset.objects.all().delete()
        if to_create:
            InfraAsset.objects.bulk_create(to_create, batch_size=500)
