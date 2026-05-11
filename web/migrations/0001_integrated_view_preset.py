from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegratedViewPreset",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("slot", models.PositiveSmallIntegerField()),
                ("name", models.CharField(blank=True, default="", max_length=100)),
                ("selected_fields", models.JSONField(blank=True, default=list)),
                ("conditions", models.JSONField(blank=True, default=list)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integrated_view_presets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user_id", "slot"],
                "unique_together": {("user", "slot")},
            },
        ),
        migrations.AddIndex(
            model_name="integratedviewpreset",
            index=models.Index(fields=["user", "slot"], name="web_integra_user_id_8c3a6d_idx"),
        ),
    ]

