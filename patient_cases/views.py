"""
patient_cases/views.py
======================
Traditional Django views for the patient case module.

Contains:
    - SymptomCheckerFormView: Symptom checker form → diagnosis.
    - DiagnosisResultDetailView: Display a single diagnosis case result.
    - CaseHistoryListView: Paginated list of all past cases.
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView

from inference_engine.services.diagnosis_service import DiagnosisService
from inference_engine.services.exceptions import InferenceEngineError
from inference_engine.services.forward_chaining import ForwardChainingStrategy
from knowledge_base.models import SymptomModel
from explanations.models import InferenceTraceModel

from .forms import SymptomCheckForm
from .models import PatientCaseModel

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Symptom Checker
# ─────────────────────────────────────────────────────────────────────


class SymptomCheckerFormView(FormView):
    """Display the symptom checker form and run diagnosis on submission.

    On valid POST, calls :class:`DiagnosisService` with
    :class:`ForwardChainingStrategy` and redirects to the result page.
    """

    template_name = "patient_cases/symptom_checker.html"
    form_class = SymptomCheckForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Group symptoms by category for the template grid
        symptoms_by_category = {}
        for symptom in SymptomModel.objects.all():
            cat = symptom.get_category_display()
            if cat not in symptoms_by_category:
                symptoms_by_category[cat] = []
            symptoms_by_category[cat].append(symptom)
        context["symptoms_by_category"] = symptoms_by_category
        return context

    def form_valid(self, form):
        symptoms = form.cleaned_data["symptoms"]
        patient_id = form.cleaned_data["patient_id"]
        symptom_ids = list(symptoms.values_list("id", flat=True))

        try:
            strategy = ForwardChainingStrategy()
            service = DiagnosisService(strategy=strategy)
            result = service.diagnose(
                symptoms=symptom_ids,
                patient_id=patient_id,
            )
            case_id = result.get("case_id")
            messages.success(
                self.request,
                "Diagnosis completed successfully!",
            )
            return redirect(
                reverse("patient_cases:diagnosis-result", kwargs={"pk": case_id})
            )
        except InferenceEngineError as exc:
            messages.error(self.request, f"Diagnosis failed: {exc.message}")
            return self.form_invalid(form)
        except Exception as exc:
            logger.exception("Unexpected error in symptom checker")
            messages.error(
                self.request,
                "An unexpected error occurred. Please try again.",
            )
            return self.form_invalid(form)


# ─────────────────────────────────────────────────────────────────────
# Diagnosis Result Detail
# ─────────────────────────────────────────────────────────────────────


class DiagnosisResultDetailView(DetailView):
    """Display the full result of a diagnostic session.

    Shows confidence bars, urgency badges, and the explanation trace.
    """

    model = PatientCaseModel
    template_name = "patient_cases/diagnosis_result.html"
    context_object_name = "case"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        case = self.object

        # Fetch the inference trace for this case
        trace = case.inference_logs.order_by("-execution_timestamp").first()
        context["trace"] = trace

        # Build explanation using the service
        try:
            strategy = ForwardChainingStrategy()
            service = DiagnosisService(strategy=strategy)
            explanation = service.get_explanation(case_id=case.pk)
            context["explanation"] = explanation
        except InferenceEngineError:
            context["explanation"] = "Explanation not available."

        # Enrich inferred results with urgency info from DiseaseModel
        from knowledge_base.models import DiseaseModel

        enriched_results = []
        for result in case.inferred_results:
            disease_id = result.get("disease_id")
            try:
                disease = DiseaseModel.objects.get(pk=disease_id)
                enriched = {
                    **result,
                    "urgency_level": disease.urgency_level,
                    "urgency_display": disease.get_urgency_level_display(),
                    "treatments": disease.treatments,
                    "description": disease.description,
                }
            except DiseaseModel.DoesNotExist:
                enriched = {
                    **result,
                    "urgency_level": "MEDIUM",
                    "urgency_display": "Unknown",
                    "treatments": "N/A",
                    "description": "N/A",
                }
            enriched_results.append(enriched)
        context["enriched_results"] = enriched_results

        return context


# ─────────────────────────────────────────────────────────────────────
# Case History
# ─────────────────────────────────────────────────────────────────────


class CaseHistoryListView(ListView):
    """Paginated list of all past diagnostic sessions.

    Supports date filtering via GET params ``date_from`` and ``date_to``.
    """

    model = PatientCaseModel
    template_name = "patient_cases/case_history.html"
    context_object_name = "cases"
    paginate_by = 15
    ordering = ["-session_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")
        if date_from:
            qs = qs.filter(session_date__date__gte=date_from)
        if date_to:
            qs = qs.filter(session_date__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")
        return context
