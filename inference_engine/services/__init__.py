"""
inference_engine/services/__init__.py
=====================================
Service layer for the MediDiagnose inference engine.

Exports:
    - InferenceStrategy: Abstract base class for inference strategies.
    - ForwardChainingStrategy: Data-driven forward chaining implementation.
    - BackwardChainingStrategy: Goal-driven backward chaining implementation.
    - DiagnosisService: Orchestration service with strategy pattern.
    - KnowledgeBaseRepository: Optimised repository for knowledge base queries.
    - InvalidSymptomError, NoMatchingRuleError, InferenceEngineError: Custom exceptions.
"""

from .base_strategy import InferenceStrategy
from .backward_chaining import BackwardChainingStrategy
from .diagnosis_service import DiagnosisService
from .exceptions import (
    InferenceEngineError,
    InvalidSymptomError,
    NoMatchingRuleError,
)
from .forward_chaining import ForwardChainingStrategy
from .knowledge_base_repository import KnowledgeBaseRepository

__all__: list[str] = [
    "InferenceStrategy",
    "ForwardChainingStrategy",
    "BackwardChainingStrategy",
    "DiagnosisService",
    "KnowledgeBaseRepository",
    "InferenceEngineError",
    "InvalidSymptomError",
    "NoMatchingRuleError",
]
