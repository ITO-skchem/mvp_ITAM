from django.urls import path

from .views import asset_ai_search

urlpatterns = [
    path("ai/search", asset_ai_search, name="asset_ai_search"),
]
