# Patient Report Analyzer

A free, bilingual (English / اردو) web application that lets patients upload their lab reports and receive a plain-language breakdown of flagged values and possible conditions — without requiring a doctor's appointment just to understand the numbers.

> **Disclaimer:** This tool is for informational purposes only. Results are not a medical diagnosis. Always consult a qualified healthcare professional.

---

## Features

- **Lab report upload** — accepts PDF, JPG, PNG, and TXT formats
- **Automatic OCR** — extracts values from scanned images and PDFs via Tesseract
- **Normal-range comparison** — flags out-of-range parameters with gender- and age-aware thresholds
- **Condition inference** — maps flagged parameters to a curated list of possible conditions with confidence scores
- **PDF report download** — generates a formatted PDF summary via ReportLab
- **Report history** — authenticated users can view past analyses and parameter trend charts
- **Bilingual UI** — full English and Urdu support with RTL layout for Urdu
- **Colorblind-accessible** — status badges use ↑/↓/✓ icons in addition to color

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLite |
| OCR | Tesseract (via pytesseract), pdf2image, Pillow |
| Auth | JWT (python-jose), bcrypt (passlib) |
| PDF generation | ReportLab |
| Frontend | React 18, Vite, Tailwind CSS |
| Charts | Recharts |
| i18n | i18next, react-i18next |

---

## Folder Structure

```
.
├── backend/
│   ├── main.py                    # FastAPI app, endpoints
│   ├── requirements.txt
│   ├── .env.example
│   ├── auth/
│   │   ├── auth_routes.py         # /api/auth/login, /api/auth/register
│   │   └── security.py            # JWT + password hashing
│   ├── analysis/
│   │   ├── range_comparator.py    # Normal-range flagging
│   │   ├── confidence_engine.py   # Condition inference
│   │   └── condition_indicators.json
│   ├── ocr/
│   │   ├── ocr_engine.py          # PDF/image text extraction
│   │   └── value_parser.py        # Structured value parsing
│   ├── database/
│   │   ├── db.py                  # SQLite helpers
│   │   └── schema.sql
│   ├── data/
│   │   └── normal_ranges.json     # Reference ranges
│   ├── reports/
│   │   └── pdf_generator.py       # ReportLab PDF output
│   └── testing/
│       ├── test_edge_cases.py
│       ├── accuracy_report.py
│       └── PHASE6_MODULE2_RESULTS.md
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── .env.example
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── i18n.js
        ├── index.css
        ├── components/
        │   ├── UploadPage.jsx
        │   ├── ResultsPage.jsx
        │   └── HistoryPage.jsx
        └── locales/
            ├── en.json
            └── ur.json
```

---

## How to Run Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- Tesseract OCR installed and on PATH ([installation guide](https://github.com/tesseract-ocr/tesseract))
- Poppler installed and on PATH (for PDF image conversion — [Windows](https://github.com/oschwartz10612/poppler-windows/releases), macOS: `brew install poppler`)

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. API calls are proxied to `:8000` automatically.

---

## How to Deploy

### Backend — Render / Railway

1. Push this repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com) or [Railway](https://railway.app).
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Set **Root Directory**: `backend`
6. Configure environment variables (see `backend/.env.example`):

| Variable | Description |
|---|---|
| `JWT_SECRET_KEY` | Random secret string (generate with `openssl rand -hex 32`) |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes (e.g. `60`) |

### Frontend — Vercel / Netlify

1. Create a new project pointing to this repository.
2. Set **Framework**: Vite
3. Set **Root Directory**: `frontend`
4. Set **Build Command**: `npm run build`
5. Set **Output Directory**: `dist`
6. Set environment variable:

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Your deployed backend URL (e.g. `https://your-app.onrender.com`) |

> When deploying the frontend separately from the backend, update `vite.config.js` to use `VITE_API_BASE_URL` for API calls, or configure your hosting provider's rewrite rules to proxy `/api` to the backend.

---

## Screenshots

| Upload | Results | History |
|---|---|---|
| *(add screenshot)* | *(add screenshot)* | *(add screenshot)* |

---

## Known Limitations

- **OCR accuracy** depends on scan quality. Blurry or low-contrast images will produce fewer extracted values.
- **Condition inference is not diagnostic.** The confidence scores are based on a curated but limited set of parameter-condition mappings and should not be interpreted as clinical probability.
- **Normal ranges** are population-level averages and may not apply to every individual's baseline.
- **Urdu translation** covers the UI strings; the condition names and parameter names displayed from the backend remain in English.
- **PDF upload** requires Poppler to be installed on the server. On hosted platforms, you may need to add a build step to install it.
- **File size limit** is 10 MB. Very large scanned PDFs should be compressed before upload.

---

## Contributors

Built as a personal project. Contributions welcome — open an issue or pull request.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
