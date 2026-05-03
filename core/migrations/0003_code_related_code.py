import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_codegroup_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="code",
            name="related_code",
            field=models.ForeignKey(
                blank=True,
                help_text="다른 코드(예: 상위 분류)를 참조할 때 사용",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="typed_component_codes",
                to="core.code",
                verbose_name="분류 코드",
            ),
        ),
    ]
