from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.converter import extract_to_markdown, SUPPORTED_TYPES, SUPPORTED_SUFFIXES
from app.masking import mask_text

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_suffix(content_type: str, filename: str) -> str | None:
    """Return the file suffix if the upload is supported, else None.

    Tries the MIME type first, then falls back to the file extension.
    """
    if content_type in SUPPORTED_TYPES:
        return SUPPORTED_TYPES[content_type]
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in SUPPORTED_SUFFIXES else None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "Hello world"}


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    language: str = Query(
        default="en",
        description="Sprache für PII-Erkennung (en / de)",
    ),
):
    """Upload and anonymize a document.

    Parses the uploaded file into Markdown text and applies PII masking
    based on the selected language.

    Args:
        file:     The uploaded file (PDF, DOCX, PNG, …).
        language: Language code ('en' or 'de') for PII entity recognition.

    Raises:
        HTTPException 415: Unsupported file type or extension.
        HTTPException 422: Text extraction failed.
        HTTPException 500: PII masking failed.

    Returns:
        filename, content_type, raw Markdown text, highlighted preview,
        anonymized text, and a list of detected PII entities.
    """
    content_type = file.content_type or ""
    filename = file.filename or ""

    if _resolve_suffix(content_type, filename) is None:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Nicht unterstützter Dateityp: {content_type or filename}. "
                f"Erlaubt: PDF, DOCX, DOC, PNG, JPG, TIFF, BMP, WEBP"
            ),
        )

    try:
        markdown = extract_to_markdown(file.file, content_type, filename)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Fehler beim Verarbeiten der Datei: {exc}",
        )

    try:
        masking = mask_text(markdown, language=language)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim PII-Masking: {exc}",
        )

    return {
        "filename": filename,
        "content_type": content_type,
        "raw_text": markdown,
        "preview": masking.preview,
        "anonymized": masking.anonymized,
        "entities_found": masking.entities_found,
    }