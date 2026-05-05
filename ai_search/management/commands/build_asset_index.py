import pickle
from pathlib import Path

import faiss
from django.core.management.base import BaseCommand

from ai_search.indexer import AssetIndexer
from assets.models import InfraAsset
from masters.models import Component, PersonMaster, ServiceMaster


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
                f"[서비스] {service.name} 구분:{service.system_type} 운영:{service.operation_type} "
                f"등급:{service.service_grade} 수준:{service.service_level} "
                f"ITGC:{service.itgc} 설명:{service.description}"
            )
            items.append((text, {"type": "service", "id": service.pk, "name": service.name}))

        for comp in Component.objects.all():
            text = (
                f"[자산] {comp.hostname} 시스템명:{comp.system_name} 구분:{comp.server_type} "
                f"운영개발:{comp.operation_dev} IP:{comp.ip or ''} MW:{comp.mw} RT:{comp.runtime or ''} OS/DBMS:{comp.os_dbms}"
            )
            items.append((text, {"type": "component", "id": comp.pk, "name": comp.hostname or comp.asset_mgmt_no}))

        for person in PersonMaster.objects.all():
            text = (
                f"[담당자] {person.name} 역할:{person.role} 회사:{person.company} "
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
