from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_code_related_code"),
        ("masters", "0023_rename_operator_role_codes"),
    ]

    operations = [
        migrations.AddField(
            model_name="personmaster",
            name="resident_type_code",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="person_resident_types",
                to="core.code",
                verbose_name="상주 여부",
            ),
        ),
    ]
