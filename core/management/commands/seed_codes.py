from django.core.management.base import BaseCommand

from core.models import Code, CodeGroup


class Command(BaseCommand):
    help = "Seed default CodeGroup/Code values"

    def handle(self, *args, **kwargs):
        seed_data = {
            "use_flag": {
                "name": "사용여부",
                "codes": [("Y", "사용"), ("N", "미사용")],
            },
            "devops_type": {
                "name": "개발/운영",
                "codes": [("DEV", "개발"), ("OPS", "운영"), ("BOTH", "개발/운영")],
            },
            "infra_type": {
                "name": "인프라 구분",
                "codes": [("ONPREM", "On-Prem"), ("AWS", "AWS"), ("OTHER", "기타")],
            },
            "network_zone": {
                "name": "네트워크 구분",
                "codes": [("DMZ", "DMZ"), ("SF", "Server Farm"), ("ETC", "기타")],
            },
            "platform_type": {
                "name": "플랫폼 구분",
                "codes": [("WEB", "WEB"), ("CS", "CS"), ("MOBILE", "MOBILE"), ("ETC", "기타")],
            },
            "person_role": {
                "name": "담당자 역할",
                "codes": [
                    ("customer_it", "고객사 IT 담당"),
                    ("sk_owner", "Infa 담당자(SK)"),
                    ("partner", "협력사 담당"),
                    ("developer", "개발담당"),
                    ("operator", "운영담당"),
                ],
            },
        }

        for index, (group_key, group_data) in enumerate(seed_data.items(), start=1):
            group, _ = CodeGroup.objects.update_or_create(
                key=group_key,
                defaults={
                    "name": group_data["name"],
                    "sort_order": index * 10,
                    "is_active": True,
                },
            )

            for code_index, (code, name) in enumerate(group_data["codes"], start=1):
                Code.objects.update_or_create(
                    group=group,
                    code=code,
                    defaults={"name": name, "sort_order": code_index * 10, "is_active": True},
                )

        self.stdout.write(self.style.SUCCESS("Code groups and codes created/updated"))
