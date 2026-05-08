from django.contrib import admin
from .models import (
    AttributeCode,
    Certificate,
    ChangeHistory,
    Component,
    ConfigurationMaster,
    ConfigurationAttribute,
    ConfigurationComponentMapping,
    PersonMaster,
    ServiceAttribute,
    ServiceConfigurationMapping,
    ServiceMaster,
    ServicePersonMapping,
)


@admin.register(ServiceMaster)
class ServiceAdmin(admin.ModelAdmin):
    search_fields = ("service_mgmt_no", "name", "description")
    list_display = ("service_mgmt_no", "name", "category_code", "status_code", "build_type_code", "service_grade_code")
    list_filter = ("category_code", "status_code", "build_type_code", "service_grade_code")


@admin.register(PersonMaster)
class PersonAdmin(admin.ModelAdmin):
    search_fields = ("person_mgmt_no", "name", "employee_no", "company", "email")
    list_display = ("person_mgmt_no", "name", "employee_no", "role_code", "status_code", "company", "deployed_at")
    list_filter = ("role_code", "status_code", "company")


@admin.register(ConfigurationMaster)
class ConfigurationMasterAdmin(admin.ModelAdmin):
    search_fields = ("asset_mgmt_no", "hostname", "ip", "url")
    list_display = ("asset_mgmt_no", "hostname", "server_type_code", "operation_dev_code", "infra_type_code", "network_zone_code", "ip")
    list_filter = ("server_type_code", "operation_dev_code", "infra_type_code", "network_zone_code")


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    search_fields = ("component_mgmt_no", "product_name", "version", "vendor_name", "cpe_name")
    list_display = ("component_mgmt_no", "product_name", "version", "component_type_code", "vendor_name", "support_status_code")
    list_filter = ("component_type_code", "support_status_code")


@admin.register(AttributeCode)
class AttributeCodeAdmin(admin.ModelAdmin):
    list_display = ("attribute_code", "name", "data_type_code", "required_code", "searchable_code", "target_code")
    search_fields = ("attribute_code", "name")


@admin.register(ServiceAttribute)
class ServiceAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "attribute_code", "value")


@admin.register(ConfigurationAttribute)
class ConfigurationAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "attribute_code", "value")


@admin.register(ServicePersonMapping)
class ServicePersonMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "person", "role_code", "status_code", "started_at", "ended_at")


@admin.register(ServiceConfigurationMapping)
class ServiceConfigurationMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "configuration", "status_code", "started_at", "ended_at")


@admin.register(ConfigurationComponentMapping)
class ConfigurationComponentMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "component", "install_path", "use_yn_code", "started_at", "ended_at")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "domain", "cert_format", "expires_at", "issuer", "use_yn_code")


@admin.register(ChangeHistory)
class ChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "table_name", "pk_value", "field_name", "changed_by", "changed_at")
