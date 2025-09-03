"""
HTML content sanitization service.

Provides HTML cleaning and text extraction using nh3 (preferred) or
BeautifulSoup4 (fallback) following the recommended packages specification.
"""

import logging
import re

logger = logging.getLogger(__name__)


class HTMLCleaner:
    """
    HTML sanitization service with multiple backend support.

    Uses nh3 (preferred) or BeautifulSoup4 (fallback) for HTML cleaning
    and text extraction following security best practices.
    """

    def __init__(self, preserve_formatting: bool = False):
        """
        Initialize HTML cleaner.

        Args:
            preserve_formatting: Whether to preserve basic formatting like line breaks
        """
        self.preserve_formatting = preserve_formatting
        self._cleaner_type = self._init_cleaner()

    def _init_cleaner(self) -> str:
        """Initialize HTML cleaner backend (nh3 preferred, bs4 fallback)."""
        import importlib.util

        if importlib.util.find_spec("nh3") is not None:
            logger.debug("Initialized nh3 HTML cleaner")
            return "nh3"
        elif importlib.util.find_spec("bs4") is not None:
            logger.debug("Initialized BeautifulSoup HTML cleaner (nh3 unavailable)")
            return "bs4"
        else:
            logger.warning("No HTML cleaner available (nh3 or bs4 required)")
            return "none"

    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content and extract plain text.

        Args:
            html_content: Raw HTML content to clean

        Returns:
            Cleaned plain text content
        """
        if not html_content or not html_content.strip():
            return ""

        if self._cleaner_type == "nh3":
            return self._clean_with_nh3(html_content)
        elif self._cleaner_type == "bs4":
            return self._clean_with_bs4(html_content)
        else:
            # Fallback to basic regex cleaning
            return self._clean_with_regex(html_content)

    def _clean_with_nh3(self, html_content: str) -> str:
        """Clean HTML using nh3 (secure and fast)."""
        try:
            import nh3

            if self.preserve_formatting:
                # Allow basic formatting tags
                allowed_tags = {"p", "br", "strong", "em", "i", "b"}
                cleaned = nh3.clean(html_content, tags=allowed_tags)
                # Convert to plain text but preserve line breaks
                cleaned = re.sub(r"<br\s*/?>", "\n", cleaned)
                cleaned = re.sub(r"<p[^>]*>", "\n", cleaned)
                cleaned = re.sub(r"</p>", "\n", cleaned)
                cleaned = re.sub(r"<[^>]+>", "", cleaned)
            else:
                # Strip all HTML for plain text
                cleaned = nh3.clean(html_content, tags=set())

            return self._normalize_whitespace(cleaned)

        except Exception as e:
            logger.warning(f"nh3 cleaning failed: {e}, falling back to regex")
            return self._clean_with_regex(html_content)

    def _clean_with_bs4(self, html_content: str) -> str:
        """Clean HTML using BeautifulSoup4."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            if self.preserve_formatting:
                # Replace certain tags with newlines
                for tag in soup.find_all(["p", "br", "div"]):
                    tag.insert_after("\n")

            # Extract text content
            cleaned = soup.get_text()
            return self._normalize_whitespace(cleaned)

        except Exception as e:
            logger.warning(f"BeautifulSoup cleaning failed: {e}, falling back to regex")
            return self._clean_with_regex(html_content)

    def _clean_with_regex(self, html_content: str) -> str:
        """Basic HTML cleaning using regex (fallback)."""
        # Remove HTML tags
        cleaned = re.sub(r"<[^>]+>", "", html_content)

        # Decode common HTML entities
        entity_map = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
            "&nbsp;": " ",
        }

        for entity, char in entity_map.items():
            cleaned = cleaned.replace(entity, char)

        return self._normalize_whitespace(cleaned)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Remove excessive whitespace while preserving intentional line breaks
        if self.preserve_formatting:
            # Preserve single line breaks, collapse multiple spaces
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n[ \t]*\n", "\n\n", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
        else:
            # Collapse all whitespace
            text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract_text_snippets(self, html_content: str, max_length: int = 500) -> str:
        """
        Extract text snippet from HTML for descriptions/summaries.

        Args:
            html_content: Raw HTML content
            max_length: Maximum length of extracted text

        Returns:
            Clean text snippet suitable for metadata
        """
        cleaned = self.clean_html(html_content)

        if len(cleaned) <= max_length:
            return cleaned

        # Truncate at word boundary
        truncated = cleaned[:max_length]
        last_space = truncated.rfind(" ")

        if last_space > max_length * 0.8:  # If we found a space reasonably close
            truncated = truncated[:last_space]

        return truncated + "..." if len(cleaned) > max_length else truncated
