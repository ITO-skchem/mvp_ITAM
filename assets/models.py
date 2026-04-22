from django.db import models
from django.db import transaction

from masters.models import Component, PersonMaster, ServiceMaster


class InfraAsset(models.Model):
    no = models.AutoField(primary_key=True)
    asset_key = models.CharField("자산KEY", max_length=20, unique=True, blank=True, editable=False)
    system_name = models.CharField("시스템명", max_length=200)
    customer_owner_name = models.CharField("고객사 담당자", max_length=100, blank=True)
    appl_owner_name = models.CharField("Appl. 담당자", max_length=100, blank=True)
    partner_operator_name = models.CharField("협력사 운영자", max_length=100, blank=True)
    service = models.ForeignKey(
        ServiceMaster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="서비스",
    )
    use_flag = models.CharField("사용여부", max_length=1, default="Y")
    devops_type = models.CharField("개발/운영", max_length=5, blank=True)
    infra_type = models.CharField("인프라 구분", max_length=10, blank=True)
    network_zone = models.CharField("네트웍 구분", max_length=5, blank=True)
    platform_type = models.CharField("플랫폼 구분", max_length=10, blank=True)

    web = models.CharField("WEB", max_length=100, blank=True)
    was = models.CharField("WAS", max_length=100, blank=True)
    hostname = models.CharField("Hostname", max_length=200, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    port = models.CharField("Port", max_length=20, blank=True)
    os = models.CharField("OS", max_length=100, blank=True)
    url = models.URLField("URL", blank=True)
    location = models.CharField("위치", max_length=100, blank=True)
    ssl_domain = models.CharField("SSL 도메인", max_length=200, blank=True)
    cert_format = models.CharField("인증서 포맷", max_length=50, blank=True)

    db_hostname = models.CharField("DB Hostname", max_length=200, blank=True)
    db_ip = models.GenericIPAddressField("DB IP", null=True, blank=True)
    db_port = models.CharField("DB Port", max_length=20, blank=True)
    db_name = models.CharField("DB명", max_length=100, blank=True)
    dbms = models.CharField("DBMS", max_length=100, blank=True)
    db_size_gb = models.DecimalField("DB Size(GB)", max_digits=12, decimal_places=2, null=True, blank=True)
    db_encrypted = models.BooleanField("DB암호화", default=False)

    dt_team_owner = models.ForeignKey(
        PersonMaster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assets_dt",
        verbose_name="DT팀 담당",
    )
    ito_owner = models.ForeignKey(
        PersonMaster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assets_ito",
        verbose_name="통합ITO 담당",
    )
    partner_owner = models.ForeignKey(
        PersonMaster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assets_partner",
        verbose_name="협력 담당",
    )
    extra_persons = models.ManyToManyField(
        PersonMaster,
        blank=True,
        related_name="assets_extra",
        verbose_name="추가 담당자",
    )
    components = models.ManyToManyField(Component, blank=True, verbose_name="컴포넌트")

    remark1 = models.TextField("비고1", blank=True)
    remark2 = models.TextField("비고2", blank=True)
    extra = models.JSONField("추가필드", default=dict, blank=True)

    class Meta:
        ordering = ["no"]

    @classmethod
    def next_asset_key(cls):
        prefix = "KEY"
        with transaction.atomic():
            last = (
                cls.objects.filter(asset_key__startswith=prefix)
                .order_by("-asset_key")
                .values_list("asset_key", flat=True)
                .first()
            )
            next_no = int(last[3:]) + 1 if last else 1
            return f"{prefix}{next_no:04d}"

    def save(self, *args, **kwargs):
        if not self.asset_key:
            self.asset_key = self.next_asset_key()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.no} - {self.system_name}"
