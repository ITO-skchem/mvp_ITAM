from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_code_related_code"),
        ("masters", "0024_personmaster_resident_type_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="personmaster",
            name="affiliation_code",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="person_affiliations",
                to="core.code",
                verbose_name="소속",
            ),
        ),
        migrations.AddField(
            model_name="personmaster",
            name="gender_code",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="person_genders",
                to="core.code",
                verbose_name="성별",
            ),
        ),
    ]
