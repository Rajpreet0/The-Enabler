"""converter/extractor.py — converts uploaded files to Markdown text."""

import os
import tempfile
from pathlib import Path
from typing import BinaryIO

from unstructured.partition.auto import partition

from .config import SUPPORTED_TYPES
from .formatters import element_to_markdown


def extract_to_markdown(file: BinaryIO, content_type: str, filename: str) -> str:
    """Parse a binary file into a Markdown string.

    Writes the file to a temporary path so that unstructured can infer
    the correct parser from the file extension, then converts each
    element to Markdown using the formatter registry.

    Args:
        file:         Binary file-like object (e.g. from UploadFile.file).
        content_type: MIME type of the file (e.g. "application/pdf").
        filename:     Original filename, used as a fallback for extension detection.

    Returns:
        A single Markdown string with all extracted content joined by
        blank lines.
    """
    suffix = SUPPORTED_TYPES.get(content_type)
    if suffix is None:
        # Fallback: derive extension from the original filename
        suffix = Path(filename).suffix.lower() or ".bin"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        elements = partition(filename=tmp_path)
    finally:
        os.unlink(tmp_path)

    lines = [element_to_markdown(el) for el in elements]
    return "\n\n".join(line for line in lines if line)