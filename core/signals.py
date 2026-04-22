from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.models import AuditLog

TRACKED_MODELS = {"ServiceMaster", "PersonMaster", "Component", "InfraAsset", "CodeGroup", "Code"}


def get_model_changes(instance):
    changes = {}
    if not instance.pk:
        return changes
    try:
        old = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return changes
    for field in instance._meta.fields:
        name = field.name
        old_val = getattr(old, name)
        new_val = getattr(instance, name)
        if old_val != new_val:
            changes[name] = {"old": str(old_val), "new": str(new_val)}
    return changes


@receiver(pre_save)
def before_save(sender, instance, **kwargs):
    if sender.__name__ in TRACKED_MODELS and instance.pk:
        instance._changes = get_model_changes(instance)


@receiver(post_save)
def after_save(sender, instance, created, **kwargs):
    if sender.__name__ in TRACKED_MODELS:
        AuditLog.objects.create(
            app_label=sender._meta.app_label,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            action="CREATE" if created else "UPDATE",
            changes={} if created else getattr(instance, "_changes", {}),
            user=None,
        )


@receiver(post_delete)
def after_delete(sender, instance, **kwargs):
    if sender.__name__ in TRACKED_MODELS:
        AuditLog.objects.create(
            app_label=sender._meta.app_label,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            action="DELETE",
            changes={},
            user=None,
        )
