from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "web"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("assets/", views.asset_list, name="asset_list"),
    path("assets/<str:pk>/", views.asset_detail, name="asset_detail"),
    path("masters/services/", views.service_master_list, name="service_master_list"),
    path("masters/persons/", views.person_master_list, name="person_master_list"),
    path("masters/configuration-master/", views.configuration_master_list, name="configuration_master_list"),
    path("masters/component-master/", views.component_master_list, name="component_master_list"),
    path(
        "masters/configurations/",
        RedirectView.as_view(pattern_name="web:configuration_master_list", permanent=False),
    ),
    path(
        "masters/components/",
        RedirectView.as_view(pattern_name="web:component_master_list", permanent=False),
    ),
    path("ai/search/", views.ai_asset_search, name="ai_asset_search"),
]
