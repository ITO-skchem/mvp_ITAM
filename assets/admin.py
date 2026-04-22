from django.contrib import admin
from django import forms

from core.code_choices import get_code_choices
from .models import InfraAsset


class InfraAssetAdminForm(forms.ModelForm):
    class Meta:
        model = InfraAsset
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")

        self.fields["use_flag"].choices = get_code_choices(
            "use_flag",
            include_blank=False,
            current_value=getattr(instance, "use_flag", None),
        )
        self.fields["devops_type"].choices = get_code_choices(
            "devops_type",
            include_blank=True,
            current_value=getattr(instance, "devops_type", None),
        )
        self.fields["infra_type"].choices = get_code_choices(
            "infra_type",
            include_blank=True,
            current_value=getattr(instance, "infra_type", None),
        )
        self.fields["network_zone"].choices = get_code_choices(
            "network_zone",
            include_blank=True,
            current_value=getattr(instance, "network_zone", None),
        )
        self.fields["platform_type"].choices = get_code_choices(
            "platform_type",
            include_blank=True,
            current_value=getattr(instance, "platform_type", None),
        )


@admin.register(InfraAsset)
class InfraAssetAdmin(admin.ModelAdmin):
    form = InfraAssetAdminForm
    search_fields = ("system_name", "hostname", "ip", "db_hostname", "db_ip")
    list_display = (
        "no",
        "system_name",
        "infra_type",
        "network_zone",
        "platform_type",
        "ip",
        "db_ip",
        "use_flag",
    )
    list_filter = ("infra_type", "network_zone", "platform_type", "use_flag", "devops_type")
    filter_horizontal = ("extra_persons", "components")
