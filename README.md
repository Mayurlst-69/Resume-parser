<div align="center">

# 📄 Resume Parser

**Batch resume extraction — PDF, JPG, PNG → Excel**

Thai & English · Drag & Drop · Real-time · Multi-provider LLM

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![Groq](https://img.shields.io/badge/Groq-Free-F55036?style=flat)](https://groq.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT4o-412991?style=flat)](https://openai.com)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-CC785C?style=flat)](https://anthropic.com)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📦 **Batch upload** | Drop หลายไฟล์พร้อมกัน ไม่จำกัดจำนวน |
| 🔍 **7 extract fields** | ชื่อ · ตำแหน่ง · เบอร์ · อีเมล · ที่อยู่ · การศึกษา · ประสบการณ์ |
| 🇹🇭 **Thai + English** | รองรับ resume ไทย อังกฤษ และแบบผสม |
| 📸 **OCR support** | PDF scan / JPG / PNG → EasyOCR + Tesseract fallback |
| 🤖 **Multi-provider AI** | Groq · OpenAI · Anthropic · Google — เลือกได้จาก UI |
| 🔑 **API key manager** | ใส่ key ได้ผ่าน UI หรือ `.env` — UI key ชนะเสมอ |
| ⚡ **Concise / General mode** | Smart section detect หรือ full text safe mode |
| 🟡 **Confidence tiers** | `confident` / `unsure` (?) / `absent` — รู้ทันทีว่าต้องตรวจ |
| 📊 **Dynamic Excel export** | Column ใน Excel ตาม field ที่ toggle — ไม่แสดง field ที่ไม่ได้เลือก |
| 🕒 **Batch history** | SQLite เก็บประวัติ re-download Excel ย้อนหลัง |
| 🔄 **Real-time SSE** | Progress แต่ละไฟล์แบบ live — ไม่ต้อง refresh |

---

## 🏗 Architecture

```
resume-parser/
├── backend/                        # FastAPI (Python 3.10+)
│   ├── api/
│   │   ├── main.py                 # Routes · SSE · History · /api/models
│   │   └── models.py               # Pydantic schemas (ParseConfig, ExtractedFields)
│   ├── extractors/
│   │   ├── pdf_extractor.py        # pdfplumber — text-based PDF
│   │   ├── ocr_extractor.py        # EasyOCR (per-lang cache) → Tesseract fallback
│   │   ├── field_parser.py         # 3-layer pipeline + multi-provider routing
│   │   └── heuristic_extractor.py  # Rule-based fallback (Thai prefix scan)
│   ├── exporters/
│   │   └── excel_exporter.py       # openpyxl — dynamic columns per config
│   └── workers/
│       ├── job_queue.py            # In-memory async queue
│       └── History_db.py          # SQLite batch history
│
└── frontend/                       # Next.js 14 (TypeScript + Tailwind)
    ├── app/
    │   ├── page.tsx                # Main page
    │   └── globals.css             # Design tokens + animations
    ├── components/
    │   ├── ConfigPanel.tsx         # Config tab + API Keys tab
    │   ├── ModelSelector.tsx       # Dropdown: provider grouping + hover tooltip
    │   ├── ApiKeySettings.tsx      # Per-provider key input + Test validation
    │   ├── DropZone.tsx            # Drag & drop
    │   ├── JobQueue.tsx            # Live processing list
    │   ├── ResultTable.tsx         # Dynamic table (columns follow toggles)
    │   └── HistoryPanel.tsx        # Batch history
    └── lib/
        ├── store.ts                # Zustand + persist (config + apiKeys)
        └── api.ts                  # uploadBatch · subscribeToStatus · validateApiKey
```

---

## 🔄 Extraction Pipeline

```
File Input (PDF / JPG / PNG)
        │
        ▼
Stage 1 — Text Extraction
  PDF text layer (pdfplumber)
  └─ if empty → OCR (EasyOCR → Tesseract fallback)
        │
        ▼
Stage 2 — clean_text()
  Remove null bytes · fix broken Thai encoding · normalize spaces
        │
        ▼
Stage 3 — Regex  [Deterministic]
  email 97% · phone 93% · Thai address pattern
        │
        ▼
Stage 4 — LLM  [AI Brain]
  Mode: Concise → contact section only (saves ~70% tokens)
        General → full text 4000 chars
  Education/Experience ON → auto full text
  Returns: value | "none" (unsure) | null (absent)
        │
        ▼
Stage 5 — Sanity Check
  Hallucination guard: company name / university / too long
        │
        ▼
Stage 6 — Heuristic Fallback
  Thai prefix scan (นาย/นาง/นางสาว)
  Keyword position detect
  Kicks in only when AI fails or unsure
        │
        ▼
Stage 7 — Merge + Confidence Score
  ExtractedFields + certainty (confident/unsure/absent) + confidence %
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) พร้อม Thai language data
- API key จากอย่างน้อย 1 provider (Groq มี free tier)

---

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/resume-parser.git
cd resume-parser
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

สร้าง `.env`:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Optional — ใส่ใน UI แทนได้
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=AIza...
```

```bash
uvicorn api.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
```

สร้าง `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
```

เปิด [http://localhost:3000](http://localhost:3000) 🎉

---

## ⚙️ Configuration

### API Keys — 2 วิธี

| วิธี | ใช้เมื่อ | Priority |
|---|---|---|
| **UI (API Keys tab)** | share ให้คนอื่นใช้ หรืออยากเปลี่ยน key แบบ real-time | สูงกว่า |
| **`.env` file** | ใช้คนเดียว / deploy server | fallback |

> UI key ชนะเสมอ — ถ้าไม่มี UI key จะ fallback ไป `.env`

### Available Models

| Provider | Model | Speed | Accuracy | Free |
|---|---|---|---|---|
| **Groq** | `llama-3.3-70b-versatile` | ⚡⚡ | ⭐⭐⭐⭐⭐ | ✅ แนะนำ |
| **Groq** | `llama-3.1-8b-instant` | ⚡⚡⚡ | ⭐⭐⭐ | ✅ quota แยก |
| **Groq** | `gemma2-9b-it` | ⚡⚡ | ⭐⭐⭐ | ✅ |
| **Groq** | `mixtral-8x7b-32768` | ⚡⚡ | ⭐⭐⭐⭐ | ✅ context ยาว |
| **OpenAI** | `gpt-4o` | ⚡⚡ | ⭐⭐⭐⭐⭐ | ❌ |
| **OpenAI** | `gpt-4o-mini` | ⚡⚡⚡ | ⭐⭐⭐⭐ | ❌ |
| **Anthropic** | `claude-sonnet-4-6` | ⚡⚡ | ⭐⭐⭐⭐⭐ | ❌ |
| **Google** | `gemini-1.5-pro` | ⚡⚡ | ⭐⭐⭐⭐ | ❌ |
| **Custom** | พิมพ์ model id เอง | — | — | — |

### Extract Mode

| Mode | วิธีทำงาน | เหมาะกับ |
|---|---|---|
| **Concise** | ส่ง contact section เท่านั้น (~200 tokens) | Resume format มาตรฐาน ✅ |
| **General** | ส่ง full text 4000 chars (~1000 tokens) | Resume format แปลก |

> ⚠️ Toggle Education / Experience ON → ใช้ full text อัตโนมัติ ไม่ขึ้นกับ mode

### Groq Free Tier Rate Limits

```
llama-3.3-70b : 100,000 TPD · 12,000 TPM
llama-3.1-8b  : 500,000 TPD · 30,000 TPM  ← สำรองสำหรับ batch ใหญ่
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Zustand (persist) |
| **Backend** | FastAPI, Python 3.10+, asyncio |
| **PDF** | pdfplumber |
| **OCR** | EasyOCR (Thai+English, per-lang cache) → Tesseract |
| **AI** | Groq · OpenAI · Anthropic · Google (configurable) |
| **DB** | SQLite (batch history) |
| **Export** | openpyxl (dynamic columns) |
| **Realtime** | Server-Sent Events (SSE) |

---

<div align="center">
Built by Mayurlst for Thai HR teams 
</div>