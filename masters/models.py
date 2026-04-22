from django.db import models
from django.db import transaction


class ServiceMaster(models.Model):
    service_mgmt_no = models.CharField("서비스관리번호", max_length=20, unique=True, blank=True, editable=False)
    category = models.CharField("구분", max_length=100, blank=True)
    name = models.CharField("서비스명", max_length=200)
    system_type = models.CharField("시스템 구분", max_length=100, blank=True)
    description = models.TextField("설명", blank=True)
    operation_type = models.CharField("운영구분", max_length=50, blank=True)
    service_grade = models.CharField("서비스 등급", max_length=50, blank=True)
    service_level = models.CharField("서비스 수준", max_length=50, blank=True)
    customer_owner = models.CharField("고객사 담당자", max_length=100, blank=True)
    appl_owner = models.CharField("Appl. 담당자", max_length=100, blank=True)
    partner_operator = models.CharField("협력사 운영자", max_length=100, blank=True)
    server_owner = models.CharField("서버 담당자", max_length=100, blank=True)
    db_owner = models.CharField("DB 담당자", max_length=100, blank=True)
    owner_company = models.CharField("담당 회사", max_length=100, blank=True)
    owner_dept = models.CharField("담당 부서", max_length=100, blank=True)
    owner_manager = models.CharField("담당 팀장", max_length=100, blank=True)
    owner_person = models.CharField("담당자", max_length=100, blank=True)
    opened_at = models.DateField("서비스 오픈일", null=True, blank=True)
    build_type = models.CharField("구축 구분", max_length=100, blank=True)
    dev_language = models.CharField("개발 언어", max_length=100, blank=True)
    dev_framework = models.CharField("개발 F/W", max_length=100, blank=True)
    cloud_type = models.CharField("Cloud 구분", max_length=100, blank=True)
    dbms = models.CharField("DBMS", max_length=100, blank=True)
    scm_tool = models.CharField("형상관리", max_length=100, blank=True)
    deploy_tool = models.CharField("배포도구", max_length=100, blank=True)
    monitoring_tool = models.CharField("모니터링도구", max_length=100, blank=True)
    frontend_stack = models.CharField("Front-End", max_length=200, blank=True)
    backend_stack = models.CharField("Back-End", max_length=200, blank=True)
    infra_env = models.CharField("운영환경", max_length=100, blank=True)
    automation_tool = models.CharField("자동화도구", max_length=100, blank=True)
    monitoring = models.CharField("모니터링", max_length=100, blank=True)
    itgc = models.BooleanField("ITGC 여부", default=False)
    gc = models.BooleanField("GC", default=False)
    pharma = models.BooleanField("파마", default=False)
    plasma = models.BooleanField("플라즈마", default=False)
    mu = models.BooleanField("MU", default=False)
    entis = models.BooleanField("엔티스", default=False)
    daejung = models.BooleanField("대정", default=False)
    dy = models.BooleanField("DY", default=False)
    bs = models.BooleanField("BS", default=False)
    bs_share_ratio = models.DecimalField("BS Share 비율", max_digits=6, decimal_places=2, null=True, blank=True)
    bs_share_note = models.TextField("BS Share 비고", blank=True)
    notes = models.TextField("비고", blank=True)
    extra = models.JSONField("추가필드", default=dict, blank=True)

    @classmethod
    def next_service_mgmt_no(cls):
        prefix = "SVC"
        with transaction.atomic():
            last = (
                cls.objects.filter(service_mgmt_no__startswith=prefix)
                .order_by("-service_mgmt_no")
                .values_list("service_mgmt_no", flat=True)
                .first()
            )
            next_no = int(last[3:]) + 1 if last else 1
            return f"{prefix}{next_no:04d}"

    def save(self, *args, **kwargs):
        if not self.service_mgmt_no:
            self.service_mgmt_no = self.next_service_mgmt_no()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PersonMaster(models.Model):
    person_mgmt_no = models.CharField("담당자관리번호", max_length=20, unique=True, blank=True, editable=False)
    system_name = models.CharField("담당 시스템", max_length=200, blank=True)
    name = models.CharField("성명", max_length=100)
    role = models.CharField("역할", max_length=20, blank=True)
    company = models.CharField("소속 조직", max_length=100, blank=True)
    employee_no = models.CharField("사번", max_length=50, blank=True)
    phone = models.CharField("연락처", max_length=50, blank=True)
    email = models.EmailField("내부 메일", blank=True)
    ext_email = models.EmailField("외부 메일", blank=True)
    resident = models.BooleanField("상주 여부", default=False)
    deployed_at = models.DateField("투입 일자", null=True, blank=True)
    notes = models.TextField("비고", blank=True)
    extra = models.JSONField("추가필드", default=dict, blank=True)

    @classmethod
    def next_person_mgmt_no(cls):
        prefix = "PRS"
        with transaction.atomic():
            last = (
                cls.objects.filter(person_mgmt_no__startswith=prefix)
                .order_by("-person_mgmt_no")
                .values_list("person_mgmt_no", flat=True)
                .first()
            )
            next_no = int(last[3:]) + 1 if last else 1
            return f"{prefix}{next_no:04d}"

    def save(self, *args, **kwargs):
        if not self.person_mgmt_no:
            self.person_mgmt_no = self.next_person_mgmt_no()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}({self.company})"


class Component(models.Model):
    asset_mgmt_no = models.CharField("자산관리번호", max_length=20, unique=True, blank=True, editable=False)
    hostname = models.CharField("Hostname", max_length=200, blank=True)
    system_name = models.CharField("시스템명", max_length=200, blank=True)
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

    @classmethod
    def next_asset_mgmt_no(cls):
        prefix = "AST"
        with transaction.atomic():
            last = (
                cls.objects.filter(asset_mgmt_no__startswith=prefix)
                .order_by("-asset_mgmt_no")
                .values_list("asset_mgmt_no", flat=True)
                .first()
            )
            next_no = int(last[3:]) + 1 if last else 1
            return f"{prefix}{next_no:04d}"

    def save(self, *args, **kwargs):
        if not self.asset_mgmt_no:
            self.asset_mgmt_no = self.next_asset_mgmt_no()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.hostname or self.asset_mgmt_no
