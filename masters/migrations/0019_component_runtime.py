from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0018_remove_componentmaster_extra_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="component",
            name="runtime",
            field=models.CharField(blank=True, max_length=100, verbose_name="Runtime"),
        ),
    ]
