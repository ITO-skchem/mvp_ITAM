# Generated manually for schema cleanup

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0017_personmaster_employee_no_notes"),
    ]

    operations = [
        migrations.RemoveField(model_name="componentmaster", name="cert_format"),
        migrations.RemoveField(model_name="componentmaster", name="ssl_domain"),
        migrations.RemoveField(model_name="componentmaster", name="os_dbms"),
        migrations.RemoveField(model_name="componentmaster", name="mw"),
        migrations.RemoveField(model_name="componentmaster", name="port"),
        migrations.RemoveField(model_name="componentmaster", name="ip"),
        migrations.RemoveField(model_name="componentmaster", name="network_zone"),
        migrations.RemoveField(model_name="componentmaster", name="location"),
        migrations.RemoveField(model_name="componentmaster", name="platform_type"),
        migrations.RemoveField(model_name="componentmaster", name="operation_dev"),
    ]
