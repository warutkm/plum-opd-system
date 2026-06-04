# Environment Variables

The Plum OPD Adjudication System requires the following environment variables to run locally or in production.

---

## 1. Backend Configuration (`backend/.env`)

Create a `.env` file inside the `backend/` directory:

| Variable | Description | Example |
|---|---|---|
| `GEMINI_API_KEY` | Google Generative AI API key (for text extraction and RAG) | `AIzaSy...` |
| `DATABASE_URL` | PostgreSQL connection string (Supabase recommended) | `postgresql://postgres:pass@db.supabase.co:5432/postgres` |
| `LOCAL_FALLBACK` | Set to `true` to use in-memory and local NumPy vector store fallbacks if PostgreSQL is down | `true` |

---

## 2. Frontend Configuration (`frontend/.env.local`)

Create a `.env.local` file inside the `frontend/` directory:

| Variable | Description | Example |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | The API root path of the FastAPI backend | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_WS_URL` | Websocket connection URL (if active) | `ws://localhost:8000/ws` |
