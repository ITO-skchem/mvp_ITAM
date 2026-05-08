import pickle
from pathlib import Path

import faiss
from django.core.management.base import BaseCommand

from ai_search.indexer import AssetIndexer
from assets.models import InfraAsset
from masters.models import Component, ConfigurationMaster, PersonMaster, ServiceMaster


class Command(BaseCommand):
    help = "Build FAISS index for AI 자산검색"

    def handle(self, *args, **kwargs):
        items = []

        for asset in InfraAsset.objects.all():
            text = (
                f"[시스템통합] {asset.system_mgmt_no} {asset.service_name} "
                f"서비스:{asset.service_mgmt_no} 자산:{asset.asset_mgmt_no} "
                f"HOST:{asset.hostname} IP:{asset.ip or ''} MW:{asset.mw} RT:{asset.runtime or ''} OS/DBMS:{asset.os_dbms} "
                f"URL/DB:{asset.url_or_db_name} 위치:{asset.location} "
                f"담당:고객사:{asset.customer_owner_name} Appl:{asset.appl_owner_name} 운영:{asset.partner_operator_name} "
                f"서버담당:{asset.server_owner_name} DB담당:{asset.db_owner_name} "
                f"비고:{asset.remark1} {asset.remark2}"
            )
            items.append((text, {"type": "infra", "id": asset.pk, "name": asset.service_name}))

        for service in ServiceMaster.objects.all():
            text = (
                f"[서비스] {service.name} "
                f"분류:{service.category_code.code if service.category_code else ''} "
                f"상태:{service.status_code.code if service.status_code else ''} "
                f"등급:{service.service_grade_code.code if service.service_grade_code else ''} "
                f"ITGC:{service.itgc_code.code if service.itgc_code else ''} 설명:{service.description}"
            )
            items.append((text, {"type": "service", "id": service.pk, "name": service.name}))

        for cfg in ConfigurationMaster.objects.all():
            text = (
                f"[구성정보] {cfg.hostname} 구성유형:{cfg.server_type_code.code if cfg.server_type_code else ''} "
                f"운영개발:{cfg.operation_dev_code.code if cfg.operation_dev_code else ''} "
                f"IP:{cfg.ip or ''} URL:{cfg.url}"
            )
            items.append((text, {"type": "configuration", "id": cfg.pk, "name": cfg.hostname or cfg.asset_mgmt_no}))

        for comp in Component.objects.all():
            cv = " ".join(p for p in (comp.product_name, comp.version) if (p or "").strip()).strip()
            text = (
                f"[컴포넌트] {cv} "
                f"유형:{comp.component_type_code.code if comp.component_type_code else ''} "
                f"벤더:{comp.vendor_name} CPE:{comp.cpe_name}"
            )
            items.append((text, {"type": "component", "id": comp.pk, "name": cv or comp.product_name}))

        for person in PersonMaster.objects.all():
            text = (
                f"[담당자] {person.name} 역할:{person.role_code.code if person.role_code else ''} 회사:{person.company} "
                f"연락:{person.phone} 이메일:{person.email}"
            )
            items.append((text, {"type": "person", "id": person.pk, "name": person.name}))

        indexer = AssetIndexer()
        indexer.build(items)

        out = Path("var")
        out.mkdir(exist_ok=True)
        with open(out / "asset_index.pkl", "wb") as f:
            pickle.dump(
                {
                    "texts": indexer.texts,
                    "meta": indexer.meta,
                    "raw_index": faiss.serialize_index(indexer.index),
                },
                f,
            )

        self.stdout.write(self.style.SUCCESS("AI Index built"))
