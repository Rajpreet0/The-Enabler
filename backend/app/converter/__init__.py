"""converter — file-to-Markdown conversion package.

Public API
----------
extract_to_markdown(file, content_type, filename) -> str
SUPPORTED_TYPES  : dict[str, str]   MIME type → file extension
SUPPORTED_SUFFIXES : frozenset[str]  valid extensions for validation

Everything else (formatters, registry) is internal.
"""

from .config import SUPPORTED_TYPES, SUPPORTED_SUFFIXES
from .extractor import extract_to_markdown

__all__ = ["extract_to_markdown", "SUPPORTED_TYPES", "SUPPORTED_SUFFIXES"]