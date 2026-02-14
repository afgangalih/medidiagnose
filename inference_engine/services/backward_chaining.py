"""
inference_engine/services/backward_chaining.py
==============================================
Goal-driven **backward chaining** inference strategy.

Algorithm:
    1. Start from a *target disease* the clinician wants to verify.
    2. Retrieve all diagnostic rules that conclude that disease.
    3. For each rule, check which of its required symptoms the patient
       has already reported.
    4. Report missing symptoms and an overall satisfaction score.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.db import DatabaseError
from django.db.models import QuerySet

from knowledge_base.models import DiagnosticRuleModel, SymptomModel

from .base_strategy import InferenceStrategy
from .exceptions import InferenceEngineError, NoMatchingRuleError
from .knowledge_base_repository import KnowledgeBaseRepository

logger: logging.Logger = logging.getLogger(__name__)


class BackwardChainingStrategy(InferenceStrategy):
    """Backward chaining: verify whether a *specific* disease is
    supported by the patient's symptoms.

    Unlike forward chaining this strategy is **goal-driven** — the
    clinician picks the hypothesis and the engine checks it.
    """

    def __init__(self) -> None:
        self.repository: KnowledgeBaseRepository = KnowledgeBaseRepository()

    def execute_inference(self, symptoms: list[int], **kwargs: Any) -> dict:
        """Verify a target disease against the patient's symptoms.

        Args:
            symptoms: List of available symptom primary-key IDs.
            **kwargs:
                target_disease_id (int): **Required.** The PK of the
                    disease to verify.

        Returns:
            Dict with structure::

                {
                    "strategy": "BACKWARD_CHAINING",
                    "target_disease_id": int,
                    "target_disease_name": str,
                    "rules_evaluated": [
                        {
                            "rule_id": int,
                            "rule_name": str,
                            "required_symptoms": [...],
                            "matched_symptoms": [...],
                            "missing_symptoms": [...],
                            "satisfaction_score": float,
                            "is_fully_satisfied": bool,
                        },
                        ...
                    ],
                    "best_satisfaction_score": float,
                    "overall_missing_symptoms": [...],
                    "rules_fired": [...],
                    "execution_time_ms": int,
                }

        Raises:
            ValueError: If ``target_disease_id`` is not provided.
            NoMatchingRuleError: If no rules exist for the target disease.
            InferenceEngineError: On database or unexpected errors.
        """
        target_disease_id: int | None = kwargs.get("target_disease_id")
        if target_disease_id is None:
            raise ValueError("target_disease_id is required for backward chaining")

        start: float = time.perf_counter()
        symptom_set: set[int] = set(symptoms)

        try:
            rules: QuerySet[DiagnosticRuleModel] = (
                self.repository.get_rules_by_disease(target_disease_id)
            )

            if not rules.exists():
                raise NoMatchingRuleError(symptom_ids=symptoms)

            # we need the disease name from the first rule
            target_disease_name: str = rules[0].then_disease.name

            evaluated: list[dict] = []
            rules_fired: list[dict] = []
            all_missing: set[int] = set()
            best_score: float = 0.0

            for rule in rules:
                required_ids: set[int] = set(
                    rule.if_symptoms.values_list("id", flat=True)
                )
                matched_ids: set[int] = symptom_set & required_ids
                missing_ids: set[int] = required_ids - symptom_set

                satisfaction: float = (
                    len(matched_ids) / len(required_ids) if required_ids else 0.0
                )

                # resolve names for readability
                matched_names: list[str] = list(
                    SymptomModel.objects
                    .filter(id__in=matched_ids)
                    .values_list("name", flat=True)
                ) if matched_ids else []

                missing_names: list[str] = list(
                    SymptomModel.objects
                    .filter(id__in=missing_ids)
                    .values_list("name", flat=True)
                ) if missing_ids else []

                required_names: list[str] = list(
                    SymptomModel.objects
                    .filter(id__in=required_ids)
                    .values_list("name", flat=True)
                )

                rule_result: dict = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "confidence_factor": rule.confidence_factor,
                    "required_symptoms": required_names,
                    "matched_symptoms": matched_names,
                    "missing_symptoms": missing_names,
                    "satisfaction_score": round(satisfaction, 4),
                    "is_fully_satisfied": len(missing_ids) == 0,
                }
                evaluated.append(rule_result)

                if satisfaction > 0:
                    rules_fired.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "satisfaction_score": round(satisfaction, 4),
                        "explanation": rule.explanation_template.format(
                            symptoms=", ".join(matched_names),
                            disease=target_disease_name,
                        ),
                    })

                all_missing.update(missing_ids)

                if satisfaction > best_score:
                    best_score = satisfaction

        except (NoMatchingRuleError, ValueError):
            raise
        except DatabaseError as exc:
            logger.exception("database error during backward chaining")
            raise InferenceEngineError(
                message="Database error during backward chaining inference.",
                details={"original_error": str(exc)},
            ) from exc

        # resolve overall missing symptom names
        overall_missing_names: list[str] = list(
            SymptomModel.objects
            .filter(id__in=all_missing)
            .values_list("name", flat=True)
        ) if all_missing else []

        elapsed_ms: int = int((time.perf_counter() - start) * 1000)

        logger.info(
            "backward chaining complete for disease %s: best score %.2f in %dms",
            target_disease_id,
            best_score,
            elapsed_ms,
        )

        return {
            "strategy": "BACKWARD_CHAINING",
            "target_disease_id": target_disease_id,
            "target_disease_name": target_disease_name,
            "rules_evaluated": evaluated,
            "best_satisfaction_score": round(best_score, 4),
            "overall_missing_symptoms": overall_missing_names,
            "rules_fired": rules_fired,
            "execution_time_ms": elapsed_ms,
        }

    def explain_result(self, result: dict) -> str:
        """Format a backward chaining result into a human-readable report.

        Args:
            result: Dict returned by :meth:`execute_inference`.

        Returns:
            Multi-line explanation string.
        """
        lines: list[str] = [
            "=== backward chaining verification report ===",
            f"target disease: {result.get('target_disease_name', 'N/A')}",
            f"best satisfaction score: {result.get('best_satisfaction_score', 0) * 100:.1f}%",
            f"execution time: {result.get('execution_time_ms', 0)}ms",
            "",
        ]

        missing = result.get("overall_missing_symptoms", [])
        if missing:
            lines.append(f"missing symptoms to investigate: {', '.join(missing)}")
        else:
            lines.append("all required symptoms are present for at least one rule")

        lines.append("")
        lines.append("--- rules evaluated ---")

        for rule in result.get("rules_evaluated", []):
            status = "SATISFIED" if rule["is_fully_satisfied"] else "PARTIAL"
            lines.append(
                f"- {rule['rule_name']} [{status}] "
                f"(score: {rule['satisfaction_score'] * 100:.1f}%)"
            )
            if rule["missing_symptoms"]:
                lines.append(
                    f"  missing: {', '.join(rule['missing_symptoms'])}"
                )

        return "\n".join(lines)
