"""
Template system for BBCode description generation.

This module provides a complete template system for generating detailed
BBCode descriptions for tracker uploads.
"""

from .renderer import TemplateRenderer, render_bbcode_description

# Try to import models, but don't fail if pydantic isn't installed
try:
    from .models import (
        TemplateData,
        Description,
        Release,
        BookInfo,  # type: ignore
        Chapter,
        Series,
        Identifiers,  # type: ignore
    )

    __all__ = [
        "TemplateRenderer",
        "render_bbcode_description",
        "TemplateData",
        "Description",
        "Release",
        "BookInfo",
        "Chapter",
        "Series",
        "Identifiers",
    ]
except ImportError:
    # Pydantic not available - provide only renderer
    __all__ = ["TemplateRenderer", "render_bbcode_description"]
