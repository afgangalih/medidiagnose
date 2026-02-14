"""
URL configuration for medidiagnose project.

Routes:
    /           → Symptom Checker (patient_cases app)
    /result/    → Diagnosis results (patient_cases app)
    /history/   → Case history (patient_cases app)
    /api/v1/    → REST API (api app)
    /admin/     → Django Admin
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # REST API (DRF)
    path("api/v1/", include("api.urls", namespace="api")),
    # Patient Cases (traditional views — serves as the main UI)
    path("", include("patient_cases.urls", namespace="patient_cases")),
]
