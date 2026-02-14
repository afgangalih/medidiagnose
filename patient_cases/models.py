"""
patient_cases/models.py
=======================
Models for storing patient diagnostic sessions and their outcomes.

Contains:
    - PatientCaseModel: A single diagnostic session for a patient,
      capturing reported symptoms, inferred results, and the trace
      of rules that fired.
"""

from __future__ import annotations

from django.db import models


class PatientCaseModel(models.Model):
    """Records a single patient diagnostic session.

    Each instance captures the full snapshot of a diagnostic interaction:
    the symptoms the patient reported, the ranked list of inferred
    diseases with confidence scores, and the rules that were applied.

    Attributes:
        patient_identifier: Opaque identifier for the patient / session.
        session_date: Timestamp auto-set when the case is created.
        reported_symptoms_snapshot: JSON list of ``{"id": int, "name": str}``
            dicts representing the symptoms that were reported.
        inferred_results: JSON list of ``{"disease_id": int,
            "disease_name": str, "confidence": float}`` dicts ranked
            by confidence descending.
        applied_rules_trace: JSON list of ``{"rule_id": int,
            "explanation": str}`` dicts for every rule that fired.
        final_diagnosis_notes: Optional free-text notes added by the
            clinician after reviewing the inference output.
    """

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    patient_identifier: str = models.CharField(
        max_length=100,
        help_text="Opaque patient or session identifier.",
    )
    session_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this diagnostic session was created.",
    )
    reported_symptoms_snapshot = models.JSONField(
        default=list,
        help_text='JSON list of symptom dicts, e.g. [{"id": 1, "name": "Fever"}].',
    )
    inferred_results = models.JSONField(
        default=list,
        help_text=(
            "Ranked list of inferred diseases with confidence scores, "
            'e.g. [{"disease_id": 1, "disease_name": "Flu", "confidence": 85.0}].'
        ),
    )
    applied_rules_trace = models.JSONField(
        default=list,
        help_text=(
            "Trace of rules that fired during inference, "
            'e.g. [{"rule_id": 1, "explanation": "..."}].'
        ),
    )
    final_diagnosis_notes: str = models.TextField(
        blank=True,
        default="",
        help_text="Optional clinician notes after reviewing inference results.",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering: list[str] = ["-session_date"]
        verbose_name: str = "Patient Case"
        verbose_name_plural: str = "Patient Cases"

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        formatted_date: str = (
            self.session_date.strftime("%Y-%m-%d %H:%M") if self.session_date else "N/A"
        )
        return f"Case {self.patient_identifier} – {formatted_date}"
