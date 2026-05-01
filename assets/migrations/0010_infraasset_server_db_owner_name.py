from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0009_system_integrated_infraasset"),
    ]

    operations = [
        migrations.AddField(
            model_name="infraasset",
            name="server_owner_name",
            field=models.CharField(blank=True, max_length=100, verbose_name="서버 담당자"),
        ),
        migrations.AddField(
            model_name="infraasset",
            name="db_owner_name",
            field=models.CharField(blank=True, max_length=100, verbose_name="DB 담당자"),
        ),
    ]
