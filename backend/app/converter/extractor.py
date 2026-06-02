"""converter/extractor.py — extracts plain text from uploaded files."""

import os
import tempfile
from pathlib import Path
from typing import BinaryIO

from unstructured.partition.auto import partition

from .config import SUPPORTED_TYPES


def extract_to_markdown(file: BinaryIO, content_type: str, filename: str) -> str:
    """Parse a binary file into a plain-text string.

    Each unstructured Element already exposes its content as a plain
    ``el.text`` string — no Markdown conversion is needed.  Elements are
    joined with blank lines to preserve paragraph structure for NLP.

    Args:
        file:         Binary file-like object (e.g. from UploadFile.file).
        content_type: MIME type of the file (e.g. "application/pdf").
        filename:     Original filename, used as a fallback for extension detection.

    Returns:
        A single plain-text string with all extracted content joined by
        blank lines.
    """
    suffix = SUPPORTED_TYPES.get(content_type)
    if suffix is None:
        suffix = Path(filename).suffix.lower() or ".bin"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        elements = partition(filename=tmp_path)
    finally:
        os.unlink(tmp_path)

    return "\n\n".join(el.text.strip() for el in elements if el.text and el.text.strip())