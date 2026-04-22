from django.contrib import admin
from django import forms

from core.code_choices import get_code_choices
from .models import Component, PersonMaster, ServiceMaster


class PersonAdminForm(forms.ModelForm):
    class Meta:
        model = PersonMaster
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        self.fields["role"].choices = get_code_choices(
            "person_role",
            include_blank=True,
            current_value=getattr(instance, "role", None),
        )


@admin.register(ServiceMaster)
class ServiceAdmin(admin.ModelAdmin):
    search_fields = ("name", "system_type", "description", "customer_owner", "appl_owner")
    list_display = ("service_mgmt_no", "name", "system_type", "operation_type", "service_grade", "itgc")
    list_filter = ("system_type", "operation_type", "itgc", "cloud_type")


@admin.register(PersonMaster)
class PersonAdmin(admin.ModelAdmin):
    form = PersonAdminForm
    search_fields = ("name", "employee_no", "system_name", "company", "email")
    list_display = ("person_mgmt_no", "name", "employee_no", "role", "system_name", "company", "resident", "deployed_at")
    list_filter = ("role", "resident", "company")


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    search_fields = ("asset_mgmt_no", "hostname", "system_name", "server_type", "platform_type", "ip")
    list_display = ("asset_mgmt_no", "hostname", "system_name", "server_type", "operation_dev", "network_zone", "platform_type", "ip")
    list_filter = ("server_type", "operation_dev", "network_zone", "platform_type")
