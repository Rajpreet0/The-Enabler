"""converter — file-to-plain-text extraction package.

Public API
----------
extract_to_markdown(file, content_type, filename) -> str
SUPPORTED_TYPES  : dict[str, str]   MIME type → file extension
SUPPORTED_SUFFIXES : frozenset[str]  valid extensions for validation
"""

from .config import SUPPORTED_TYPES, SUPPORTED_SUFFIXES
from .extractor import extract_to_markdown

__all__ = ["extract_to_markdown", "SUPPORTED_TYPES", "SUPPORTED_SUFFIXES"]