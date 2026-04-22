# Generated manually for 시스템 통합정보(InfraAsset) 스키마 교체

import django.db.models.deletion
from django.db import migrations, models


def populate_infra(apps, schema_editor):
    from assets.infra_sync import rebuild_infra_assets_from_masters

    rebuild_infra_assets_from_masters()


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0008_alter_infraasset_partner_operator_name"),
        ("masters", "0012_alter_servicemaster_partner_operator"),
    ]

    operations = [
        migrations.DeleteModel(name="InfraAsset"),
        migrations.CreateModel(
            name="InfraAsset",
            fields=[
                (
                    "system_mgmt_no",
                    models.CharField(
                        editable=False,
                        max_length=16,
                        primary_key=True,
                        serialize=False,
                        verbose_name="시스템 관리번호",
                    ),
                ),
                (
                    "service_mgmt_no",
                    models.CharField(db_index=True, max_length=20, verbose_name="서비스관리번호"),
                ),
                (
                    "asset_mgmt_no",
                    models.CharField(db_index=True, max_length=20, verbose_name="자산관리번호"),
                ),
                ("service_name", models.CharField(max_length=200, verbose_name="서비스명")),
                (
                    "customer_owner_name",
                    models.CharField(blank=True, max_length=100, verbose_name="고객사 담당자"),
                ),
                (
                    "appl_owner_name",
                    models.CharField(blank=True, max_length=100, verbose_name="Appl. 담당자"),
                ),
                (
                    "partner_operator_name",
                    models.CharField(blank=True, max_length=100, verbose_name="Appl. 운영자"),
                ),
                ("hostname", models.CharField(blank=True, max_length=200, verbose_name="Hostname")),
                ("server_type", models.CharField(blank=True, max_length=100, verbose_name="서버 구분")),
                ("operation_dev", models.CharField(blank=True, max_length=50, verbose_name="운영/개발")),
                ("network_zone", models.CharField(blank=True, max_length=100, verbose_name="네트웍 구분")),
                ("platform_type", models.CharField(blank=True, max_length=100, verbose_name="플랫폼 구분")),
                ("ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("port", models.CharField(blank=True, max_length=20, verbose_name="Port")),
                ("location", models.CharField(blank=True, max_length=100, verbose_name="위치")),
                ("mw", models.CharField(blank=True, max_length=100, verbose_name="MW")),
                ("os_dbms", models.CharField(blank=True, max_length=200, verbose_name="OS/DBMS")),
                ("url_or_db_name", models.CharField(blank=True, max_length=300, verbose_name="URL/DB명")),
                ("ssl_domain", models.CharField(blank=True, max_length=200, verbose_name="SSL 도메인")),
                ("cert_format", models.CharField(blank=True, max_length=100, verbose_name="인증서 포맷")),
                ("remark1", models.TextField(blank=True, verbose_name="비고1")),
                ("remark2", models.TextField(blank=True, verbose_name="비고2")),
                ("extra", models.JSONField(blank=True, default=dict, verbose_name="추가필드")),
                (
                    "component",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="infra_assets",
                        to="masters.component",
                        verbose_name="자산 마스터",
                    ),
                ),
            ],
            options={
                "verbose_name": "시스템 통합정보",
                "verbose_name_plural": "시스템 통합정보",
                "ordering": ["service_mgmt_no", "asset_mgmt_no"],
            },
        ),
        migrations.RunPython(populate_infra, migrations.RunPython.noop),
    ]
