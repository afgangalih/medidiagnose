"""
api/serializers.py
==================
DRF serializers for the MediDiagnose REST API.

Contains:
    - SymptomSerializer: Read-only representation of symptoms.
    - DiseaseSerializer: Read-only representation of diseases.
    - DiagnosticRuleSerializer: Nested serializer with inline symptoms.
    - PatientCaseSerializer: Read-only representation of diagnostic sessions.
    - DiagnosisRequestSerializer: Input validation for the /diagnose endpoint.
"""

from __future__ import annotations

from rest_framework import serializers

from knowledge_base.models import DiagnosticRuleModel, DiseaseModel, SymptomModel
from patient_cases.models import PatientCaseModel


# ─────────────────────────────────────────────────────────────────────
# Read-only serializers
# ─────────────────────────────────────────────────────────────────────


class SymptomSerializer(serializers.ModelSerializer):
    """Serializer for :class:`SymptomModel`.

    Exposes all fields needed for the symptom listing and
    the symptom-checker UI.
    """

    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )

    class Meta:
        model = SymptomModel
        fields = [
            "id",
            "name",
            "category",
            "category_display",
            "severity_weight",
        ]
        read_only_fields = fields


class DiseaseSerializer(serializers.ModelSerializer):
    """Serializer for :class:`DiseaseModel`.

    Includes the human-readable urgency level display value.
    """

    urgency_display = serializers.CharField(
        source="get_urgency_level_display",
        read_only=True,
    )

    class Meta:
        model = DiseaseModel
        fields = [
            "id",
            "name",
            "description",
            "treatments",
            "urgency_level",
            "urgency_display",
        ]
        read_only_fields = fields


class DiagnosticRuleSerializer(serializers.ModelSerializer):
    """Nested serializer for :class:`DiagnosticRuleModel`.

    Inlines the related symptoms and the target disease so that a
    single API call returns the full rule definition.
    """

    if_symptoms = SymptomSerializer(many=True, read_only=True)
    then_disease = DiseaseSerializer(read_only=True)

    class Meta:
        model = DiagnosticRuleModel
        fields = [
            "id",
            "name",
            "if_symptoms",
            "then_disease",
            "confidence_factor",
            "explanation_template",
        ]
        read_only_fields = fields


class PatientCaseSerializer(serializers.ModelSerializer):
    """Read-only serializer for :class:`PatientCaseModel`.

    Exposes the full snapshot of a completed diagnostic session.
    """

    class Meta:
        model = PatientCaseModel
        fields = [
            "id",
            "patient_identifier",
            "session_date",
            "reported_symptoms_snapshot",
            "inferred_results",
            "applied_rules_trace",
            "final_diagnosis_notes",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────────
# Input serializers
# ─────────────────────────────────────────────────────────────────────


class DiagnosisRequestSerializer(serializers.Serializer):
    """Input validation for the diagnosis endpoint.

    Validates that the caller provides a patient identifier and
    a non-empty list of symptom IDs.
    """

    patient_id = serializers.CharField(
        max_length=100,
        help_text="Opaque patient or session identifier.",
    )
    symptom_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        help_text="List of symptom primary-key IDs to diagnose against.",
    )

    def validate_symptom_ids(self, value: list[int]) -> list[int]:
        """Ensure all symptom IDs actually exist in the database."""
        existing_ids = set(
            SymptomModel.objects.filter(id__in=value).values_list("id", flat=True)
        )
        missing = set(value) - existing_ids
        if missing:
            raise serializers.ValidationError(
                f"The following symptom IDs do not exist: {sorted(missing)}"
            )
        return value
