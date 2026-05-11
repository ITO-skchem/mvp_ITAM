from django.conf import settings
from django.db import models


class IntegratedViewPreset(models.Model):
    """로그인 사용자별 시스템 통합정보 조회 프리셋(즐겨찾기)."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="integrated_view_presets")
    slot = models.PositiveSmallIntegerField()  # 1~3
    name = models.CharField(max_length=100, blank=True, default="")
    selected_fields = models.JSONField(default=list, blank=True)
    conditions = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "slot")]
        indexes = [models.Index(fields=["user", "slot"])]
        ordering = ["user_id", "slot"]

    def __str__(self) -> str:
        return f"IntegratedViewPreset(user={self.user_id}, slot={self.slot})"
