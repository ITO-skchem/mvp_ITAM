from django.urls import path
from django.views.generic import RedirectView

from . import views
from . import integrated_view as iv

app_name = "web"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("integrated-view/", iv.integrated_view, name="integrated_view"),
    path("api/integrated-view/meta/", iv.integrated_view_meta, name="integrated_view_meta"),
    path("api/integrated-view/search/", iv.integrated_view_search, name="integrated_view_search"),
    path("api/integrated-view/export/", iv.integrated_view_export, name="integrated_view_export"),
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
