# The Enabler — Technische Dokumentation

## Inhaltsverzeichnis

1. [Projektübersicht](#1-projektübersicht)
2. [Architektur](#2-architektur)
3. [Backend](#3-backend)
   - [Phase 1.1 — Dokumentenverarbeitung](#phase-11--dokumentenverarbeitung)
   - [Phase 1.2 — PII Detection & Masking](#phase-12--pii-detection--masking)
4. [Frontend](#4-frontend)
5. [Setup & Installation](#5-setup--installation)
6. [API Referenz](#6-api-referenz)
7. [Systemvoraussetzungen](#7-systemvoraussetzungen)

---

## 1. Projektübersicht

**The Enabler** ist eine lokale Web-Applikation zur automatischen Erkennung und Maskierung von personenbezogenen Daten (PII) in Dokumenten — DSGVO-konform, ohne Cloud-Anbindung.

**Unterstützte Dateiformate:** PDF, DOCX, DOC, PNG, JPG, TIFF, BMP, WEBP

**Erkannte PII-Kategorien:**

| Kategorie | Beispiel | Platzhalter |
|---|---|---|
| Person | Max Mustermann | `[PERSON]` |
| E-Mail | max@beispiel.de | `[EMAIL]` |
| Telefon | +49 170 1234567 | `[TELEFON]` |
| Ort | Berlin | `[ORT]` |
| IBAN | DE89 3704 0044 | `[IBAN]` |
| Firma | Muster GmbH | `[FIRMA]` |
| Adresse | Hauptstr. 7, 63512 Hainburg | `[ADRESSE]` |

---

## 2. Architektur

```
the-enabler/
├── backend/                  # FastAPI (Python)
│   ├── app/
│   │   ├── main.py           # API-Endpunkte
│   │   ├── converter.py      # Dokumenten → Markdown
│   │   └── masking.py        # PII-Erkennung & Maskierung
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # Next.js 15 (TypeScript)
│   ├── app/
│   │   ├── page.tsx          # Hauptseite
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── UploadZone.tsx    # Drag & Drop Upload
│   │   ├── ResultView.tsx    # Ergebnis-Anzeige + PII-Toggles
│   │   └── ExportButton.tsx  # TXT / PDF Export
│   ├── lib/
│   │   └── api.ts            # Backend-Client
│   └── Dockerfile
└── docker-compose.yml
```

**Datenfluss:**

```
User lädt Datei hoch
        │
        ▼
[Frontend] POST /upload
        │
        ▼
[Backend] converter.py
  unstructured partitioniert das Dokument
  → Einheitlicher Markdown-Text
        │
        ▼
[Backend] masking.py
  Presidio analysiert den Text
  → entities_found (start, end, typ, score)
        │
        ▼
[Backend] Response
  raw_text / preview / anonymized / entities_found
        │
        ▼
[Frontend] ResultView
  User sieht Markierungen, kann PII abwählen
  Export als TXT oder PDF
```

---

## 3. Backend

Das Backend ist eine **FastAPI**-Anwendung, die auf Port `8000` läuft.

### Phase 1.1 — Dokumentenverarbeitung

**Datei:** `backend/app/converter.py`

#### Wie es funktioniert

Jedes hochgeladene Dokument durchläuft folgende Schritte:

**Schritt 1 — Temporäre Datei**

Da `unstructured` einen Dateipfad erwartet (kein Stream), wird die hochgeladene Datei zuerst in eine temporäre Datei geschrieben:

```python
with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
    tmp.write(file.read())
```

**Schritt 2 — Partitionierung mit `unstructured`**

`unstructured.partition.auto.partition()` erkennt den Dateityp automatisch und gibt eine Liste von strukturierten Elementen zurück:

```python
elements = partition(filename=tmp_path)
```

Für **PDFs** werden Textelemente direkt extrahiert.
Für **DOCX** werden Paragraphen, Tabellen und Listen erkannt.
Für **Bilder (PNG, JPG etc.)** wird Tesseract OCR verwendet um den Text zu lesen.

**Schritt 3 — Konvertierung zu Markdown**

Jedes Element wird seinem Typ entsprechend in Markdown umgewandelt:

| Element-Typ | Markdown-Output |
|---|---|
| `Title` (Tiefe 0) | `# Überschrift` |
| `Title` (Tiefe 1) | `## Unterüberschrift` |
| `ListItem` | `- Listenpunkt` |
| `Table` | ` ```html <table>...</table>``` ` |
| `Image` | `*[Bild: Bildtext]*` |
| `PageBreak` | `---` |
| `NarrativeText` | Rohtext |

**Schritt 4 — Temp-Datei löschen**

```python
finally:
    os.unlink(tmp_path)  # wird immer gelöscht, auch bei Fehler
```

#### Unterstützte MIME-Types

```python
SUPPORTED_TYPES = {
    "application/pdf":          ".pdf",
    "application/vnd.openxmlformats...": ".docx",
    "application/msword":       ".doc",
    "image/png":                ".png",
    "image/jpeg":               ".jpg",
    "image/tiff":               ".tiff",
    "image/bmp":                ".bmp",
    "image/webp":               ".webp",
}
```

Wenn der Content-Type nicht erkannt wird, wird die Dateiendung als Fallback genutzt.

---

### Phase 1.2 — PII Detection & Masking

**Datei:** `backend/app/masking.py`

#### Verwendete Technologien

- **Microsoft Presidio** — Framework für PII-Erkennung
- **spaCy** — NLP-Modelle für Named Entity Recognition (NER)
  - `en_core_web_lg` — Englisch
  - `de_core_news_lg` — Deutsch
- **Eigene Regex-Recognizer** — für deutsche Adressen und Firmen

#### Die 5-stufige Masking-Pipeline

```
Rohtext
   │
   ▼ Schritt 1: Presidio + spaCy analysieren
   │
   ▼ Schritt 2: False Positives filtern
   │
   ▼ Schritt 3: Adressen per Regex finden
   │
   ▼ Schritt 4: PERSON-Spans trimmen + propagieren
   │
   ▼ Schritt 5: Überlappungen auflösen
   │
   ▼ preview + anonymized + entities_found
```

**Schritt 1 — Presidio Analyse**

```python
results = analyzer.analyze(text=text, entities=ENTITIES, language=language)
```

Presidio kombiniert spaCy's NER mit regelbasierten Recognizern (IBAN, E-Mail, Telefon).

**Schritt 2 — False Positive Filter (`_filter_results`)**

Presidio und spaCy erkennen manchmal Begriffe die keine PII sind. Der Filter entfernt:
- Treffer unterhalb des Mindest-Scores (z.B. PERSON < 0.7)
- Bekannte False-Positive-Wörter (z.B. `Hinweise`, `Datum`, `Prüfcode`, `Semesterzeitraum`)
- PERSON-Spans mit nur einem Wort (kein vollständiger Name)
- PERSON-Spans mit Wörtern in Großbuchstaben (Header-Text)
- LOCATION-Spans die Hex-Strings sind (z.B. `fe5b0199`)

**Schritt 3 — Adress-Erkennung per Regex (`_find_addresses_in_text`)**

Presidio hat keinen eingebauten Adress-Recognizer für Deutschland. Zwei eigene Regex-Pattern:

```
Vollständige Adresse:  Calwer Straße 7 70173 Stuttgart
                       Hauptstr. 33 63512 Hainburg

Nur PLZ + Ort:         63512 Hainburg
```

Adressen werden direkt im Rohtext gesucht — unabhängig von spaCy — weil spaCy Straßennamen oft als Teil eines Personennamens erkennt.

**Schritt 4a — PERSON-Spans trimmen (`_trim_person_spans`)**

spaCy erkennt manchmal `Rajpreet Singh Hauptstr` als einen einzigen PERSON-Span weil der Name direkt vor der Straße steht. Der Trimmer schneidet alles ab dem ersten Straßen-Keyword ab:

```
"Rajpreet Singh Hauptstr"  →  "Rajpreet Singh"
```

**Schritt 4b — Name Propagation (`_propagate_persons`)**

Wenn ein Name irgendwo im Dokument erkannt wurde, wird der gesamte Text nochmal nach diesem Namen durchsucht. So werden alle Vorkommen maskiert — auch wenn spaCy sie beim zweiten Mal nicht erkennt:

```python
for name in known_names:
    for m in re.finditer(re.escape(name), text):
        # Neuer Treffer → als PERSON hinzufügen
```

Namen aus dem Trimming (der gekürzte `Rajpreet Singh`) werden ebenfalls in die Propagation einbezogen.

**Schritt 5 — Überlappungen auflösen (`_resolve_overlaps`)**

Wenn zwei Recognizer dieselbe Textstelle erkennen, gewinnt die Entity mit der höheren Priorität:

```
ADDRESS      Priorität 5  (gewinnt fast immer)
ORGANIZATION Priorität 4
IBAN         Priorität 4
EMAIL        Priorität 4
PHONE        Priorität 4
PERSON       Priorität 3
LOCATION     Priorität 2  (verliert gegen alles)
```

#### Output

```python
@dataclass
class MaskingResult:
    preview: str         # Text mit Emoji-Markierungen (🟥`Name`🟥)
    anonymized: str      # Text mit Platzhaltern ([PERSON], [ORT], ...)
    entities_found: list[dict]  # Metadaten aller gefundenen Entities
```

`entities_found` Beispiel:
```json
{
  "entity_type": "PERSON",
  "start": 14,
  "end": 28,
  "score": 0.85,
  "original": "Maria Schmidt"
}
```

Die `start`/`end`-Indizes zeigen auf den `raw_text` — das Frontend nutzt sie um Highlights pixelgenau zu platzieren.

---

## 4. Frontend

Das Frontend ist eine **Next.js 15**-App mit **ShadCN UI** und **Tailwind CSS v4**, die auf Port `3000` läuft.

### Komponenten

#### `UploadZone.tsx`
- Drag & Drop oder Klick zum Datei-Auswählen
- Zeigt Lade-Animation während das Backend verarbeitet
- Gibt das Ergebnis per `onResult`-Callback weiter
- Unterstützte Formate: PDF, DOCX, PNG, JPG, TIFF, BMP, WEBP

#### `ResultView.tsx`
Herzstück der Anzeige. Bekommt das komplette `UploadResult` vom Backend und verwaltet:

**Entity-Badges (abwählbar)**
- Jede erkannte Entity wird als farbiger Badge angezeigt
- Klick auf Badge → deaktiviert diese Entity (durchgestrichen, ausgegraut)
- Nochmal klicken → wieder aktiviert
- Preview und KI-Text aktualisieren sich sofort (client-seitig, kein Backend-Call)

**Preview-Tab**
- Zeigt den Originaltext
- Aktive Entities werden farbig mit `<mark>` hervorgehoben
- Die Farbe entspricht dem Entity-Typ (Rot = Person, Grün = Ort, etc.)

**KI-Tab**
- Zeigt den anonymisierten Text
- Nur aktive Entities werden ersetzt
- Deaktivierte Entities bleiben im Klartext

**Wie die Highlights berechnet werden (client-seitig)**

```typescript
// Segmente von links nach rechts aufbauen
const sorted = [...activeEntities].sort((a, b) => a.start - b.start);
let cursor = 0;
for (const e of sorted) {
  // Text vor der Entity
  segments.push({ text: rawText.slice(cursor, e.start), entity: null });
  // Die Entity selbst
  segments.push({ text: rawText.slice(e.start, e.end), entity: e });
  cursor = e.end;
}
```

#### `ExportButton.tsx`
- Dropdown mit TXT und PDF
- **TXT**: Blob-Download des anonymisierten Texts
- **PDF**: jsPDF generiert eine A4-PDF mit automatischem Zeilenumbruch
- Dateiname: `[Originaldateiname]_anonymized.txt / .pdf`

#### `lib/api.ts`
Typsicherer HTTP-Client:

```typescript
export async function uploadDocument(file: File, language: "de" | "en"): Promise<UploadResult>
```

Wirft einen typisierten Fehler wenn das Backend einen Fehlercode zurückgibt.

---

## 5. Setup & Installation

### Voraussetzungen

| Tool | Version | Zweck |
|---|---|---|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| Tesseract OCR | 5.x | Bild-OCR |

### Tesseract installieren (Windows)

1. Installer herunterladen: [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Bei Installation **German** als zusätzliche Sprache auswählen
3. PATH setzen:
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\Tesseract-OCR", "Machine")
```
4. Terminal neu starten → `tesseract --version`

### Backend starten

```bash
cd backend

# Virtuelle Umgebung erstellen
python -m venv .venv
.venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# spaCy-Modelle herunterladen
python -m spacy download en_core_web_lg
python -m spacy download de_core_news_lg

# Server starten
uvicorn app.main:app --reload
# → http://localhost:8000
```

### Frontend starten

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Mit Docker (beide Services gleichzeitig)

```bash
docker-compose up --build
```

---

## 6. API Referenz

### `GET /`
Health-Check.

**Response:**
```json
{ "message": "Hello world ich schreibe was:)" }
```

---

### `POST /upload`

Nimmt ein Dokument entgegen, extrahiert den Text und maskiert PII.

**Request:**
```
Content-Type: multipart/form-data
Query-Parameter: language=de  (oder "en", default: "en")
Body: file=[Datei]
```

**Response (200):**
```json
{
  "filename": "vertrag.pdf",
  "content_type": "application/pdf",
  "raw_text": "Max Mustermann\nHauptstr. 7...",
  "preview": "🟥`Max Mustermann`🟥\n🟫`Hauptstr. 7 63512 Hainburg`🟫...",
  "anonymized": "[PERSON]\n[ADRESSE]...",
  "entities_found": [
    {
      "entity_type": "PERSON",
      "start": 0,
      "end": 14,
      "score": 0.85,
      "original": "Max Mustermann"
    },
    {
      "entity_type": "ADDRESS",
      "start": 15,
      "end": 41,
      "score": 0.85,
      "original": "Hauptstr. 7 63512 Hainburg"
    }
  ]
}
```

**Fehler:**

| Code | Bedeutung |
|---|---|
| `415` | Dateityp nicht unterstützt |
| `422` | Fehler beim Verarbeiten (z.B. Tesseract nicht installiert) |
| `500` | Fehler beim PII-Masking |

---

## 7. Systemvoraussetzungen

### Python-Pakete (Backend)

| Paket | Zweck |
|---|---|
| `fastapi` | Web-Framework |
| `uvicorn` | ASGI-Server |
| `unstructured` | Dokumenten-Partitionierung |
| `presidio-analyzer` | PII-Erkennung |
| `presidio-anonymizer` | PII-Maskierung |
| `spacy` | NLP / Named Entity Recognition |
| `python-multipart` | Datei-Upload |
| `pillow` | Bild-Verarbeitung |
| `pypdf` | PDF-Verarbeitung |
| `python-docx` | DOCX-Verarbeitung |
| `unstructured.pytesseract` | OCR-Anbindung |

### npm-Pakete (Frontend)

| Paket | Zweck |
|---|---|
| `next` | React Framework |
| `shadcn` | UI-Komponenten |
| `tailwindcss` | Styling |
| `lucide-react` | Icons |
| `jspdf` | PDF-Export |
| `radix-ui` | Zugängliche UI-Primitives |
