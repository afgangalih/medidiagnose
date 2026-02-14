"""
patient_cases/admin.py
======================
Django admin configuration for patient case models.
"""

from django.contrib import admin

from .models import PatientCaseModel


@admin.register(PatientCaseModel)
class PatientCaseModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`PatientCaseModel`."""

    list_display: list[str] = [
        "patient_identifier",
        "session_date",
        "final_diagnosis_notes",
    ]
    list_filter: list[str] = ["session_date"]
    search_fields: list[str] = ["patient_identifier", "final_diagnosis_notes"]
    readonly_fields: list[str] = ["session_date"]
    list_per_page: int = 25
