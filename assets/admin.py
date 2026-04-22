from django.contrib import admin

from .models import InfraAsset


@admin.register(InfraAsset)
class InfraAssetAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = (
        "system_mgmt_no",
        "service_mgmt_no",
        "asset_mgmt_no",
        "service_name",
        "hostname",
        "ip",
        "operation_dev",
    )
    search_fields = (
        "system_mgmt_no",
        "service_mgmt_no",
        "asset_mgmt_no",
        "service_name",
        "hostname",
        "customer_owner_name",
        "appl_owner_name",
        "partner_operator_name",
    )
    list_filter = ("operation_dev", "network_zone", "platform_type")
    readonly_fields = [f.name for f in InfraAsset._meta.fields]
