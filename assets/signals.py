import threading

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from masters.models import ConfigurationMaster, PersonMaster, ServiceMaster

_tls = threading.local()


def schedule_rebuild_infra_assets():
    """동일 DB 트랜잭션 내 여러 마스터 변경 시 InfraAsset 재계산을 한 번만 예약."""
    if getattr(_tls, "infra_rebuild_scheduled", False):
        return
    _tls.infra_rebuild_scheduled = True

    def _run():
        _tls.infra_rebuild_scheduled = False
        from assets.infra_sync import rebuild_infra_assets_from_masters

        rebuild_infra_assets_from_masters()

    transaction.on_commit(_run)


@receiver(post_save, sender=ServiceMaster)
@receiver(post_delete, sender=ServiceMaster)
@receiver(post_save, sender=PersonMaster)
@receiver(post_delete, sender=PersonMaster)
@receiver(post_save, sender=ConfigurationMaster)
@receiver(post_delete, sender=ConfigurationMaster)
def refresh_infra_assets_on_master_change(sender, **kwargs):
    schedule_rebuild_infra_assets()
