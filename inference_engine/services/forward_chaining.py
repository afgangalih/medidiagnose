"""
inference_engine/services/forward_chaining.py
=============================================
Data-driven **forward chaining** inference strategy.

Algorithm:
    1. Load all diagnostic rules (prefetch symptoms for performance).
    2. For each rule, compute how many of its required symptoms the
       patient has reported.
    3. Keep rules where at least one required symptom matches.
    4. Score each rule:  ``match_ratio * (confidence_factor / 100)``.
    5. Aggregate scores per disease and rank descending.
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


class ForwardChainingStrategy(InferenceStrategy):
    """Forward chaining: fire every rule whose conditions are met.

    This is the primary diagnostic strategy — it fans out from the
    reported symptoms and returns *all* diseases that could match,
    ranked by confidence.
    """

    def __init__(self) -> None:
        self.repository: KnowledgeBaseRepository = KnowledgeBaseRepository()

    def execute_inference(self, symptoms: list[int], **kwargs: Any) -> dict:
        """Run forward chaining against the knowledge base.

        Args:
            symptoms: List of symptom primary-key IDs.

        Returns:
            Dict with structure::

                {
                    "strategy": "FORWARD_CHAINING",
                    "diseases": [
                        {
                            "disease_id": int,
                            "disease_name": str,
                            "final_confidence": float,
                            "matching_rules": [ ... ],
                        },
                        ...
                    ],
                    "rules_fired": [ ... ],
                    "total_rules_evaluated": int,
                    "execution_time_ms": int,
                }

        Raises:
            NoMatchingRuleError: If no rules fire.
            InferenceEngineError: On database or unexpected errors.
        """
        start: float = time.perf_counter()
        symptom_set: set[int] = set(symptoms)

        try:
            # fetch all rules with prefetched symptom relations
            all_rules: QuerySet[DiagnosticRuleModel] = (
                DiagnosticRuleModel.objects
                .select_related("then_disease")
                .prefetch_related("if_symptoms")
                .all()
            )

            rules_fired: list[dict] = []
            # disease_id -> aggregated data
            disease_scores: dict[int, dict] = {}

            total_evaluated: int = 0

            for rule in all_rules:
                total_evaluated += 1

                # ids required by this rule
                rule_symptom_ids: set[int] = set(
                    rule.if_symptoms.values_list("id", flat=True)
                )
                matched_ids: set[int] = symptom_set & rule_symptom_ids

                if not matched_ids:
                    continue

                # scoring
                match_ratio: float = len(matched_ids) / len(rule_symptom_ids)
                final_confidence: float = match_ratio * (rule.confidence_factor / 100)

                # resolve matched symptom names for the explanation
                matched_symptom_names: list[str] = list(
                    SymptomModel.objects
                    .filter(id__in=matched_ids)
                    .values_list("name", flat=True)
                )

                rule_record: dict = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "matched_symptoms": matched_symptom_names,
                    "match_ratio": round(match_ratio, 4),
                    "confidence_factor": rule.confidence_factor,
                    "final_confidence": round(final_confidence, 4),
                    "explanation": rule.explanation_template.format(
                        symptoms=", ".join(matched_symptom_names),
                        disease=rule.then_disease.name,
                    ),
                }
                rules_fired.append(rule_record)

                # aggregate per disease (keep the highest confidence)
                d_id: int = rule.then_disease.id
                if d_id not in disease_scores:
                    disease_scores[d_id] = {
                        "disease_id": d_id,
                        "disease_name": rule.then_disease.name,
                        "final_confidence": final_confidence,
                        "matching_rules": [rule_record],
                    }
                else:
                    existing = disease_scores[d_id]
                    existing["matching_rules"].append(rule_record)
                    # take the max confidence across all rules for this disease
                    if final_confidence > existing["final_confidence"]:
                        existing["final_confidence"] = final_confidence

        except DatabaseError as exc:
            logger.exception("database error during forward chaining")
            raise InferenceEngineError(
                message="Database error during forward chaining inference.",
                details={"original_error": str(exc)},
            ) from exc

        if not rules_fired:
            logger.warning("no rules fired for symptoms %s", symptoms)
            raise NoMatchingRuleError(symptom_ids=symptoms)

        # rank diseases by confidence descending
        ranked_diseases: list[dict] = sorted(
            disease_scores.values(),
            key=lambda d: d["final_confidence"],
            reverse=True,
        )

        # round the top-level confidence for readability
        for disease in ranked_diseases:
            disease["final_confidence"] = round(disease["final_confidence"], 4)

        elapsed_ms: int = int((time.perf_counter() - start) * 1000)

        logger.info(
            "forward chaining complete: %d rules evaluated, %d fired in %dms",
            total_evaluated,
            len(rules_fired),
            elapsed_ms,
        )

        return {
            "strategy": "FORWARD_CHAINING",
            "diseases": ranked_diseases,
            "rules_fired": rules_fired,
            "total_rules_evaluated": total_evaluated,
            "execution_time_ms": elapsed_ms,
        }

    def explain_result(self, result: dict) -> str:
        """Format a forward chaining result into a human-readable report.

        Args:
            result: Dict returned by :meth:`execute_inference`.

        Returns:
            Multi-line explanation string.
        """
        lines: list[str] = [
            "=== forward chaining diagnosis report ===",
            f"strategy: {result.get('strategy', 'N/A')}",
            f"total rules evaluated: {result.get('total_rules_evaluated', 0)}",
            f"rules fired: {len(result.get('rules_fired', []))}",
            f"execution time: {result.get('execution_time_ms', 0)}ms",
            "",
            "--- ranked diseases ---",
        ]

        for idx, disease in enumerate(result.get("diseases", []), start=1):
            confidence_pct: float = disease["final_confidence"] * 100
            lines.append(
                f"{idx}. {disease['disease_name']} "
                f"(confidence: {confidence_pct:.1f}%)"
            )
            for rule in disease.get("matching_rules", []):
                lines.append(f"   - rule: {rule['rule_name']}")
                lines.append(f"     matched symptoms: {', '.join(rule['matched_symptoms'])}")
                lines.append(f"     explanation: {rule['explanation']}")

        return "\n".join(lines)
