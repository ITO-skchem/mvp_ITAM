import pandas as pd
from django.core.management.base import BaseCommand

from masters.models import Component, PersonMaster, ServiceMaster


class Command(BaseCommand):
    help = "Import masters and assets from Excel"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)

    def handle(self, *args, **opts):
        path = opts["path"]
        xls = pd.ExcelFile(path)

        if "서비스 마스터" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="서비스 마스터")
            for _, row in df.iterrows():
                name = str(row.get("시스템명", "")).strip()
                if not name:
                    continue
                ServiceMaster.objects.update_or_create(
                    name=name,
                    defaults={
                        "description": str(row.get("설명", "")),
                        "created_by": "import_excel",
                        "updated_by": "import_excel",
                    },
                )

        if "담당자 관리" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="담당자 관리")
            for _, row in df.iterrows():
                name = row.get("C&C담당자") or row.get("고객사담당자") or row.get("협력") or ""
                name = str(name).strip()
                if not name:
                    continue
                employee_no = str(row.get("사번", "")).strip() or None
                if not employee_no:
                    continue
                PersonMaster.objects.update_or_create(
                    employee_no=employee_no,
                    defaults={
                        "name": name,
                        "company": str(row.get("업체명", "")),
                        "phone": str(row.get("연락처", "")),
                        "email": str(row.get("메일주소", "")) or "",
                        "external_email": str(row.get("외부메일주소", "")) or "",
                        "deployed_at": pd.to_datetime(row.get("투입일자", None), errors="coerce"),
                    },
                )

        if "컴포넌트 관리" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="컴포넌트 관리")
            for _, row in df.iterrows():
                name = str(row.get("컴포넌트/컨트롤 명", "")).strip()
                if not name:
                    continue
                version = str(row.get("버전", "")).strip()
                Component.objects.update_or_create(
                    product_name=name,
                    version=version,
                    defaults={
                        "vendor_name": str(row.get("벤더명", "")),
                        "cpe_name": str(row.get("CPE", "")),
                        "created_by": "import_excel",
                        "updated_by": "import_excel",
                    },
                )

        # 시스템 통합정보(InfraAsset)는 마스터 저장 시 자동 재계산되므로 엑셀에서 직접 적재하지 않습니다.

        self.stdout.write(self.style.SUCCESS("Excel import completed"))
