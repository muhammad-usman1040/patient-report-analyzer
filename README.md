# Patient Report Analyzer

A bilingual English and Urdu web application that helps users understand supported laboratory report values in plain language. Upload a report, review extracted measurements and out-of-range values, and download a summary.

> **Medical disclaimer:** This tool is for informational purposes only. It is not a medical diagnosis. Always consult a qualified healthcare professional.

## Supported Test Panels

The current analysis engine supports these ten panels:

1. CBC (Complete Blood Count)
2. Blood Glucose (Fasting/Random) and HbA1c
3. Lipid Profile (Cholesterol)
4. LFT (Liver Function Test)
5. KFT/RFT (Kidney Function)
6. Thyroid Profile
7. Urinalysis (Urine R/E)
8. Vitamin D and B12
9. Electrolytes
10. CRP/ESR (Inflammation Markers)

Results for any other test type are not guaranteed to be accurate and may be reported as unsupported.

## Features

- Upload PDF, JPG, PNG, and TXT laboratory reports
- Extract text from images and PDFs with Tesseract OCR
- Compare values against age- and gender-aware reference ranges
- Highlight normal, high, and low measurements with accessible status icons
- Show possible conditions based on supported indicators
- Download a formatted PDF summary
- Authenticate users and view saved report history
- Switch between English and Urdu, including RTL layout support

## Technology

| Area | Technology |
| --- | --- |
| Backend | Python 3.11+, FastAPI, SQLite |
| OCR | Tesseract, pytesseract, PyMuPDF, Pillow |
| Authentication | JWT, python-jose, passlib, bcrypt |
| PDF output | ReportLab |
| Frontend | React 18, Vite, Tailwind CSS |
| Charts and localization | Recharts, i18next |

## Local Setup

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- Tesseract OCR installed and available on `PATH`

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

The API runs at `http://localhost:8000` and interactive documentation is available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The web app runs at `http://localhost:5173`. Vite proxies `/api` requests to the local backend.

### Tests

From the `backend` directory, with the virtual environment activated:

```bash
pytest -q
```

## Project Structure

```text
backend/
  main.py                 FastAPI application and API endpoints
  auth/                   Authentication routes and security helpers
  analysis/               Reference-range comparison and condition scoring
  ocr/                    OCR extraction and value parsing
  database/               SQLite schema and persistence helpers
  reports/                PDF report generation
  testing/                Edge cases, fixtures, and sample reports
frontend/
  src/
    App.jsx               Application navigation and authentication UI
    components/           Upload, result, and history views
    locales/              English and Urdu interface text
```

## Deployment Notes

For the backend, install `backend/requirements.txt` and start with:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

For the frontend, build with `npm run build` and deploy the generated `frontend/dist` directory. Configure `VITE_API_BASE_URL` or the host's reverse proxy to point API requests to the deployed backend.

Keep `JWT_SECRET_KEY` private and use a strong production value. Do not commit `.env`, local databases, virtual environments, or dependency folders.

## Limitations

- OCR quality depends on scan quality and document layout.
- Condition scoring is informational and must not be interpreted as clinical probability.
- Reference ranges are population-level values and may not apply to every person.
- The current supported scope is limited to the ten panels listed above.
- Uploads are limited to 10 MB.

## License

MIT License. See [LICENSE](LICENSE).
