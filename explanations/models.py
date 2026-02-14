"""
explanations/models.py
======================
Models for logging inference execution traces and explanations.

Contains:
    - InferenceTraceModel: Detailed log of a single inference run,
      including the strategy used, rules fired, calculated confidence
      scores, and execution time.
"""

from __future__ import annotations

from django.db import models

from patient_cases.models import PatientCaseModel


class InferenceTraceModel(models.Model):
    """Detailed execution log for a single inference run.

    Each trace records *how* the inference engine arrived at its
    conclusions, enabling full auditability and explainability.

    Attributes:
        patient_case: The case this trace belongs to.
        execution_timestamp: Auto-set timestamp of the inference run.
        strategy_used: Inference strategy applied (forward / backward chaining).
        rules_fired: JSON list of rule IDs and metadata that fired.
        confidence_scores_calculated: JSON dict of disease-to-score mappings.
        execution_time_ms: Wall-clock execution time in milliseconds.
    """

    class Strategy(models.TextChoices):
        """Allowed inference strategies."""

        FORWARD_CHAINING = "FORWARD_CHAINING", "Forward Chaining"
        BACKWARD_CHAINING = "BACKWARD_CHAINING", "Backward Chaining"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    patient_case: models.ForeignKey = models.ForeignKey(
        PatientCaseModel,
        on_delete=models.CASCADE,
        related_name="inference_logs",
        help_text="The patient case this inference trace belongs to.",
    )
    execution_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when inference was executed.",
    )
    strategy_used: str = models.CharField(
        max_length=20,
        choices=Strategy.choices,
        help_text="Inference strategy that was applied.",
    )
    rules_fired = models.JSONField(
        default=list,
        help_text=(
            "JSON list of rules that fired during inference, "
            'e.g. [{"rule_id": 1, "name": "Rule-Flu-01", "confidence": 85}].'
        ),
    )
    confidence_scores_calculated = models.JSONField(
        default=dict,
        help_text=(
            "JSON dict mapping disease IDs/names to calculated confidence scores, "
            'e.g. {"Flu": 85.0, "Cold": 60.5}.'
        ),
    )
    execution_time_ms: int = models.PositiveIntegerField(
        help_text="Inference execution time in milliseconds.",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering: list[str] = ["-execution_timestamp"]
        verbose_name: str = "Inference Trace"
        verbose_name_plural: str = "Inference Traces"

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return (
            f"Trace for {self.patient_case.patient_identifier} "
            f"– {self.get_strategy_used_display()} "
            f"({self.execution_time_ms}ms)"
        )
