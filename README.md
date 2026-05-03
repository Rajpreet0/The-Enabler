# The Enabler

**DSGVO-konformes Tool zur automatischen Erkennung und Maskierung von personenbezogenen Daten (PII) in Dokumenten.**

Dokumente werden lokal verarbeitet — es findet keine Datenspeicherung oder externe Übertragung statt.

---

## Features

- **Dokumenten-Upload**: PDF, DOCX, DOC, PNG, JPG, TIFF, BMP, WEBP
- **Texterkennung (OCR)**: Bilder werden via Tesseract OCR in Text umgewandelt
- **PII-Erkennung** mit Microsoft Presidio + spaCy (Deutsch & Englisch):
  - Personen (Vor- + Nachname)
  - E-Mail-Adressen
  - Telefonnummern
  - Adressen (Straße + Hausnummer, PLZ + Ort)
  - IBANs
  - Organisationen (mit Rechtsform-Suffix: GmbH, AG, KG, ...)
  - Standorte / Ortsangaben
- **Preview-Ansicht**: Gefundene Entitäten werden farbig mit Emoji-Icons markiert
- **Anonymisierung**: Alle PII-Felder werden durch Labels ersetzt (`[PERSON]`, `[EMAIL]`, `[IBAN]`, ...)
- **PDF-Export**: Anonymisiertes Dokument als PDF herunterladen

---

## Architektur

```
the-enabler/
├── backend/          # FastAPI (Python)
│   └── app/
│       ├── main.py       # API-Endpunkte
│       ├── converter.py  # Dokument → Markdown (unstructured)
│       └── masking.py    # PII-Erkennung & Anonymisierung (Presidio)
└── frontend/         # Next.js (TypeScript)
    └── app/
        ├── page.tsx      # Hauptseite
        ├── components/   # UploadZone, ResultView, ...
        └── lib/api.ts    # API-Client
```

### Backend-Flow

1. Datei-Upload via `POST /upload`
2. `converter.py` extrahiert Text als Markdown (Titel, Listen, Tabellen, Bilder)
3. `masking.py` analysiert den Text mit Presidio + spaCy-Modellen
4. Rückgabe: Rohtext, Preview (mit Markierungen) und anonymisierter Text

---

## Setup

### Voraussetzungen

- Python 3.12+
- Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (für Bilddateien)

### Backend

```bash
cd backend

# Virtuelle Umgebung erstellen
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Abhängigkeiten installieren
pip install -r requirements.txt

# spaCy-Sprachmodelle herunterladen
python -m spacy download en_core_web_lg
python -m spacy download de_core_news_lg

# Server starten
uvicorn app.main:app --reload
```

Backend läuft auf: `http://localhost:8000`

### Frontend

```bash
cd frontend

npm install
npm run dev
```

Frontend läuft auf: `http://localhost:3000`

---

## API

### `POST /upload`

Lädt ein Dokument hoch und gibt PII-Analyse zurück.

**Query-Parameter:**

| Parameter  | Typ    | Standard | Beschreibung                   |
|------------|--------|----------|-------------------------------|
| `language` | string | `en`     | Sprache für PII-Erkennung (`en` oder `de`) |

**Unterstützte Dateitypen:**

| MIME-Type                                                                 | Endung  |
|---------------------------------------------------------------------------|---------|
| `application/pdf`                                                         | `.pdf`  |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` |
| `application/msword`                                                      | `.doc`  |
| `image/png`                                                               | `.png`  |
| `image/jpeg`                                                              | `.jpg`  |
| `image/tiff`                                                              | `.tiff` |
| `image/bmp`                                                               | `.bmp`  |
| `image/webp`                                                              | `.webp` |

**Response:**

```json
{
  "filename": "dokument.pdf",
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

---

## PII-Typen & Farben

| Typ            | Label        | Farbe |
|----------------|--------------|-------|
| PERSON         | `[PERSON]`   | 🟥    |
| EMAIL_ADDRESS  | `[EMAIL]`    | 🟦    |
| PHONE_NUMBER   | `[TELEFON]`  | 🟨    |
| LOCATION       | `[ORT]`      | 🟩    |
| IBAN_CODE      | `[IBAN]`     | 🟪    |
| ORGANIZATION   | `[FIRMA]`    | 🟧    |
| ADDRESS        | `[ADRESSE]`  | 🟫    |

---

## Tech Stack

### Backend
| Paket | Version | Zweck |
|-------|---------|-------|
| FastAPI | 0.136.1 | REST-API |
| uvicorn | 0.46.0 | ASGI-Server |
| presidio-analyzer | 2.2.362 | PII-Erkennung |
| presidio-anonymizer | 2.2.362 | PII-Anonymisierung |
| spaCy | 3.8.14 | NLP (en/de Modelle) |
| unstructured | 0.22.23 | Dokumenten-Parsing |
| Pillow | 12.2.0 | Bildverarbeitung |
| pypdfium2 | 5.7.1 | PDF-Rendering |
| python-docx | 1.2.0 | DOCX-Parsing |

### Frontend
| Paket | Version | Zweck |
|-------|---------|-------|
| Next.js | 16.2.4 | React-Framework |
| React | 19.2.4 | UI |
| Tailwind CSS | 4.x | Styling |
| shadcn/ui | 4.5.0 | UI-Komponenten |
| lucide-react | 1.11.0 | Icons |
| jsPDF | 4.2.1 | PDF-Export |

---

## Datenschutz

- Alle Verarbeitung erfolgt **lokal** auf dem eigenen Server
- Keine externe API-Anfragen für die Analyse
- Keine persistente Speicherung der hochgeladenen Dateien
- Konform mit DSGVO-Anforderungen für lokale Datenverarbeitung
