from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("assets/", views.asset_list, name="asset_list"),
    path("assets/<int:pk>/", views.asset_detail, name="asset_detail"),
    path("masters/services/", views.service_master_list, name="service_master_list"),
    path("masters/persons/", views.person_master_list, name="person_master_list"),
    path("masters/components/", views.component_master_list, name="component_master_list"),
    path("ai/search/", views.ai_asset_search, name="ai_asset_search"),
]
