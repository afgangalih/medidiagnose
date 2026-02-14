"""
knowledge_base/admin.py
=======================
Django admin configuration for knowledge base models.

Customized DiagnosticRuleModelAdmin with:
    - Inline symptom selection via filter_horizontal.
    - Confidence factor displayed as a slider in the form.
"""

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import DiagnosticRuleModel, DiseaseModel, SymptomModel


# ─────────────────────────────────────────────────────────────────────
# Symptom Admin
# ─────────────────────────────────────────────────────────────────────


@admin.register(SymptomModel)
class SymptomModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`SymptomModel`."""

    list_display: list[str] = ["name", "category", "severity_weight"]
    list_filter: list[str] = ["category", "severity_weight"]
    search_fields: list[str] = ["name"]
    list_per_page: int = 25


# ─────────────────────────────────────────────────────────────────────
# Disease Admin
# ─────────────────────────────────────────────────────────────────────


@admin.register(DiseaseModel)
class DiseaseModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`DiseaseModel`."""

    list_display: list[str] = ["name", "urgency_level", "description"]
    list_filter: list[str] = ["urgency_level"]
    search_fields: list[str] = ["name", "description"]
    list_per_page: int = 25


# ─────────────────────────────────────────────────────────────────────
# Diagnostic Rule Admin — Custom Form with Slider
# ─────────────────────────────────────────────────────────────────────


class DiagnosticRuleAdminForm(forms.ModelForm):
    """Custom form for :class:`DiagnosticRuleModel` in the admin.

    Renders the ``confidence_factor`` field as an HTML range slider
    with a live numeric readout beside it.
    """

    confidence_factor = forms.IntegerField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(
            attrs={
                "type": "range",
                "min": "0",
                "max": "100",
                "step": "1",
                "class": "form-range",
                "style": "width: 300px; vertical-align: middle;",
                "oninput": "document.getElementById('cf-value').textContent = this.value + '%';",
            }
        ),
        help_text="Rule confidence factor (0–100 %). Drag the slider to adjust.",
    )

    class Meta:
        model = DiagnosticRuleModel
        fields = "__all__"


@admin.register(DiagnosticRuleModel)
class DiagnosticRuleModelAdmin(admin.ModelAdmin):
    """Admin view for :class:`DiagnosticRuleModel`.

    Features:
        - ``filter_horizontal`` widget for inline symptom selection.
        - Range slider for the confidence factor.
        - Colored confidence display in the list view.
    """

    form = DiagnosticRuleAdminForm

    list_display: list[str] = [
        "name",
        "then_disease",
        "confidence_bar",
        "symptom_count",
    ]
    list_filter: list[str] = ["confidence_factor", "then_disease"]
    search_fields: list[str] = ["name", "then_disease__name"]
    filter_horizontal: tuple[str, ...] = ("if_symptoms",)
    list_per_page: int = 25

    fieldsets = (
        (
            "Rule Definition",
            {
                "fields": ("name", "then_disease", "explanation_template"),
            },
        ),
        (
            "Symptoms (IF conditions)",
            {
                "fields": ("if_symptoms",),
                "description": "Select the symptoms that must be present for this rule to fire.",
            },
        ),
        (
            "Confidence",
            {
                "fields": ("confidence_factor",),
                "description": (
                    'Drag the slider to set the confidence percentage. '
                    '<span id="cf-value" style="font-weight: bold; font-size: 1.1em; '
                    'color: #4f46e5;"></span>'
                ),
            },
        ),
    )

    @admin.display(description="Confidence")
    def confidence_bar(self, obj: DiagnosticRuleModel) -> str:
        """Render a mini progress bar for the confidence factor."""
        cf = obj.confidence_factor
        if cf >= 70:
            colour = "#10b981"
        elif cf >= 40:
            colour = "#f59e0b"
        else:
            colour = "#ef4444"
        return format_html(
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<div style="width:80px; height:8px; background:#e2e8f0; '
            'border-radius:4px; overflow:hidden;">'
            '<div style="width:{}%; height:100%; background:{}; '
            'border-radius:4px;"></div></div>'
            '<span style="font-weight:600; font-size:0.85em;">{}%</span></div>',
            cf,
            colour,
            cf,
        )

    @admin.display(description="Symptoms")
    def symptom_count(self, obj: DiagnosticRuleModel) -> int:
        """Display the number of associated symptoms."""
        return obj.if_symptoms.count()
