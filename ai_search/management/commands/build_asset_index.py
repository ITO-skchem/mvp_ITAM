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
                f"[인프라] {asset.system_name} IP:{asset.ip or ''} "
                f"DB:{asset.dbms or ''}/{asset.db_name or ''} "
                f"인프라:{asset.infra_type} 네트워크:{asset.network_zone} 플랫폼:{asset.platform_type} "
                f"HOST:{asset.hostname} URL:{asset.url} 위치:{asset.location} "
                f"메모:{asset.remark1} {asset.remark2}"
            )
            items.append((text, {"type": "infra", "id": asset.pk, "name": asset.system_name}))

        for service in ServiceMaster.objects.all():
            text = (
                f"[서비스] {service.name} 구분:{service.system_type} 운영:{service.operation_type} "
                f"등급:{service.service_grade} 수준:{service.service_level} "
                f"ITGC:{service.itgc} 설명:{service.description}"
            )
            items.append((text, {"type": "service", "id": service.pk, "name": service.name}))

        for comp in Component.objects.all():
            text = f"[컴포넌트] {comp.name} {comp.version} 유형:{comp.comp_type} 용도:{comp.usage} EOS:{comp.eos}"
            items.append((text, {"type": "component", "id": comp.pk, "name": comp.name}))

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
