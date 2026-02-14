"""
api/apps.py
===========
Django app configuration for the REST API module.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Configuration for the ``api`` application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "REST API"
