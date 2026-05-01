from django.db import models


class InfraAsset(models.Model):
    """시스템 통합정보: 서비스·자산 마스터 조인 + 담당자 반영(동기화는 infra_sync / 시그널)."""

    system_mgmt_no = models.CharField(
        "시스템 관리번호",
        max_length=16,
        primary_key=True,
        editable=False,
    )
    service_mgmt_no = models.CharField("서비스관리번호", max_length=20, db_index=True)
    asset_mgmt_no = models.CharField("자산관리번호", max_length=20, db_index=True)
    service_name = models.CharField("서비스명", max_length=200)

    customer_owner_name = models.CharField("고객사 담당자", max_length=100, blank=True)
    appl_owner_name = models.CharField("Appl. 담당자", max_length=100, blank=True)
    partner_operator_name = models.CharField("Appl. 운영자", max_length=100, blank=True)
    server_owner_name = models.CharField("서버 담당자", max_length=100, blank=True)
    db_owner_name = models.CharField("DB 담당자", max_length=100, blank=True)

    hostname = models.CharField("Hostname", max_length=200, blank=True)
    server_type = models.CharField("서버 구분", max_length=100, blank=True)
    operation_dev = models.CharField("운영/개발", max_length=50, blank=True)
    network_zone = models.CharField("네트웍 구분", max_length=100, blank=True)
    platform_type = models.CharField("플랫폼 구분", max_length=100, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    port = models.CharField("Port", max_length=20, blank=True)
    location = models.CharField("위치", max_length=100, blank=True)
    mw = models.CharField("MW", max_length=100, blank=True)
    os_dbms = models.CharField("OS/DBMS", max_length=200, blank=True)
    url_or_db_name = models.CharField("URL/DB명", max_length=300, blank=True)
    ssl_domain = models.CharField("SSL 도메인", max_length=200, blank=True)
    cert_format = models.CharField("인증서 포맷", max_length=100, blank=True)
    remark1 = models.TextField("비고1", blank=True)
    remark2 = models.TextField("비고2", blank=True)
    extra = models.JSONField("추가필드", default=dict, blank=True)

    component = models.ForeignKey(
        "masters.Component",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="infra_assets",
        verbose_name="자산 마스터",
    )

    class Meta:
        ordering = ["service_mgmt_no", "asset_mgmt_no"]
        verbose_name = "시스템 통합정보"
        verbose_name_plural = "시스템 통합정보"

    def __str__(self):
        return f"{self.system_mgmt_no} - {self.service_name}"
