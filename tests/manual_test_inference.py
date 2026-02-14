"""
tests/manual_test_inference.py
==============================
Manual smoke-test for the inference engine.

Bootstraps Django, then calls DiagnosisService with a dummy symptom list.
Run from the project root:

    python tests/manual_test_inference.py
"""

import os
import sys

# ---------------------------------------------------------------------------
# Django bootstrap
# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so Django can find the settings.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medidiagnose.settings")

import django  # noqa: E402
django.setup()

# ---------------------------------------------------------------------------
# Imports (must come AFTER django.setup())
# ---------------------------------------------------------------------------
from inference_engine.services import DiagnosisService, ForwardChainingStrategy  # noqa: E402

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("  MediDiagnose – Manual Inference Test")
    print("=" * 60)

    # 1. Create the service with forward chaining strategy
    strategy = ForwardChainingStrategy()
    service = DiagnosisService(strategy=strategy)
    print("\n✔ DiagnosisService created with ForwardChainingStrategy")

    # 2. Define dummy symptoms
    symptom_ids = [1, 2, 3]
    patient_id = "TEST-001"
    print(f"✔ Symptom IDs: {symptom_ids}")
    print(f"✔ Patient ID:  {patient_id}")

    # 3. Run the diagnosis
    print("\n--- Running diagnosis ---")
    try:
        result = service.diagnose(symptoms=symptom_ids, patient_id=patient_id)
        print("\n✔ Diagnosis succeeded!\n")

        # Pretty-print the result
        print(f"  Strategy:        {result.get('strategy')}")
        print(f"  Case ID:         {result.get('case_id')}")
        print(f"  Rules evaluated: {result.get('total_rules_evaluated')}")
        print(f"  Rules fired:     {len(result.get('rules_fired', []))}")
        print(f"  Execution time:  {result.get('execution_time_ms')}ms")

        print("\n  Ranked diseases:")
        for idx, disease in enumerate(result.get("diseases", []), start=1):
            confidence_pct = disease["final_confidence"] * 100
            print(f"    {idx}. {disease['disease_name']} — {confidence_pct:.1f}%")

        # Also test get_explanation
        print("\n--- Explanation ---")
        explanation = service.get_explanation(case_id=result["case_id"])
        print(explanation)

    except Exception as exc:
        print(f"\n✘ Diagnosis failed: {exc.__class__.__name__}: {exc}")
        if hasattr(exc, "details"):
            print(f"  Details: {exc.details}")

    print("\n" + "=" * 60)
    print("  Test complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
