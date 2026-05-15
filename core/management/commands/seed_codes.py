from django.core.management.base import BaseCommand

from core.models import Code, CodeGroup
from masters.models import Component, ConfigurationMaster
from masters.service_person_grid import ensure_service_duty_attribute_code, ensure_service_person_attribute_codes


# 이전 component_type 코드 → 새 코드 (seed 후 비활성화되기 전에 FK를 옮김)
LEGACY_COMPONENT_TYPE_CODE_MAP = {
    "APP": "기타",
    "MIDDLEWARE": "middleware",
    "OS": "OS",
    "DB": "DB",
}

# 이전 operation_type 코드 → 새 코드
LEGACY_OPERATION_TYPE_CODE_MAP = {
    "OPS": "운영",
    "DEV": "개발",
    "BOTH": "운영",  # 운영/개발 통합 → 운영으로 흡수
}

# 이전 config_type 코드 → 새 코드
LEGACY_CONFIG_TYPE_CODE_MAP = {
    "ETC": "기타",
    "CACHE": "기타",
}

# 이전 infra_type 코드 → 새 코드
LEGACY_INFRA_TYPE_CODE_MAP = {
    "ONPREM": "OnPrem",
    "AZURE": "기타",
    "GCP": "기타",
}

# 이전 infra_location 코드 → 새 코드
LEGACY_INFRA_LOCATION_CODE_MAP = {
    "DC1": "판교",
    "DC2": "청주",
}

# 이전 network_zone 코드 → 새 코드
LEGACY_NETWORK_ZONE_CODE_MAP = {
    "INTERNAL": "내부망",
    "EXTERNAL": "외부망",
}


def migrate_component_type_foreign_keys():
    """컴포넌트 유형 코드 체계 변경 시 기존 Component FK를 새 Code 행으로 이전한다."""
    for old_code, new_code in LEGACY_COMPONENT_TYPE_CODE_MAP.items():
        if old_code == new_code:
            continue
        old = Code.objects.filter(group__key="component_type", code=old_code).first()
        new = Code.objects.filter(group__key="component_type", code=new_code).first()
        if old and new and old.pk != new.pk:
            Component.objects.filter(component_type_code=old).update(component_type_code=new)


def migrate_operation_type_foreign_keys():
    """운영/개발 코드 체계 변경 시 기존 ConfigurationMaster FK를 새 Code 행으로 이전한다."""
    for old_code, new_code in LEGACY_OPERATION_TYPE_CODE_MAP.items():
        if old_code == new_code:
            continue
        old = Code.objects.filter(group__key="operation_type", code=old_code).first()
        new = Code.objects.filter(group__key="operation_type", code=new_code).first()
        if old and new and old.pk != new.pk:
            ConfigurationMaster.objects.filter(operation_dev_code=old).update(operation_dev_code=new)


def _migrate_config_master_fk(group_key: str, attr: str, mapping: dict[str, str]) -> None:
    """ConfigurationMaster의 단일 FK 필드를 group_key 코드 매핑에 따라 일괄 이전한다."""
    for old_code, new_code in mapping.items():
        if old_code == new_code:
            continue
        old = Code.objects.filter(group__key=group_key, code=old_code).first()
        new = Code.objects.filter(group__key=group_key, code=new_code).first()
        if old and new and old.pk != new.pk:
            ConfigurationMaster.objects.filter(**{attr: old}).update(**{attr: new})


def migrate_config_type_foreign_keys():
    _migrate_config_master_fk("config_type", "server_type_code", LEGACY_CONFIG_TYPE_CODE_MAP)


def migrate_infra_type_foreign_keys():
    _migrate_config_master_fk("infra_type", "infra_type_code", LEGACY_INFRA_TYPE_CODE_MAP)


def migrate_infra_location_foreign_keys():
    _migrate_config_master_fk("infra_location", "location_code", LEGACY_INFRA_LOCATION_CODE_MAP)


def migrate_network_zone_foreign_keys():
    _migrate_config_master_fk("network_zone", "network_zone_code", LEGACY_NETWORK_ZONE_CODE_MAP)


