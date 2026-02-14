"""
knowledge_base/admin.py
=======================
Django admin configuration for knowledge base models.
"""

from django.contrib import admin

from .models import DiagnosticRuleModel, DiseaseModel, SymptomModel


@admin.register(SymptomModel)
class SymptomModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`SymptomModel`."""

    list_display: list[str] = ["name", "category", "severity_weight"]
    list_filter: list[str] = ["category", "severity_weight"]
    search_fields: list[str] = ["name"]
    list_per_page: int = 25


@admin.register(DiseaseModel)
class DiseaseModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`DiseaseModel`."""

    list_display: list[str] = ["name", "urgency_level", "description"]
    list_filter: list[str] = ["urgency_level"]
    search_fields: list[str] = ["name", "description"]
    list_per_page: int = 25


@admin.register(DiagnosticRuleModel)
class DiagnosticRuleModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`DiagnosticRuleModel`."""

    list_display: list[str] = ["name", "then_disease", "confidence_factor"]
    list_filter: list[str] = ["confidence_factor", "then_disease"]
    search_fields: list[str] = ["name", "then_disease__name"]
    filter_horizontal: list[str] = ["if_symptoms"]
    list_per_page: int = 25
