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
    path("api/integrated-view/presets/", iv.integrated_view_presets, name="integrated_view_presets"),
    path("api/integrated-view/presets/save/", iv.integrated_view_presets_save, name="integrated_view_presets_save"),
    path("api/integrated-view/presets/clear/", iv.integrated_view_presets_clear, name="integrated_view_presets_clear"),
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