SEED_GROUPS = {
    "yn_flag": [("예", "Y"), ("아니오", "N")],
    "service_category": [
        ("경영지원", "경영지원"),
        ("기업문화", "기업문화"),
        ("영업", "영업"),
        ("재무", "재무"),
        ("R&D", "R&D"),
        ("SHE", "SHE"),
        ("생산", "생산"),
        ("품질", "품질"),
        ("구매", "구매"),
        ("ERP", "ERP"),
        ("M365", "M365"),
        ("G/W", "G/W"),
    ],
    "service_status": [("운영중", "운영중"), ("대기", "대기"), ("종료", "종료")],
    "build_type": [("SI개발", "SI개발"), ("솔루션", "솔루션"), ("기타", "기타")],
    "service_grade": [("S", "S"), ("A", "A"), ("B", "B"), ("C", "C")],
    "service_ito": [
        ("통합ITO", "통합ITO"),
        ("Non ITO", "Non ITO"),
    ],
    "data_type": [("STRING", "문자열"), ("NUMBER", "숫자"), ("DATE", "날짜"), ("BOOL", "불리언")],
    "required_flag": [("Y", "필수"), ("N", "선택")],
    "searchable_flag": [("Y", "검색가능"), ("N", "검색불가")],
    "attribute_target": [("SERVICE", "서비스"), ("CONFIG", "구성정보")],
    "person_role": [
        ("DT_TEAM", "DT팀"),
        ("ADMIN", "관리자"),
        ("OPERATOR", "운영자"),
        ("INFRA_OPERATOR", "Infra 담당자"),
    ],
    "person_status": [("투입", "투입"), ("종료", "종료"), ("대기", "대기")],
    "resident_type": [("상주", "상주"), ("비상주", "비상주")],
    "gender": [("남", "남"), ("여", "여")],
    "affiliation": [
        ("DT팀", "DT팀"),
        ("ITO(SKCC)", "ITO(SKCC)"),
        ("ICT(일반)", "ICT(일반)"),
        ("ICT(비상주)", "ICT(비상주)"),
        ("ICT(DX)", "ICT(DX)"),
        ("ICT(프로젝트)", "ICT(프로젝트)"),
        ("ICT(ERP)", "ICT(ERP)"),
        ("ICT(ITSecPrj)", "ICT(ITSecPrj)"),
        ("ICT(M365)", "ICT(M365)"),
        ("기타", "기타"),
    ],
    "mapping_status": [("ACTIVE", "활성"), ("INACTIVE", "비활성"), ("END", "종료")],
    "config_type": [("WEB", "WEB"), ("WAS", "WAS"), ("DB", "DB"), ("기타", "기타")],
    "operation_type": [("운영", "운영"), ("개발", "개발"), ("스테이징", "스테이징"), ("백업", "백업")],
    "infra_type": [("AWS", "AWS"), ("OnPrem", "OnPrem"), ("기타", "기타")],
    "infra_location": [("AWS", "AWS"), ("판교", "판교"), ("청주", "청주"), ("울산", "울산")],
    "network_zone": [("DMZ", "DMZ"), ("내부망", "내부망"), ("외부망", "외부망")],
    "component_type": [
        ("language", "language"),
        ("runtime", "runtime"),
        ("framework", "framework"),
        ("library", "library"),
        ("middleware", "middleware"),
        ("OS", "OS"),
        ("DB", "DB"),
        ("기타", "기타"),
    ],
    "support_status": [("SUPPORTED", "지원"), ("LIMITED", "부분지원"), ("END", "지원종료")],
    "use_flag": [("Y", "사용"), ("N", "미사용")],
}


class Command(BaseCommand):
    help = "전면 재정리 테이블용 공통 코드 시드"

    def handle(self, *args, **kwargs):
        for gi, (group_key, rows) in enumerate(SEED_GROUPS.items(), start=1):
            group, _ = CodeGroup.objects.update_or_create(
                key=group_key,
                defaults={"name": group_key, "sort_order": gi * 10, "is_active": True},
            )
            valid_codes = {code for code, name in rows}
            for ci, (code, name) in enumerate(rows, start=1):
                Code.objects.update_or_create(
                    group=group,
                    code=code,
                    defaults={"name": name, "sort_order": ci * 10, "is_active": True, "related_code": None},
                )
            if group_key == "component_type":
                migrate_component_type_foreign_keys()
            elif group_key == "operation_type":
                migrate_operation_type_foreign_keys()
            elif group_key == "config_type":
                migrate_config_type_foreign_keys()
            elif group_key == "infra_type":
                migrate_infra_type_foreign_keys()
            elif group_key == "infra_location":
                migrate_infra_location_foreign_keys()
            elif group_key == "network_zone":
                migrate_network_zone_foreign_keys()
            Code.objects.filter(group=group).exclude(code__in=valid_codes).update(is_active=False)
        ensure_service_duty_attribute_code()
        ensure_service_person_attribute_codes()
        self.stdout.write(self.style.SUCCESS("재정리 공통 코드 시드 완료"))
