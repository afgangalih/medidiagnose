"""
inference_engine/services/exceptions.py
=======================================
Custom exception hierarchy for the inference engine.

Exception Tree::

    InferenceEngineError (base)
    ├── InvalidSymptomError
    └── NoMatchingRuleError
"""

from __future__ import annotations


class InferenceEngineError(Exception):
    """Base exception for all inference engine errors.

    All domain-specific exceptions raised within the service layer
    inherit from this class so callers can catch them uniformly.

    Attributes:
        message: Human-readable error description.
        details: Optional dict with structured error context.
    """

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message: str = message
        self.details: dict = details or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class InvalidSymptomError(InferenceEngineError):
    """Raised when one or more symptom IDs do not exist in the knowledge base.

    Attributes:
        missing_ids: List of symptom IDs that could not be found.
    """

    def __init__(self, missing_ids: list[int]) -> None:
        self.missing_ids: list[int] = missing_ids
        super().__init__(
            message=f"The following symptom IDs do not exist: {missing_ids}",
            details={"missing_symptom_ids": missing_ids},
        )


class NoMatchingRuleError(InferenceEngineError):
    """Raised when no diagnostic rules match the provided symptoms.

    Attributes:
        symptom_ids: The symptom IDs that were submitted.
    """

    def __init__(self, symptom_ids: list[int]) -> None:
        self.symptom_ids: list[int] = symptom_ids
        super().__init__(
            message=(
                "No diagnostic rules matched the provided symptoms. "
                f"Symptom IDs: {symptom_ids}"
            ),
            details={"submitted_symptom_ids": symptom_ids},
        )
