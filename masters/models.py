from django.db import models
from django.db import transaction

from core.models import Code, CodeGroup


def _next_prefixed_value(model_cls, field_name, prefix, width=4):
    with transaction.atomic():
        last = (
            model_cls.objects.filter(**{f"{field_name}__startswith": prefix})
            .order_by(f"-{field_name}")
            .values_list(field_name, flat=True)
            .first()
        )
        next_no = int(last[len(prefix) :]) + 1 if last else 1
        return f"{prefix}{next_no:0{width}d}"


class AuditStampMixin(models.Model):
    created_at = models.DateTimeField("생성일", auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField("수정일", auto_now=True, null=True, blank=True)
    created_by = models.CharField("생성자", max_length=100, blank=True)
    updated_by = models.CharField("수정자", max_length=100, blank=True)

    class Meta:
        abstract = True


class ServiceMaster(AuditStampMixin):
    service_mgmt_no = models.CharField("서비스 ID", max_length=20, unique=True, blank=True, editable=False)
    name = models.CharField("서비스 명", max_length=200)
    category_code = models.ForeignKey(
        Code,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_category_items",
        verbose_name="서비스 분류",
    )
    ito_code = models.ForeignKey(
        Code,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_ito_items",
        verbose_name="ITO",
    )
    status_code = models.ForeignKey(
        Code,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_status_items",
        verbose_name="서비스 상태",
    )
    build_type_code = models.ForeignKey(
        Code,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_build_type_items",
        verbose_name="구축 구분",
    )
    itgc_code = models.ForeignKey(
        Code,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_itgc_items",
        verbose_name="ITGC 여부",
    )
    service_grade_code = models.ForeignKey(
        Code,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="service_grade_items",
        verbose_name="서비스 등급",
    )
    opened_at = models.DateField("서비스 오픈일", null=True, blank=True)
    ended_at = models.DateField("서비스 종료일", null=True, blank=True)
    description = models.TextField("설명", blank=True)

    class Meta:
        ordering = ["service_mgmt_no", "name"]

    def save(self, *args, **kwargs):
        if not self.service_mgmt_no:
            self.service_mgmt_no = _next_prefixed_value(ServiceMaster, "service_mgmt_no", "SVC")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AttributeCode(models.Model):
    attribute_code = models.CharField("속성 코드", max_length=50, primary_key=True)
    name = models.CharField("속성명", max_length=200)
    data_type_code = models.ForeignKey(
        Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="attribute_data_type_codes", verbose_name="데이터 타입"
    )
    required_code = models.ForeignKey(
        Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="attribute_required_codes", verbose_name="필수 여부"
    )
    searchable_code = models.ForeignKey(
        Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="attribute_searchable_codes", verbose_name="검색 가능 여부"
    )
    code_group = models.ForeignKey(
        CodeGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="attribute_codes", verbose_name="코드 그룹"
    )
    target_code = models.ForeignKey(
        Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="attribute_target_codes", verbose_name="적용 대상"
    )

    class Meta:
        ordering = ["attribute_code"]

    def __str__(self):
        return f"{self.attribute_code} - {self.name}"


class PersonMaster(models.Model):
    person_mgmt_no = models.CharField("담당자 ID", max_length=20, unique=True, blank=True, editable=False)
    employee_no = models.CharField("사번", max_length=50, unique=True, null=True, blank=True)
    name = models.CharField("성명", max_length=100)
    role_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="person_roles", verbose_name="역할")
    resident_type_code = models.ForeignKey(
        Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="person_resident_types", verbose_name="상주 여부"
    )
    affiliation_code = models.ForeignKey(
        Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="person_affiliations", verbose_name="소속"
    )
    company = models.CharField("회사명", max_length=100, blank=True)
    phone = models.CharField("전화번호", max_length=50, blank=True)
    email = models.EmailField("내부 이메일", blank=True)
    external_email = models.EmailField("외부 이메일", blank=True)
    gender_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="person_genders", verbose_name="성별")
    status_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="person_statuses", verbose_name="상태")
    deployed_at = models.DateField("투입 일자", null=True, blank=True)
    ended_at = models.DateField("종료 일자", null=True, blank=True)

    class Meta:
        ordering = ["person_mgmt_no", "name"]

    def save(self, *args, **kwargs):
        if not self.person_mgmt_no:
            self.person_mgmt_no = _next_prefixed_value(PersonMaster, "person_mgmt_no", "PRS")
        if not (self.employee_no or "").strip():
            self.employee_no = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}({self.employee_no or '-'})"


