from django.core.management.base import BaseCommand

from core.models import Code, CodeGroup
from masters.service_person_grid import ensure_service_person_attribute_codes


SEED_GROUPS = {
    "yn_flag": [("Y", "예"), ("N", "아니오")],
    "service_category": [("ERP", "ERP"), ("MES", "MES"), ("PORTAL", "PORTAL"), ("GROUPWARE", "GROUPWARE")],
    "service_status": [("ACTIVE", "운영중"), ("PAUSED", "중지"), ("END", "종료")],
    "build_type": [("NEW", "신규"), ("RENEWAL", "고도화"), ("MAINT", "유지보수")],
    "service_grade": [("S", "S"), ("A", "A"), ("B", "B"), ("C", "C")],
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
    "person_status": [("ACTIVE", "재직"), ("LEAVE", "휴직"), ("END", "종료")],
    "mapping_status": [("ACTIVE", "활성"), ("INACTIVE", "비활성"), ("END", "종료")],
    "config_type": [("WEB", "WEB"), ("WAS", "WAS"), ("DB", "DB"), ("CACHE", "CACHE"), ("ETC", "기타")],
    "operation_type": [("OPS", "운영"), ("DEV", "개발"), ("BOTH", "운영/개발")],
    "infra_type": [("ONPREM", "온프레미스"), ("AWS", "AWS"), ("AZURE", "AZURE"), ("GCP", "GCP")],
    "infra_location": [("DC1", "센터1"), ("DC2", "센터2"), ("AWS", "AWS")],
    "network_zone": [("DMZ", "DMZ"), ("INTERNAL", "내부"), ("EXTERNAL", "외부")],
    "component_type": [("OS", "OS"), ("MIDDLEWARE", "미들웨어"), ("DB", "DB"), ("APP", "애플리케이션")],
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
            Code.objects.filter(group=group).exclude(code__in=valid_codes).update(is_active=False)
        ensure_service_person_attribute_codes()
        self.stdout.write(self.style.SUCCESS("재정리 공통 코드 시드 완료"))
