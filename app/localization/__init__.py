"""Localization package for managing multi-language support."""

from .locales import get_text, TEXTS # Export TEXTS too for introspection

__all__ = ["get_text", "TEXTS"]



