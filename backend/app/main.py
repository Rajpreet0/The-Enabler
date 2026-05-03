from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.converter import extract_to_markdown, SUPPORTED_TYPES
from app.masking import mask_text

from pathlib import Path

# Create a new instance of FastAPI
app = FastAPI()


# CORS Middleware from FastAPI to be able to communicate to the Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# GET HTTP request to the root path, which simply sends a message
@app.get("/")
def read_root():
    return {"message": "Hello world ich schreibe was:)"}


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    language: str = Query(
        default="en", description="Sprache für PII-Erkennung (en / de)"
    ),
):

    content_type = file.content_type or ""
    filename = file.filename or ""

    suffix = Path(filename).suffix.lower()
    supported_suffixes = set(SUPPORTED_TYPES.values())

    if content_type not in SUPPORTED_TYPES and suffix not in supported_suffixes:
        raise HTTPException(
            status_code=415,
            detail=f"Nicht unterstützter Dateityp: {content_type or suffix}. "
            f"Erlaubt: PDF, DOCX, DOC, PNG, JPG, TIFF, BMP, WEBP",
        )

    try:
        markdown = extract_to_markdown(file.file, content_type, filename)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Fehler beim Verarbeiten der Datei: {exc}"
        )

    try:
        masking = mask_text(markdown, language=language)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fehler beim PII-Masking: {exc}")

    return {
        "filename": filename,
        "content_type": content_type,
        "raw_text": markdown,
        "preview": masking.preview,
        "anonymized": masking.anonymized,
        "entities_found": masking.entities_found,
    }
