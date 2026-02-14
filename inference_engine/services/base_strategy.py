"""
inference_engine/services/base_strategy.py
==========================================
Abstract base class defining the contract every inference strategy
must fulfil.  Follows the **Strategy** design pattern so the
:class:`DiagnosisService` can swap algorithms at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InferenceStrategy(ABC):
    """Abstract inference strategy interface.

    Subclasses implement a concrete algorithm (e.g. forward chaining,
    backward chaining) while the :class:`DiagnosisService` interacts
    only with this interface.
    """

    @abstractmethod
    def execute_inference(self, symptoms: list[int], **kwargs: Any) -> dict:
        """Run the inference algorithm against the knowledge base.

        Args:
            symptoms: List of :class:`SymptomModel` primary-key IDs
                reported by the patient.
            **kwargs: Strategy-specific keyword arguments.  For example
                :class:`BackwardChainingStrategy` accepts
                ``target_disease_id``.

        Returns:
            A dict containing at minimum::

                {
                    "diseases": [ ... ],   # ranked results
                    "rules_fired": [ ... ],
                    "execution_time_ms": int,
                }

        Raises:
            InferenceEngineError: On any unrecoverable engine failure.
            InvalidSymptomError: If symptom IDs are invalid.
            NoMatchingRuleError: If no rules match.
        """
        ...

    @abstractmethod
    def explain_result(self, result: dict) -> str:
        """Produce a human-readable explanation of an inference result.

        Args:
            result: The dict previously returned by
                :meth:`execute_inference`.

        Returns:
            A formatted multi-line explanation string.
        """
        ...
