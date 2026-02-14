"""
inference_engine/services/knowledge_base_repository.py
=====================================================
Repository layer providing optimised, cached access to the
knowledge base models.

All database interaction for symptoms, diseases, and diagnostic
rules is centralised here so service classes never build raw
querysets themselves.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.core.cache import cache
from django.db.models import QuerySet

from knowledge_base.models import DiagnosticRuleModel, SymptomModel

logger: logging.Logger = logging.getLogger(__name__)

# cache key and ttl for the full symptom list
_SYMPTOM_CACHE_KEY: str = "kb:all_symptoms"
_SYMPTOM_CACHE_TTL: int = 300  # 5 minutes


class KnowledgeBaseRepository:
    """Centralised, read-optimised access to the knowledge base.

    Methods use ``select_related`` / ``prefetch_related`` where
    appropriate and an optional Django cache layer for frequently
    accessed data.
    """

    def get_all_symptoms(self) -> QuerySet[SymptomModel]:
        """Return all symptoms, served from cache when available.

        Returns:
            QuerySet of all :class:`SymptomModel` instances ordered by
            the model's default ordering (category, name).
        """
        cached: QuerySet[SymptomModel] | None = cache.get(_SYMPTOM_CACHE_KEY)
        if cached is not None:
            logger.debug("serving symptoms from cache")
            return cached

        qs: QuerySet[SymptomModel] = SymptomModel.objects.all()
        cache.set(_SYMPTOM_CACHE_KEY, qs, _SYMPTOM_CACHE_TTL)
        logger.debug("symptoms loaded from db and cached for %ss", _SYMPTOM_CACHE_TTL)
        return qs

    def get_rules_by_disease(
        self, disease_id: int
    ) -> QuerySet[DiagnosticRuleModel]:
        """Return diagnostic rules for a given disease with prefetched symptoms.

        Args:
            disease_id: Primary key of the target disease.

        Returns:
            QuerySet of :class:`DiagnosticRuleModel` filtered by
            ``then_disease_id`` with ``if_symptoms`` prefetched.
        """
        return (
            DiagnosticRuleModel.objects
            .filter(then_disease_id=disease_id)
            .select_related("then_disease")
            .prefetch_related("if_symptoms")
        )

    def get_rule_by_id(self, rule_id: int) -> Optional[DiagnosticRuleModel]:
        """Return a single diagnostic rule by primary key, or ``None``.

        Args:
            rule_id: Primary key of the rule.

        Returns:
            The :class:`DiagnosticRuleModel` instance, or ``None``
            if not found.
        """
        try:
            return (
                DiagnosticRuleModel.objects
                .select_related("then_disease")
                .prefetch_related("if_symptoms")
                .get(pk=rule_id)
            )
        except DiagnosticRuleModel.DoesNotExist:
            logger.warning("rule id %s not found", rule_id)
            return None

    def validate_symptom_existence(
        self, symptom_ids: list[int]
    ) -> tuple[bool, list[int]]:
        """Check whether every supplied symptom ID exists in the database.

        Args:
            symptom_ids: List of symptom PKs to validate.

        Returns:
            Tuple of ``(all_exist, missing_ids)`` where
            ``all_exist`` is ``True`` when every ID was found and
            ``missing_ids`` lists those that were not.
        """
        existing_ids: set[int] = set(
            SymptomModel.objects
            .filter(id__in=symptom_ids)
            .values_list("id", flat=True)
        )
        missing: list[int] = [
            sid for sid in symptom_ids if sid not in existing_ids
        ]

        if missing:
            logger.warning("symptom ids not found in knowledge base: %s", missing)

        return len(missing) == 0, missing
