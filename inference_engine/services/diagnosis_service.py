"""
inference_engine/services/diagnosis_service.py
==============================================
Orchestration service that ties together the inference strategy,
the knowledge base repository, and the persistence layer.

Uses the **Strategy** pattern — callers inject or swap the
inference algorithm at runtime via :meth:`set_strategy`.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_base.models import SymptomModel
from patient_cases.models import PatientCaseModel
from explanations.models import InferenceTraceModel

from .base_strategy import InferenceStrategy
from .exceptions import InferenceEngineError, InvalidSymptomError
from .knowledge_base_repository import KnowledgeBaseRepository

logger: logging.Logger = logging.getLogger(__name__)


class DiagnosisService:
    """High-level diagnostic orchestrator.

    Typical usage::

        from inference_engine.services import (
            DiagnosisService,
            ForwardChainingStrategy,
        )

        svc = DiagnosisService(strategy=ForwardChainingStrategy())
        result = svc.diagnose(symptoms=[1, 2, 3], patient_id="PT-001")
    """

    def __init__(self, strategy: InferenceStrategy) -> None:
        """Initialise with an inference strategy (dependency injection).

        Args:
            strategy: Concrete :class:`InferenceStrategy` implementation.
        """
        self._strategy: InferenceStrategy = strategy
        self._repository: KnowledgeBaseRepository = KnowledgeBaseRepository()

    def set_strategy(self, strategy: InferenceStrategy) -> None:
        """Replace the active inference strategy at runtime.

        Args:
            strategy: New :class:`InferenceStrategy` to use for
                subsequent :meth:`diagnose` calls.
        """
        logger.info(
            "switching inference strategy to %s",
            strategy.__class__.__name__,
        )
        self._strategy = strategy

    def diagnose(
        self,
        symptoms: list[int],
        patient_id: str,
        **kwargs: Any,
    ) -> dict:
        """Run a full diagnostic session: validate → infer → persist.

        Args:
            symptoms: List of symptom primary-key IDs.
            patient_id: Opaque patient / session identifier.
            **kwargs: Extra arguments forwarded to the strategy's
                :meth:`execute_inference` (e.g. ``target_disease_id``
                for backward chaining).

        Returns:
            Dict with the inference result plus a ``case_id`` key
            referencing the persisted :class:`PatientCaseModel`.

        Raises:
            InvalidSymptomError: If any symptom IDs are invalid.
            NoMatchingRuleError: If no rules match.
            InferenceEngineError: On unexpected errors.
        """
        # validate symptom ids exist in the knowledge base
        all_exist, missing = self._repository.validate_symptom_existence(symptoms)
        if not all_exist:
            raise InvalidSymptomError(missing_ids=missing)

        logger.info(
            "starting diagnosis for patient %s with %d symptoms using %s",
            patient_id,
            len(symptoms),
            self._strategy.__class__.__name__,
        )

        try:
            # execute the inference strategy
            result: dict = self._strategy.execute_inference(
                symptoms=symptoms, **kwargs
            )

            # persist the case and inference trace
            case: PatientCaseModel = self._persist_result(
                result=result,
                patient_id=patient_id,
                symptoms=symptoms,
            )

            # attach the persisted case id to the result
            result["case_id"] = case.id

            logger.info(
                "diagnosis complete for patient %s — case id %s",
                patient_id,
                case.id,
            )
            return result

        except (InvalidSymptomError, InferenceEngineError):
            raise
        except Exception as exc:
            logger.exception("unexpected error during diagnosis")
            raise InferenceEngineError(
                message="An unexpected error occurred during diagnosis.",
                details={"original_error": str(exc)},
            ) from exc

    def _persist_result(
        self,
        result: dict,
        patient_id: str,
        symptoms: list[int],
    ) -> PatientCaseModel:
        """Save the inference result to the database.

        Creates a :class:`PatientCaseModel` and a linked
        :class:`InferenceTraceModel`.

        Args:
            result: Dict returned by the inference strategy.
            patient_id: Patient / session identifier.
            symptoms: Original symptom IDs submitted.

        Returns:
            The newly created :class:`PatientCaseModel`.
        """
        # build the symptoms snapshot
        symptom_objects = SymptomModel.objects.filter(id__in=symptoms)
        symptoms_snapshot: list[dict] = [
            {"id": s.id, "name": s.name} for s in symptom_objects
        ]

        # build the inferred results payload
        inferred: list[dict] = [
            {
                "disease_id": d["disease_id"],
                "disease_name": d["disease_name"],
                "confidence": d["final_confidence"],
            }
            for d in result.get("diseases", [])
        ]

        # build the rules trace payload
        rules_trace: list[dict] = [
            {
                "rule_id": r["rule_id"],
                "explanation": r.get("explanation", ""),
            }
            for r in result.get("rules_fired", [])
        ]

        case: PatientCaseModel = PatientCaseModel.objects.create(
            patient_identifier=patient_id,
            reported_symptoms_snapshot=symptoms_snapshot,
            inferred_results=inferred,
            applied_rules_trace=rules_trace,
        )

        # create the inference trace log
        strategy_label: str = result.get("strategy", "FORWARD_CHAINING")
        confidence_map: dict = {
            d["disease_name"]: d.get("final_confidence", 0)
            for d in result.get("diseases", [])
        }

        InferenceTraceModel.objects.create(
            patient_case=case,
            strategy_used=strategy_label,
            rules_fired=result.get("rules_fired", []),
            confidence_scores_calculated=confidence_map,
            execution_time_ms=result.get("execution_time_ms", 0),
        )

        logger.info("persisted case %s with inference trace", case.id)
        return case

    def get_explanation(self, case_id: int) -> str:
        """Retrieve and format the explanation for a completed case.

        Loads the latest :class:`InferenceTraceModel` linked to the
        case, re-runs :meth:`explain_result` through the current
        strategy, and prepends case metadata.

        Args:
            case_id: Primary key of the :class:`PatientCaseModel`.

        Returns:
            Human-readable explanation string.

        Raises:
            InferenceEngineError: If the case or trace cannot be found.
        """
        try:
            case: PatientCaseModel = PatientCaseModel.objects.get(pk=case_id)
        except PatientCaseModel.DoesNotExist as exc:
            raise InferenceEngineError(
                message=f"patient case with id {case_id} not found.",
                details={"case_id": case_id},
            ) from exc

        trace: InferenceTraceModel | None = (
            case.inference_logs.order_by("-execution_timestamp").first()
        )

        if trace is None:
            raise InferenceEngineError(
                message=f"no inference trace found for case {case_id}.",
                details={"case_id": case_id},
            )

        # reconstruct a result dict from the persisted data
        reconstructed: dict = {
            "strategy": trace.strategy_used,
            "diseases": case.inferred_results,
            "rules_fired": trace.rules_fired,
            "execution_time_ms": trace.execution_time_ms,
            "total_rules_evaluated": len(trace.rules_fired),
        }

        # build header
        header: str = (
            f"patient: {case.patient_identifier}\n"
            f"session: {case.session_date:%Y-%m-%d %H:%M}\n"
            f"strategy: {trace.get_strategy_used_display()}\n"
        )

        # delegate formatting to the current strategy
        body: str = self._strategy.explain_result(reconstructed)

        return f"{header}\n{body}"