class ConfigurationMaster(AuditStampMixin):
    asset_mgmt_no = models.CharField("구성 ID", max_length=20, unique=True, blank=True, editable=False)
    hostname = models.CharField("구성명", max_length=200)
    server_type_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="config_types", verbose_name="구성 유형")
    operation_dev_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="config_operation_types", verbose_name="운영/개발")
    infra_type_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="config_infra_types", verbose_name="인프라 구분")
    location_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="config_locations", verbose_name="인프라 위치")
    network_zone_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="config_network_zones", verbose_name="네트웍 구분")
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    port = models.CharField("Port", max_length=20, blank=True)
    url = models.CharField("URL", max_length=300, blank=True)

    class Meta:
        ordering = ["asset_mgmt_no", "hostname"]

    def save(self, *args, **kwargs):
        if not self.asset_mgmt_no:
            self.asset_mgmt_no = _next_prefixed_value(ConfigurationMaster, "asset_mgmt_no", "CFG")
        super().save(*args, **kwargs)

    @property
    def connected_services_label(self) -> str:
        """서비스-구성 매핑에 연결된 서비스명(표시용). prefetch_related 권장."""
        if not self.pk:
            return ""
        names = sorted(
            {m.service.name for m in self.service_configuration_mappings.all() if m.service_id}
        )
        return ", ".join(names)

    def __str__(self):
        return self.hostname or self.asset_mgmt_no


class Component(AuditStampMixin):
    component_mgmt_no = models.CharField("컴포넌트 ID", max_length=20, unique=True, blank=True, editable=False)
    component_type_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="component_types", verbose_name="컴포넌트 유형")
    product_name = models.CharField("컴포넌트명", max_length=200, default="", blank=True)
    version = models.CharField("버전", max_length=100, blank=True)
    vendor_name = models.CharField("벤더명", max_length=200, blank=True)
    cpe_name = models.CharField("CPE 이름", max_length=300, blank=True)
    eos_date = models.DateField("EOS 날짜", null=True, blank=True)
    eol_date = models.DateField("EOL 날짜", null=True, blank=True)
    support_status_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="component_support_statuses", verbose_name="지원 여부")

    class Meta:
        ordering = ["component_mgmt_no", "product_name"]

    def save(self, *args, **kwargs):
        if not self.component_mgmt_no:
            self.component_mgmt_no = _next_prefixed_value(Component, "component_mgmt_no", "CMP")
        super().save(*args, **kwargs)

    def __str__(self):
        return " ".join(p for p in (self.product_name, self.version) if (p or "").strip()).strip()


class ComponentAlias(models.Model):
    """컴포넌트 검색을 위한 product_name 별 alias 사전.

    예) product_name="OpenJDK", alias="java" 행이 존재하면 "java" 검색 시
    OpenJDK가 결과에 포함된다. 같은 alias가 여러 product_name에 매핑될 수 있다.
    """

    id = models.BigAutoField(primary_key=True, verbose_name="컴포넌트 alias ID")
    product_name = models.CharField("제품명", max_length=200)
    alias = models.CharField("Alias", max_length=200)

    class Meta:
        unique_together = [("product_name", "alias")]
        indexes = [
            models.Index(fields=["alias"]),
            models.Index(fields=["product_name"]),
        ]
        ordering = ["product_name", "alias"]
        verbose_name = "컴포넌트 alias"
        verbose_name_plural = "컴포넌트 alias"

    def __str__(self):
        return f"{self.product_name} ← {self.alias}"


