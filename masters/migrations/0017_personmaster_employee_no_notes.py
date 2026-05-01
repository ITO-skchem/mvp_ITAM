from django.db import migrations, models


def clear_notes_and_renumber_employee_no(apps, schema_editor):
    PersonMaster = apps.get_model("masters", "PersonMaster")
    PersonMaster.objects.update(notes="")
    for i, row in enumerate(PersonMaster.objects.order_by("person_mgmt_no"), start=1):
        PersonMaster.objects.filter(pk=row.pk).update(employee_no=f"I{i:05d}")


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0016_component_db_component_middleware_component_os"),
    ]

    operations = [
        migrations.RunPython(clear_notes_and_renumber_employee_no, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="personmaster",
            name="employee_no",
            field=models.CharField(blank=True, max_length=50, unique=True, verbose_name="사번"),
        ),
    ]
