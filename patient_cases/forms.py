"""
patient_cases/forms.py
======================
Django forms for the patient case symptom checker.
"""

from __future__ import annotations

from django import forms

from knowledge_base.models import SymptomModel


class SymptomCheckForm(forms.Form):
    """Form for selecting symptoms in the symptom checker view.

    Uses a ``ModelMultipleChoiceField`` backed by checkboxes so users
    can select one or more symptoms from the knowledge base.
    """

    symptoms = forms.ModelMultipleChoiceField(
        queryset=SymptomModel.objects.all(),
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "form-check-input symptom-checkbox"}
        ),
        label="Select your symptoms",
        help_text="Check all symptoms that apply to you.",
    )

    patient_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. PT-001",
            }
        ),
        label="Patient Identifier",
        help_text="Enter a patient or session identifier.",
    )
