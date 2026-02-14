"""
api/urls.py
===========
URL configuration for the MediDiagnose REST API.

All endpoints are prefixed with ``/api/v1/`` by the project-level router.
"""

from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path(
        "symptoms/",
        views.SymptomListAPIView.as_view(),
        name="symptom-list",
    ),
    path(
        "diagnose/",
        views.DiagnosisAPIView.as_view(),
        name="diagnose",
    ),
    path(
        "explanation/<int:case_id>/",
        views.ExplanationAPIView.as_view(),
        name="explanation",
    ),
]
