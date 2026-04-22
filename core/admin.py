from django.contrib import admin

from .models import AuditLog, Code, CodeGroup


class CodeInline(admin.TabularInline):
    model = Code
    extra = 1
    fields = ("code", "name", "is_active", "sort_order", "description")
    ordering = ("sort_order", "code")


@admin.register(CodeGroup)
class CodeGroupAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("key", "name")
    inlines = (CodeInline,)


@admin.register(Code)
class CodeAdmin(admin.ModelAdmin):
    list_display = ("group", "code", "name", "is_active", "sort_order")
    list_filter = ("group", "is_active")
    search_fields = ("group__key", "code", "name")
    ordering = ("group__sort_order", "group__key", "sort_order", "code")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "app_label", "model_name", "object_id", "action", "user")
    list_filter = ("app_label", "model_name", "action", "user")
    search_fields = ("object_id",)
