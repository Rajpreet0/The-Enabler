import tempfile
import os
from pathlib import Path
from typing import BinaryIO

from unstructured.partition.auto import partition
from unstructured.documents.elements import (
    Title, ListItem, Table, Image, PageBreak, Element
)

SUPPORTED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


def _element_to_markdown(el: Element) -> str:
    text = el.text.strip() if el.text else ""
    if not text:
        return ""

    if isinstance(el, Title):
        depth = getattr(el.metadata, "category_depth", 0) or 0
        hashes = "#" * (depth + 1) if depth < 5 else "######"
        return f"{hashes} {text}"

    if isinstance(el, ListItem):
        return f"- {text}"

    if isinstance(el, Table):
        # unstructured gibt Tabellen als HTML-String zurück — als Code-Block ausgeben
        html = getattr(el.metadata, "text_as_html", None)
        if html:
            return f"```html\n{html}\n```"
        return text

    if isinstance(el, Image):
        return f"*[Bild: {text}]*"

    if isinstance(el, PageBreak):
        return "\n---\n"

    return text


def extract_to_markdown(file: BinaryIO, content_type: str, filename: str) -> str:
    suffix = SUPPORTED_TYPES.get(content_type)
    if suffix is None:
        # Fallback: Endung aus Dateinamen ableiten
        suffix = Path(filename).suffix.lower() or ".bin"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        elements = partition(filename=tmp_path)
    finally:
        os.unlink(tmp_path)

    lines: list[str] = []
    for el in elements:
        md_line = _element_to_markdown(el)
        if md_line:
            lines.append(md_line)

    return "\n\n".join(lines)
