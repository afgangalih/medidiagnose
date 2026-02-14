"""
knowledge_base/management/commands/seed_data.py
================================================
Management command to seed the database with initial test data.

Usage:
    python manage.py seed_data
"""

from django.core.management.base import BaseCommand, CommandError

from knowledge_base.models import DiagnosticRuleModel, DiseaseModel, SymptomModel


class Command(BaseCommand):
    help = "Seed the knowledge base with initial symptoms, diseases, and diagnostic rules."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Seeding Knowledge Base ===\n"))

        # ------------------------------------------------------------------
        # 1. Create Symptoms
        # ------------------------------------------------------------------
        symptoms_data = [
            {"id": 1, "name": "Fever", "category": "GENERAL", "severity_weight": 3},
            {"id": 2, "name": "Cough", "category": "RESPIRATORY", "severity_weight": 2},
            {"id": 3, "name": "Fatigue", "category": "GENERAL", "severity_weight": 1},
        ]

        created_symptoms = []
        for data in symptoms_data:
            symptom, created = SymptomModel.objects.update_or_create(
                id=data["id"],
                defaults={
                    "name": data["name"],
                    "category": data["category"],
                    "severity_weight": data["severity_weight"],
                },
            )
            status = "CREATED" if created else "UPDATED"
            self.stdout.write(f"  [{status}] Symptom: {symptom}")
            created_symptoms.append(symptom)

        # ------------------------------------------------------------------
        # 2. Create Diseases
        # ------------------------------------------------------------------
        influenza, created = DiseaseModel.objects.update_or_create(
            name="Influenza",
            defaults={
                "description": (
                    "Influenza (flu) is a contagious respiratory illness caused by "
                    "influenza viruses. It can cause mild to severe illness and, "
                    "at times, can lead to death."
                ),
                "treatments": (
                    "Rest, fluids, antiviral medications (oseltamivir/zanamivir). "
                    "Seek medical attention if symptoms are severe."
                ),
                "urgency_level": "MEDIUM",
            },
        )
        status = "CREATED" if created else "UPDATED"
        self.stdout.write(f"  [{status}] Disease: {influenza}")

        # ------------------------------------------------------------------
        # 3. Create Diagnostic Rules
        # ------------------------------------------------------------------
        flu_rule, created = DiagnosticRuleModel.objects.update_or_create(
            name="FluRule",
            then_disease=influenza,
            defaults={
                "confidence_factor": 75,
                "explanation_template": (
                    "Patient presents with {symptoms}, which are characteristic "
                    "symptoms of {disease}."
                ),
            },
        )
        # Set the M2M relation (symptoms for this rule)
        flu_rule.if_symptoms.set(created_symptoms)
        status = "CREATED" if created else "UPDATED"
        self.stdout.write(f"  [{status}] Rule: {flu_rule}")

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔ Seeding complete: "
                f"{SymptomModel.objects.count()} symptoms, "
                f"{DiseaseModel.objects.count()} diseases, "
                f"{DiagnosticRuleModel.objects.count()} rules.\n"
            )
        )
