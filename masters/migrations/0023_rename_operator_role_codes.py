# 마이그레이션: person_role 코드 APPL_OPS/INFRA_OPS → OPERATOR/INFRA_OPERATOR,
# 서비스 담당자 AttributeCode PK SVC_ATTR_PERSON_*_OPS → SVC_ATTR_PERSON_*_OPERATOR


from django.db import migrations


def rename_person_roles(apps, schema_editor):
    Code = apps.get_model("core", "Code")
    CodeGroup = apps.get_model("core", "CodeGroup")
    PersonMaster = apps.get_model("masters", "PersonMaster")
    ServicePersonMapping = apps.get_model("masters", "ServicePersonMapping")

    grp = CodeGroup.objects.filter(key="person_role").first()
    if not grp:
        return
    rename_map = {"APPL_OPS": "OPERATOR", "INFRA_OPS": "INFRA_OPERATOR"}
    for old_code, new_code in rename_map.items():
        legacy = Code.objects.filter(group_id=grp.id, code=old_code).first()
        target = Code.objects.filter(group_id=grp.id, code=new_code).first()
        if not legacy:
            continue
        if target:
            if legacy.pk != target.pk:
                PersonMaster.objects.filter(role_code_id=legacy.pk).update(role_code_id=target.pk)
                ServicePersonMapping.objects.filter(role_code_id=legacy.pk).update(role_code_id=target.pk)
            legacy.delete()
            continue
        legacy.code = new_code
        legacy.save(update_fields=["code"])


def remap_service_person_attribute_codes(apps, schema_editor):
    AttributeCode = apps.get_model("masters", "AttributeCode")
    ServiceAttribute = apps.get_model("masters", "ServiceAttribute")
    ConfigurationAttribute = apps.get_model("masters", "ConfigurationAttribute")

    pairs = [
        ("SVC_ATTR_PERSON_APPL_OPS", "SVC_ATTR_PERSON_OPERATOR"),
        ("SVC_ATTR_PERSON_INFRA_OPS", "SVC_ATTR_PERSON_INFRA_OPERATOR"),
    ]
    for old_pk, new_pk in pairs:
        old = AttributeCode.objects.filter(pk=old_pk).first()
        has_new = AttributeCode.objects.filter(pk=new_pk).exists()
        if not old and has_new:
            continue
        if not old:
            continue
        if has_new:
            ServiceAttribute.objects.filter(attribute_code_id=old_pk).update(attribute_code_id=new_pk)
            ConfigurationAttribute.objects.filter(attribute_code_id=old_pk).update(attribute_code_id=new_pk)
            old.delete()
            continue
        attrs = dict(
            name=old.name,
            code_group_id=old.code_group_id,
            data_type_code_id=old.data_type_code_id,
            required_code_id=old.required_code_id,
            searchable_code_id=old.searchable_code_id,
            target_code_id=old.target_code_id,
        )
        AttributeCode.objects.create(attribute_code=new_pk, **attrs)
        ServiceAttribute.objects.filter(attribute_code_id=old_pk).update(attribute_code_id=new_pk)
        ConfigurationAttribute.objects.filter(attribute_code_id=old_pk).update(attribute_code_id=new_pk)
        old.delete()


def forwards(apps, schema_editor):
    rename_person_roles(apps, schema_editor)
    remap_service_person_attribute_codes(apps, schema_editor)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0022_rename_configuration_component_labels"),
    ]

    operations = [
        migrations.RunPython(forwards, noop_reverse),
    ]
