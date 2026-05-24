import json
import sys
from pathlib import Path


"""
Run once to generate raw pipeline output for each document.
Review and correct the output, then save as your ground-truth annotations.

Usage:
    cd backend
    python tests/generate_anootiations.py
"""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.masking import mask_text

DOCS_DIR = Path(__file__).parent / "documents"
OUT_DIR = Path(__file__).parent / "annotations"
OUT_DIR.mkdir(exist_ok=True)

for doc_path in sorted(DOCS_DIR.glob("*.txt")):
    text = doc_path.read_text(encoding="utf-8")
    result = mask_text(text, language="de")

    annotation = {
        "document": doc_path.name,
        "entities": [
            {
                "entity_type":  e["entity_type"],
                "start":        e["start"],
                "end":          e["end"],
                "text":         e["original"],
            }
            for e in result.entities_found
        ],
    }

    out_path = OUT_DIR / doc_path.with_suffix(".json").name
    out_path.write_text(
        json.dumps(annotation, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{doc_path.name}: {len(annotation['entities'])} entities -> {out_path.name}")
    for e in annotation["entities"]:
        print(f" [{e["entity_type"]:20s}] {e['text']!r}")
    print()