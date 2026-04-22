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
                        "category": str(row.get("구분", "")),
                        "system_type": str(row.get("시스템 구분", "")),
                        "description": str(row.get("설명", "")),
                        "operation_type": str(row.get("운영구분", "")),
                        "service_grade": str(row.get("서비스 등급", "")),
                        "service_level": str(row.get("서비스 수준", "")),
                    },
                )

        if "담당자 관리" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="담당자 관리")
            for _, row in df.iterrows():
                name = row.get("C&C담당자") or row.get("고객사담당자") or row.get("협력") or ""
                name = str(name).strip()
                if not name:
                    continue
                PersonMaster.objects.update_or_create(
                    name=name,
                    defaults={
                        "system_name": str(row.get("시스템명", "")),
                        "company": str(row.get("업체명", "")),
                        "phone": str(row.get("연락처", "")),
                        "email": str(row.get("메일주소", "")) or "",
                        "ext_email": str(row.get("외부메일주소", "")) or "",
                        "resident": str(row.get("상주여부", "")).upper() in ["Y", "YES", "1", "TRUE"],
                        "notes": str(row.get("비고(특이사항)", "")),
                    },
                )

        if "컴포넌트 관리" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="컴포넌트 관리")
            for _, row in df.iterrows():
                name = str(row.get("컴포넌트/컨트롤 명", "")).strip()
                if not name:
                    continue
                Component.objects.update_or_create(
                    name=name,
                    version=str(row.get("버전", "")).strip(),
                    defaults={
                        "system_name": str(row.get("시스템명", "")),
                        "comp_type": str(row.get("컴포넌트 유형", "")),
                        "usage": str(row.get("사용 용도", "")),
                        "eos": str(row.get("EOS여부", "")).upper() in ["Y", "YES", "1", "TRUE"],
                        "update_support": str(row.get("업데이트 지원 여부", "")).upper()
                        not in ["N", "NO", "0", "FALSE"],
                        "license": str(row.get("라이선스", "")),
                        "install_method": str(row.get("설치방법", "")),
                    },
                )

        # 시스템 통합정보(InfraAsset)는 마스터 저장 시 자동 재계산되므로 엑셀에서 직접 적재하지 않습니다.

        self.stdout.write(self.style.SUCCESS("Excel import completed"))
