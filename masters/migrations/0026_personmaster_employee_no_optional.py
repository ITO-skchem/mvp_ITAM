from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0025_personmaster_affiliation_gender"),
    ]

    operations = [
        migrations.AlterField(
            model_name="personmaster",
            name="employee_no",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name="사번"),
        ),
    ]
