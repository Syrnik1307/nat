"""Expose Celery application for Django auto-discovery."""

from .celery import app as celery_app

__all__ = ("celery_app",)
