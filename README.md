# Resume Parser — Setup Guide (Windows)

## Stack
- **Frontend**: Next.js 14 (App Router) — drag & drop UI, live status, Excel download
- **Backend**: FastAPI (Python) — parser waterfall, OCR, Groq LLM extraction
- **LLM**: Groq API (`llama-3.3-70b-versatile`) — free, fast field extraction
- **OCR**: PaddleOCR (Thai + English)
- **Queue**: In-memory async queue (no Redis needed)

## Prerequisites
- Python 3.10+
- Node.js 18+
- Tesseract OCR installed (for fallback)
- Groq API key (free at https://console.groq.com)

---

## Step 1 — Install Tesseract OCR (Windows)

Download and install from:
https://github.com/UB-Mannheim/tesseract/wiki

During install, check: **Additional language data → Thai**

Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

---

## Step 2 — Backend Setup

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create your `.env` file:
```
GROQ_API_KEY=your_key_here
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Run the backend:
```powershell
uvicorn api.main:app --reload --port 8000
```

---

## Step 3 — Frontend Setup

```powershell
cd frontend
npm install
```

Create your `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the frontend:
```powershell
npm run dev
```

Open: http://localhost:3000

---

## Project Structure

```
resume-parser/
├── backend/
│   ├── api/
│   │   ├── main.py          # FastAPI app + routes
│   │   └── models.py        # Pydantic schemas
│   ├── extractors/
│   │   ├── pdf_extractor.py # pdfplumber (text-based PDF)
│   │   ├── ocr_extractor.py # PaddleOCR (scanned PDF, image)
│   │   └── field_parser.py  # Groq LLM + regex field extraction
│   ├── exporters/
│   │   └── excel_exporter.py # openpyxl Excel builder
│   ├── workers/
│   │   └── job_queue.py     # In-memory async job queue
│   ├── requirements.txt
│   └── .env
│
└── frontend/
    ├── app/
    │   ├── page.tsx          # Main upload page
    │   ├── results/page.tsx  # Results table page
    │   └── api/              # Next.js API routes (proxy)
    ├── components/
    │   ├── DropZone.tsx
    │   ├── ConfigPanel.tsx
    │   ├── JobQueue.tsx
    │   └── ResultTable.tsx
    ├── lib/
    │   └── api.ts            # API client + SSE
    ├── package.json
    └── .env.local
```
