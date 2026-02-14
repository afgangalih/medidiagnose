"""
knowledge_base/models.py
========================
Core domain models for the medical knowledge base.

Contains:
    - SymptomModel: Represents individual medical symptoms with categorisation.
    - DiseaseModel: Represents diseases with treatment info and urgency levels.
    - DiagnosticRuleModel: IF-THEN rules mapping symptom sets to diseases
      with confidence factors and explanation templates.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SymptomModel(models.Model):
    """A single medical symptom used as input for diagnostic inference.

    Attributes:
        name: Unique human-readable symptom name (e.g. "Persistent Cough").
        category: Symptom category drawn from ``CATEGORY_CHOICES``.
        severity_weight: Relative severity weight (1–5 scale, default 1).
    """

    class Category(models.TextChoices):
        """Allowed symptom categories."""

        GENERAL = "GENERAL", "General"
        RESPIRATORY = "RESPIRATORY", "Respiratory"
        DIGESTIVE = "DIGESTIVE", "Digestive"
        NEUROLOGICAL = "NEUROLOGICAL", "Neurological"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name: str = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique symptom name.",
    )
    category: str = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        help_text="Broad medical category this symptom belongs to.",
    )
    severity_weight: int = models.PositiveSmallIntegerField(
        default=1,
        help_text="Relative severity weight (higher = more severe).",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering: list[str] = ["category", "name"]
        verbose_name: str = "Symptom"
        verbose_name_plural: str = "Symptoms"

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"


class DiseaseModel(models.Model):
    """A disease / condition that the system can diagnose.

    Attributes:
        name: Unique disease name.
        description: Detailed clinical description.
        treatments: Recommended treatment information.
        urgency_level: Clinical urgency drawn from ``URGENCY_CHOICES``.
    """

    class UrgencyLevel(models.TextChoices):
        """Allowed urgency levels."""

        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name: str = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique disease name.",
    )
    description: str = models.TextField(
        help_text="Clinical description of the disease.",
    )
    treatments: str = models.TextField(
        help_text="Recommended treatments and interventions.",
    )
    urgency_level: str = models.CharField(
        max_length=10,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.MEDIUM,
        help_text="Clinical urgency level.",
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering: list[str] = ["-urgency_level", "name"]
        verbose_name: str = "Disease"
        verbose_name_plural: str = "Diseases"

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.name} (Urgency: {self.get_urgency_level_display()})"


class DiagnosticRuleModel(models.Model):
    """An IF-THEN diagnostic rule.

    Represents the inference: *if* a patient reports ``if_symptoms``,
    *then* infer ``then_disease`` with a given ``confidence_factor``.

    Attributes:
        name: Short rule label (e.g. "Rule-Flu-01").
        if_symptoms: Many-to-many link to required symptoms.
        then_disease: The disease this rule concludes.
        confidence_factor: Certainty percentage (0–100).
        explanation_template: Template string with ``{symptoms}`` and
            ``{disease}`` placeholders for generating human-readable
            explanations.
    """

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name: str = models.CharField(
        max_length=200,
        help_text="Short descriptive rule name.",
    )
    if_symptoms: models.ManyToManyField = models.ManyToManyField(
        SymptomModel,
        related_name="rules_containing",
        help_text="Symptoms that must be present for this rule to fire.",
    )
    then_disease: models.ForeignKey = models.ForeignKey(
        DiseaseModel,
        on_delete=models.CASCADE,
        related_name="diagnostic_rules",
        help_text="Disease concluded when this rule fires.",
    )
    confidence_factor: int = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        help_text="Rule confidence factor (0–100 %).",
    )
    explanation_template: str = models.TextField(
        help_text=(
            "Human-readable explanation template. "
            "Use {symptoms} and {disease} as placeholders."
        ),
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def clean(self) -> None:
        """Validate that the rule has at least one symptom assigned.

        Note:
            ``clean()`` is called by ``full_clean()`` and therefore by
            Django admin and model form validation.  It cannot be
            enforced at the database level for M2M fields because the
            related objects are saved *after* the owning model instance.
        """
        super().clean()
        # M2M validation can only run when the instance has a PK
        if self.pk and self.if_symptoms.count() == 0:
            raise ValidationError(
                {"if_symptoms": "A diagnostic rule must have at least one symptom."}
            )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        unique_together: list[list[str]] = [["name", "then_disease"]]
        ordering: list[str] = ["name"]
        verbose_name: str = "Diagnostic Rule"
        verbose_name_plural: str = "Diagnostic Rules"

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.name} → {self.then_disease.name} ({self.confidence_factor}%)"
