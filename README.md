# The Enabler

**A GDPR-friendly tool for automatically detecting and masking personally identifiable information (PII) in documents.**

Documents are processed entirely locally — nothing is stored persistently and nothing is sent to external services during analysis.

---

## Features

- **Document upload**: PDF, DOCX, DOC, PNG, JPG, TIFF, BMP, WEBP
- **OCR**: images are converted to text via Tesseract OCR
- **PII detection** powered by Microsoft Presidio + spaCy (German & English), covering:
  - Persons (first + last name)
  - Email addresses
  - Phone numbers
  - Addresses (street + house number, postal code + city)
  - IBANs
  - Organizations (including German legal-form suffixes: GmbH, AG, KG, …)
  - Locations
- **Preview view**: detected entities are highlighted with colored emoji markers
- **Anonymization**: every PII field can be replaced with a label (`[PERSON]`, `[EMAIL]`, `[IBAN]`, …)
- **Selective masking**: each detected entity can be toggled on/off in the UI before export, entirely client-side
- **Export**: download the anonymized document as TXT or PDF

## How it works

1. A file is uploaded via `POST /upload`.
2. The backend converts the document into Markdown text (titles, lists, tables, images — using OCR for image files).
3. The text is analyzed by a 5-step Presidio/spaCy masking pipeline (entity recognition → false-positive filtering → regex-based address detection → person-span trimming & propagation → overlap resolution).
4. The API returns the raw text, a highlighted preview, the anonymized text, and the list of detected entities (with character offsets).
5. The frontend lets you review each detected entity, deselect any you want to keep, and export the result.

## Architecture

```
the-enabler/
├── backend/                     # FastAPI (Python)
│   └── app/
│       ├── main.py               # API endpoints
│       ├── converter/            # Document → Markdown extraction (OCR, PDF/DOCX parsing)
│       └── masking/               # PII detection & anonymization pipeline (Presidio/spaCy)
├── frontend/                    # Next.js (TypeScript)
│   ├── app/                      # App Router pages
│   ├── components/               # UploadZone, ResultView, ExportButton, ...
│   ├── modules/home/              # Home view + supporting components
│   ├── hooks/                    # useAnonymizer hook
│   ├── config/                   # Entity type configuration
│   └── lib/api.ts                # Backend API client
├── docker-compose.yml
└── DOCUMENTATION.md              # Full technical documentation (German)
```

## Tech Stack

### Backend
| Package | Purpose |
|---|---|
| FastAPI | REST API |
| uvicorn | ASGI server |
| presidio-analyzer / presidio-anonymizer | PII detection & anonymization |
| spaCy (`en_core_web_lg`, `de_core_news_lg`) | NLP / named entity recognition |
| unstructured | Document parsing (PDF, DOCX, images) |
| pytesseract | OCR |
| Pillow, pypdfium2, pypdf, python-docx | File/image/PDF handling |

### Frontend
| Package | Purpose |
|---|---|
| Next.js 16 | React framework |
| React 19 | UI |
| Tailwind CSS 4 | Styling |
| shadcn/ui + radix-ui | UI components |
| lucide-react | Icons |
| jsPDF | PDF export |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (required for processing image files)

### Backend

```bash
cd backend

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Download spaCy language models
python -m spacy download en_core_web_lg
python -m spacy download de_core_news_lg

# Start the server
uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000`.

### With Docker

To run both services together:

```bash
docker-compose up --build
```

## API

### `GET /`

Health check.

### `POST /upload`

Uploads a document and returns the PII analysis.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `language` | string | `en` | Language used for PII detection (`en` or `de`) |

**Supported file types:** PDF, DOCX, DOC, PNG, JPG, TIFF, BMP, WEBP

**Response:**

```json
{
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "raw_text": "...",
  "preview": "...🟥`Max Mustermann`🟥...",
  "anonymized": "...[PERSON]...",
  "entities_found": [
    {
      "entity_type": "PERSON",
      "start": 10,
      "end": 24,
      "score": 0.85,
      "original": "Max Mustermann"
    }
  ]
}
```

**Errors:**

| Code | Meaning |
|---|---|
| `415` | Unsupported file type |
| `422` | Failed to extract text from the file (e.g. Tesseract not installed) |
| `500` | PII masking failed |

## PII Types & Colors

| Type | Label | Color |
|---|---|---|
| PERSON | `[PERSON]` | 🟥 |
| EMAIL_ADDRESS | `[EMAIL]` | 🟦 |
| PHONE_NUMBER | `[TELEFON]` | 🟨 |
| LOCATION | `[ORT]` | 🟩 |
| IBAN_CODE | `[IBAN]` | 🟪 |
| ORGANIZATION | `[FIRMA]` | 🟧 |
| ADDRESS | `[ADRESSE]` | 🟫 |

## Testing

Backend tests live in `backend/tests/`, including pipeline and step-level unit tests plus annotated sample documents (CV, employment contract, invoice) for evaluating detection accuracy. Run them with `pytest` from the `backend` directory.

## Privacy

- All processing happens **locally** on your own server
- No external API calls are made for the analysis itself
- Uploaded files are not stored persistently
- Designed to support GDPR-compliant, on-premise document handling

## Further Reading

See [`DOCUMENTATION.md`](./DOCUMENTATION.md) for the full technical documentation of the backend pipeline and frontend components (German).
