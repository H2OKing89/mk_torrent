"""
BBCode template rendering system with Jinja2.

This module provides a robust template rendering system for generating
BBCode descriptions with custom filters and strict validation.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TemplateRenderer:
    """BBCode template renderer with custom filters and strict validation."""

    def __init__(self, template_dir: str | Path | None = None):
        """
        Initialize the template renderer.

        Args:
            template_dir: Directory containing template files. If None, uses built-in templates.
        """
        self.template_dir = (
            Path(template_dir) if template_dir else self._get_default_template_dir()
        )

        # Create Jinja2 environment with strict settings
        self.env = Environment(  # nosec B701 # BBCode generation requires no autoescaping
            loader=FileSystemLoader(str(self.template_dir)),
            undefined=StrictUndefined,  # Fail on missing variables
            trim_blocks=True,  # Remove trailing newlines
            lstrip_blocks=True,  # Remove leading whitespace from blocks
            autoescape=False,  # Don't escape BBCode - safe for BBCode generation
        )

        # Register custom filters
        self._register_filters()

    def _get_default_template_dir(self) -> Path:
        """Get the default template directory."""
        return Path(__file__).parent / "templates"

    def _register_filters(self) -> None:
        """Register custom Jinja2 filters for BBCode formatting."""
        self.env.filters["fmt_bytes"] = self._format_bytes
        self.env.filters["fmt_duration"] = self._format_duration
        self.env.filters["yesno"] = self._yesno_filter
        self.env.filters["join_authors"] = self._join_authors
        self.env.filters["clean_html"] = self._clean_html
        self.env.filters["format_timestamp"] = self._format_timestamp
        self.env.filters["upper"] = str.upper
        self.env.filters["lower"] = str.lower
        self.env.filters["title_case"] = str.title

    @staticmethod
    def _format_bytes(bytes_value: int | float) -> str:
        """
        Format bytes into human-readable size.

        Args:
            bytes_value: Size in bytes

        Returns:
            Formatted size string (e.g., "350.19 MB")
        """
        if bytes_value < 0:
            return "0 B"

        value = float(bytes_value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} B"
                else:
                    return f"{value:.2f} {unit}"
            value = value / 1024

        return f"{value:.2f} TB"

    @staticmethod
    def _format_duration(duration_ms: int | float) -> str:
        """
        Format duration in milliseconds to human-readable format.

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            Formatted duration string (e.g., "2h 34m" or "1:23:45")
        """
        if duration_ms < 0:
            return "0:00:00"

        total_seconds = int(duration_ms // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            if seconds == 0:
                return f"{hours}h {minutes:02d}m"
            else:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @staticmethod
    def _yesno_filter(value: Any, yes: str = "Yes", no: str = "No") -> str:
        """
        Convert boolean value to yes/no string.

        Args:
            value: Value to test for truthiness
            yes: String for truthy values
            no: String for falsy values

        Returns:
            Yes or no string
        """
        return yes if value else no

    @staticmethod
    def _join_authors(
        authors: list[str], separator: str = ", ", last_separator: str = " & "
    ) -> str:
        """
        Join authors with proper grammar.

        Args:
            authors: List of author names
            separator: Separator for most authors
            last_separator: Separator before the last author

        Returns:
            Properly formatted author string
        """
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]}{last_separator}{authors[1]}"

        return f"{separator.join(authors[:-1])}{last_separator}{authors[-1]}"

    @staticmethod
    def _clean_html(text: str) -> str:
        """
        Clean HTML tags from text for BBCode output.

        Args:
            text: Text potentially containing HTML

        Returns:
            Text with HTML tags removed
        """
        if not text:
            return ""

        # Simple HTML tag removal - could be enhanced with nh3 later
        clean_text = re.sub(r"<[^>]+>", "", text)
        # Clean up multiple whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @staticmethod
    def _format_timestamp(timestamp: str) -> str:
        """
        Format timestamp for display.

        Args:
            timestamp: Timestamp string (HH:MM:SS format)

        Returns:
            Formatted timestamp
        """
        if not timestamp or not re.match(r"^\d{1,2}:\d{2}:\d{2}$", timestamp):
            return timestamp

        # Ensure HH:MM:SS format with zero-padding
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

        return timestamp

    def render_template(self, template_name: str, **context: Any) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file
            **context: Template context variables

        Returns:
            Rendered template content

        Raises:
            TemplateNotFound: If template file doesn't exist
            UndefinedError: If required template variables are missing
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_string(self, template_string: str, **context: Any) -> str:
        """
        Render a template string with the given context.

        Args:
            template_string: Template content as string
            **context: Template context variables

        Returns:
            Rendered template content
        """
        template = self.env.from_string(template_string)
        return template.render(**context)

    def render_description(
        self,
        template_data: dict[str, Any],
        desc_template: str = "bbcode_desc.jinja",
        release_template: str = "bbcode_release_desc.jinja",
    ) -> str:
        """
        Render complete BBCode description from template data.

        Args:
            template_data: Template data containing description and release info
            desc_template: Description template filename
            release_template: Release info template filename

        Returns:
            Complete rendered BBCode description
        """
        # Render description section
        description_bbcode = self.render_template(desc_template, **template_data)

        # Render release info section
        release_bbcode = self.render_template(release_template, **template_data)

        # Combine sections
        return f"{description_bbcode}\n\n{release_bbcode}"

    def list_templates(self) -> list[str]:
        """
        List available template files.

        Returns:
            List of template filenames
        """
        if not self.template_dir.exists():
            return []

        return [f.name for f in self.template_dir.glob("*.jinja")]

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template file exists.

        Args:
            template_name: Template filename to check

        Returns:
            True if template exists, False otherwise
        """
        return (self.template_dir / template_name).exists()


# Convenience function for quick rendering
def render_bbcode_description(
    template_data: dict[str, Any], template_dir: str | Path | None = None
) -> str:
    """
    Convenience function to render a complete BBCode description.

    Args:
        template_data: Template data containing description and release info
        template_dir: Optional custom template directory

    Returns:
        Rendered BBCode description
    """
    renderer = TemplateRenderer(template_dir)
    return renderer.render_description(template_data)
