# 서비스 대상 속성 "운영부서" → 표준 코드 SVC_ATTR_CURRENT_DUTY / 표시명 "담당현업"

from django.db import migrations

DUTY_PK = "SVC_ATTR_CURRENT_DUTY"
DUTY_LABEL = "담당현업"


def forwards(apps, schema_editor):
    AttributeCode = apps.get_model("masters", "AttributeCode")
    ServiceAttribute = apps.get_model("masters", "ServiceAttribute")
    Code = apps.get_model("core", "Code")
    CodeGroup = apps.get_model("core", "CodeGroup")

    def pick_code(group_key: str, code: str):
        g = CodeGroup.objects.filter(key=group_key).first()
        if not g:
            return None
        return Code.objects.filter(group_id=g.id, code=code, is_active=True).first()

    data_type = pick_code("data_type", "STRING")
    required = pick_code("required_flag", "N")
    searchable = pick_code("searchable_flag", "Y")
    target = pick_code("attribute_target", "SERVICE")
    if not all([data_type, required, searchable, target]):
        return

    duty_ac, _ = AttributeCode.objects.update_or_create(
        attribute_code=DUTY_PK,
        defaults={
            "name": DUTY_LABEL,
            "data_type_code": data_type,
            "required_code": required,
            "searchable_code": searchable,
            "target_code": target,
        },
    )

    tgt_id = target.id
    old_qs = AttributeCode.objects.filter(name="운영부서", target_code_id=tgt_id).exclude(
        attribute_code=DUTY_PK
    )
    for old in old_qs.iterator():
        for sa in ServiceAttribute.objects.filter(attribute_code_id=old.attribute_code):
            existing = ServiceAttribute.objects.filter(
                service_id=sa.service_id, attribute_code_id=DUTY_PK
            ).first()
            v = (sa.value or "").strip()
            if existing:
                ev = (existing.value or "").strip()
                if v and not ev:
                    existing.value = sa.value
                    existing.save(update_fields=["value"])
            else:
                ServiceAttribute.objects.create(
                    service_id=sa.service_id,
                    attribute_code=duty_ac,
                    value=sa.value or "",
                )
            sa.delete()
        old.delete()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0028_servicemaster_ito_code"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
