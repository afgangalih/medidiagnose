"""
api/views.py
============
DRF views for the MediDiagnose REST API.

Contains:
    - SymptomViewSet: ListAPIView with category & severity filtering.
    - DiagnosisAPIView: POST endpoint running ForwardChainingStrategy.
    - ExplanationAPIView: GET endpoint for formatted explanation traces.
"""

from __future__ import annotations

import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from inference_engine.services.diagnosis_service import DiagnosisService
from inference_engine.services.exceptions import InferenceEngineError
from inference_engine.services.forward_chaining import ForwardChainingStrategy
from knowledge_base.models import SymptomModel

from .serializers import (
    DiagnosisRequestSerializer,
    SymptomSerializer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Symptom listing
# ─────────────────────────────────────────────────────────────────────


class SymptomListAPIView(generics.ListAPIView):
    """List all symptoms with optional filtering.

    **Filters** (query params):
        - ``category``: exact match (e.g. ``?category=RESPIRATORY``)
        - ``severity_weight``: exact match (e.g. ``?severity_weight=3``)
        - ``search``: partial match on ``name``
        - ``ordering``: sort by any field (e.g. ``?ordering=-severity_weight``)
    """

    queryset = SymptomModel.objects.all()
    serializer_class = SymptomSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "severity_weight"]
    search_fields = ["name"]
    ordering_fields = ["name", "category", "severity_weight"]
    ordering = ["category", "name"]


# ─────────────────────────────────────────────────────────────────────
# Diagnosis endpoint
# ─────────────────────────────────────────────────────────────────────


class DiagnosisAPIView(APIView):
    """Run a forward-chaining diagnosis.

    **POST** ``/api/v1/diagnose/``

    Request body::

        {
            "patient_id": "PT-001",
            "symptom_ids": [1, 2, 3]
        }

    Returns the full inference result with ``case_id``.
    """

    def post(self, request):
        serializer = DiagnosisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patient_id: str = serializer.validated_data["patient_id"]
        symptom_ids: list[int] = serializer.validated_data["symptom_ids"]

        try:
            strategy = ForwardChainingStrategy()
            service = DiagnosisService(strategy=strategy)
            result = service.diagnose(
                symptoms=symptom_ids,
                patient_id=patient_id,
            )
            return Response(result, status=status.HTTP_200_OK)
        except InferenceEngineError as exc:
            logger.warning("Diagnosis failed: %s", exc.message)
            return Response(
                {"error": exc.message, "details": exc.details},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Unexpected error during API diagnosis")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─────────────────────────────────────────────────────────────────────
# Explanation endpoint
# ─────────────────────────────────────────────────────────────────────


class ExplanationAPIView(APIView):
    """Retrieve the formatted explanation trace for a case.

    **GET** ``/api/v1/explanation/<case_id>/``

    Returns a JSON object with the human-readable explanation string.
    """

    def get(self, request, case_id: int):
        try:
            strategy = ForwardChainingStrategy()
            service = DiagnosisService(strategy=strategy)
            explanation: str = service.get_explanation(case_id=case_id)
            return Response(
                {"case_id": case_id, "explanation": explanation},
                status=status.HTTP_200_OK,
            )
        except InferenceEngineError as exc:
            logger.warning("Explanation retrieval failed: %s", exc.message)
            return Response(
                {"error": exc.message, "details": exc.details},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.exception("Unexpected error retrieving explanation")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
