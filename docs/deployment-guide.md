# Deployment Guide

This guide details how to deploy the Plum OPD Adjudication System to production environments.

---

## 1. Database Setup (Supabase)

1. Create a project on [Supabase](https://supabase.com/).
2. Enable the `pgvector` extension in the SQL editor:
   ```sql
   create extension if not exists vector;
   ```
3. Run the database migrations (Alembic) or create tables schema:
   ```powershell
   alembic upgrade head
   ```

---

## 2. Backend Deployment (Railway)

1. Link your GitHub repository to [Railway](https://railway.app/).
2. Add a new service pointing to the `backend/` directory.
3. Configure the start command:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Set the following environment variables:
   - `DATABASE_URL`: PostgreSQL connection string.
   - `GEMINI_API_KEY`: Google AI Generative API key.
   - `JWT_SECRET`: Random key for session management.

---

## 3. Frontend Deployment (Vercel)

1. Import your repository into [Vercel](https://vercel.com/).
2. Point the project root to `frontend/`.
3. Select the **Next.js** framework preset.
4. Set the environment variables:
   - `NEXT_PUBLIC_API_URL`: The URL of your deployed Railway backend (e.g. `https://your-backend.railway.app/api/v1`).
5. Click **Deploy**.
