"""
patient_cases/urls.py
=====================
URL configuration for the patient_cases app.
"""

from django.urls import path

from . import views

app_name = "patient_cases"

urlpatterns = [
    path(
        "",
        views.SymptomCheckerFormView.as_view(),
        name="symptom-checker",
    ),
    path(
        "result/<int:pk>/",
        views.DiagnosisResultDetailView.as_view(),
        name="diagnosis-result",
    ),
    path(
        "history/",
        views.CaseHistoryListView.as_view(),
        name="case-history",
    ),
]
