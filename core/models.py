from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CodeGroup(models.Model):
    key = models.CharField("그룹키", max_length=50, unique=True)
    name = models.CharField("그룹명", max_length=100)
    description = models.TextField("설명", blank=True)
    is_active = models.BooleanField("사용여부", default=True)
    sort_order = models.PositiveIntegerField("정렬순서", default=100)
    extra = models.JSONField("추가필드", default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "key"]

    def __str__(self):
        return f"{self.key} ({self.name})"


class Code(models.Model):
    group = models.ForeignKey(CodeGroup, on_delete=models.CASCADE, related_name="codes", verbose_name="코드그룹")
    code = models.CharField("코드값", max_length=50)
    name = models.CharField("코드명", max_length=100)
    description = models.TextField("설명", blank=True)
    is_active = models.BooleanField("사용여부", default=True)
    sort_order = models.PositiveIntegerField("정렬순서", default=100)
    extra = models.JSONField("추가필드", default=dict, blank=True)

    class Meta:
        ordering = ["group__sort_order", "group__key", "sort_order", "code"]
        unique_together = ("group", "code")

    def __str__(self):
        return f"{self.group.key}:{self.code} ({self.name})"


class AuditLog(models.Model):
    ACTIONS = [("CREATE", "생성"), ("UPDATE", "수정"), ("DELETE", "삭제")]
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    action = models.CharField(max_length=10, choices=ACTIONS)
    changes = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} {self.model_name}#{self.object_id} {self.action}"
