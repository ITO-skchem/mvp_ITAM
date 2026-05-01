import threading

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from masters.models import Component, PersonMaster, ServiceMaster

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


def sync_service_owner_fields_from_persons(system_names: set[str]) -> None:
    """담당자 마스터 기준으로 ServiceMaster 담당자 컬럼을 맞춤. update()만 사용해 재귀 시그널 없음."""
    from assets.infra_sync import build_appl_owner_names, build_person_names_for_role

    role_customer = "고객사 담당자"
    role_appl = "Appl. 담당자"
    role_server = "서버 담당자"
    role_db = "DB 담당자"

    for target in system_names:
        t = (target or "").strip()
        if not t:
            continue
        ServiceMaster.objects.filter(name=t).update(
            customer_owner=build_person_names_for_role(t, role_customer),
            partner_operator=build_person_names_for_role(t, role_appl),
            server_owner=build_person_names_for_role(t, role_server),
            db_owner=build_person_names_for_role(t, role_db),
            appl_owner=build_appl_owner_names(t),
        )
    # QuerySet.update는 ServiceMaster post_save를 타지 않으므로 InfraAsset 재계산 예약
    schedule_rebuild_infra_assets()


@receiver(pre_save, sender=PersonMaster)
def person_presave_track_system_name(sender, instance, **kwargs):
    if not instance.pk:
        instance._prev_system_name_for_appl_sync = None
        return
    try:
        prev = PersonMaster.objects.only("system_name").get(pk=instance.pk)
        instance._prev_system_name_for_appl_sync = (prev.system_name or "").strip()
    except PersonMaster.DoesNotExist:
        instance._prev_system_name_for_appl_sync = None


@receiver(post_save, sender=PersonMaster)
def sync_service_appl_owner_after_person_save(sender, instance, **kwargs):
    targets = {(instance.system_name or "").strip()}
    prev = getattr(instance, "_prev_system_name_for_appl_sync", None)
    if prev:
        targets.add(prev)
    sync_service_owner_fields_from_persons(targets)


@receiver(post_delete, sender=PersonMaster)
def sync_service_appl_owner_after_person_delete(sender, instance, **kwargs):
    sync_service_owner_fields_from_persons({(instance.system_name or "").strip()})


@receiver(post_save, sender=ServiceMaster)
def sync_service_master_owners_from_persons(sender, instance, **kwargs):
    """서비스명 저장 시 담당자 마스터와 동기화(역할별·Appl. 운영자). QuerySet.update는 시그널 미발생."""
    sync_service_owner_fields_from_persons({(instance.name or "").strip()})


@receiver(post_save, sender=ServiceMaster)
@receiver(post_delete, sender=ServiceMaster)
@receiver(post_save, sender=PersonMaster)
@receiver(post_delete, sender=PersonMaster)
@receiver(post_save, sender=Component)
@receiver(post_delete, sender=Component)
def refresh_infra_assets_on_master_change(sender, **kwargs):
    schedule_rebuild_infra_assets()
