import pandas as pd
from django.core.management.base import BaseCommand

from assets.models import InfraAsset
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

        if "인프라 자산관리" in xls.sheet_names:
            df = pd.read_excel(path, sheet_name="인프라 자산관리")
            for _, row in df.iterrows():
                system_name = str(row.get("시스템명", "")).strip()
                if not system_name:
                    continue
                InfraAsset.objects.create(
                    system_name=system_name,
                    use_flag="Y" if str(row.get("사용여부", "Y")).upper() in ["Y", "YES", "1", "TRUE"] else "N",
                    infra_type="AWS" if "AWS" in str(row.get("인프라 구분", "")).upper() else "ONPREM",
                    network_zone="DMZ" if "DMZ" in str(row.get("네트웍 구분", "")).upper() else "SF",
                    platform_type="WEB",
                    web=str(row.get("WEB", "")),
                    was=str(row.get("WAS", "")),
                    hostname=str(row.get("Hostname", "")),
                    ip=str(row.get("IP", "")) or None,
                    port=str(row.get("Port", "")),
                    os=str(row.get("OS", "")),
                    url=str(row.get("URL", "")),
                    location=str(row.get("위치", "")),
                    ssl_domain=str(row.get("SSL 도메인", "")),
                    cert_format=str(row.get("인증서 포맷", "")),
                    db_hostname=str(row.get("DB Hostname", "")),
                    db_ip=str(row.get("DB IP", "")) or None,
                    db_port=str(row.get("DB Port", "")),
                    db_name=str(row.get("DB명", "")),
                    dbms=str(row.get("DBMS", "")),
                    remark1=str(row.get("비고1", "")),
                    remark2=str(row.get("비고2", "")),
                )

        self.stdout.write(self.style.SUCCESS("Excel import completed"))
