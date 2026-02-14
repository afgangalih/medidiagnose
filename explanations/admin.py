"""
explanations/admin.py
=====================
Django admin configuration for inference explanation models.
"""

from django.contrib import admin

from .models import InferenceTraceModel


@admin.register(InferenceTraceModel)
class InferenceTraceModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`InferenceTraceModel`."""

    list_display: list[str] = [
        "patient_case",
        "strategy_used",
        "execution_timestamp",
        "execution_time_ms",
    ]
    list_filter: list[str] = ["strategy_used", "execution_timestamp"]
    search_fields: list[str] = [
        "patient_case__patient_identifier",
        "strategy_used",
    ]
    readonly_fields: list[str] = ["execution_timestamp"]
    list_per_page: int = 25