class ServiceAttribute(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="서비스 속성 ID")
    service = models.ForeignKey(ServiceMaster, on_delete=models.CASCADE, related_name="service_attributes", verbose_name="서비스 ID")
    attribute_code = models.ForeignKey(AttributeCode, on_delete=models.CASCADE, related_name="service_attributes", verbose_name="속성 코드")
    value = models.TextField("속성 값", blank=True)

    class Meta:
        unique_together = ("service", "attribute_code")


class ConfigurationAttribute(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="구성정보 속성 ID")
    configuration = models.ForeignKey(ConfigurationMaster, on_delete=models.CASCADE, related_name="configuration_attributes", verbose_name="구성 ID")
    attribute_code = models.ForeignKey(AttributeCode, on_delete=models.CASCADE, related_name="configuration_attributes", verbose_name="속성 코드")
    value = models.TextField("속성 값", blank=True)

    class Meta:
        unique_together = ("configuration", "attribute_code")


class ServicePersonMapping(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="서비스 담당자 매핑 ID")
    service = models.ForeignKey(ServiceMaster, on_delete=models.CASCADE, related_name="service_person_mappings", verbose_name="서비스 ID")
    person = models.ForeignKey(PersonMaster, on_delete=models.CASCADE, related_name="service_person_mappings", verbose_name="담당자 ID")
    role_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="service_person_mapping_roles", verbose_name="역할")
    status_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="service_person_mapping_statuses", verbose_name="상태")
    started_at = models.DateField("시작일", null=True, blank=True)
    ended_at = models.DateField("종료일", null=True, blank=True)


class ServiceConfigurationMapping(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="서비스 구성 매핑 ID")
    service = models.ForeignKey(ServiceMaster, on_delete=models.CASCADE, related_name="service_configuration_mappings", verbose_name="서비스 ID")
    configuration = models.ForeignKey(ConfigurationMaster, on_delete=models.CASCADE, related_name="service_configuration_mappings", verbose_name="구성 ID")
    status_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="service_configuration_mapping_statuses", verbose_name="상태")
    started_at = models.DateField("시작일", null=True, blank=True)
    ended_at = models.DateField("종료일", null=True, blank=True)


class ConfigurationComponentMapping(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="구성 컴포넌트 ID")
    configuration = models.ForeignKey(ConfigurationMaster, on_delete=models.CASCADE, related_name="configuration_component_mappings", verbose_name="구성 ID")
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name="configuration_component_mappings", verbose_name="컴포넌트 ID")
    install_path = models.CharField("설치 경로", max_length=300, blank=True)
    use_yn_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="configuration_component_use_flags", verbose_name="사용 여부")
    started_at = models.DateField("시작일", null=True, blank=True)
    ended_at = models.DateField("종료일", null=True, blank=True)


class Certificate(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="인증서 ID")
    configuration = models.ForeignKey(ConfigurationMaster, on_delete=models.CASCADE, related_name="certificates", verbose_name="구성 ID")
    domain = models.CharField("도메인", max_length=200)
    cert_format = models.CharField("인증서 포맷", max_length=100, blank=True)
    expires_at = models.DateField("만료일", null=True, blank=True)
    issuer = models.CharField("발급기관", max_length=200, blank=True)
    use_yn_code = models.ForeignKey(Code, null=True, blank=True, on_delete=models.SET_NULL, related_name="certificate_use_flags", verbose_name="사용 여부")


class ChangeHistory(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="이력 ID")
    table_name = models.CharField("테이블 명", max_length=100)
    pk_value = models.CharField("PK 값", max_length=100)
    field_name = models.CharField("변경 필드", max_length=100)
    before_value = models.TextField("변경 전 값", blank=True)
    after_value = models.TextField("변경 후 값", blank=True)
    changed_by = models.CharField("변경자", max_length=100, blank=True)
    changed_at = models.DateTimeField("변경일", auto_now_add=True)
