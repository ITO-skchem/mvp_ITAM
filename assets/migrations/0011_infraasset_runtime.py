from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0010_infraasset_server_db_owner_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="infraasset",
            name="runtime",
            field=models.CharField(blank=True, max_length=100, verbose_name="Runtime"),
        ),
    ]
