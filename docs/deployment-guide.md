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

## 2. Backend Deployment (Render)

1. Sign in to your [Render Dashboard](https://render.com/).
2. Create a new **Web Service** and link your GitHub repository.
3. In the configuration settings:
   - **Root Directory**: Leave empty or set to `backend` depending on structure (if deploying the Dockerfile, Render will auto-detect the root `Dockerfile` or `backend/Dockerfile` if pointed correctly).
   - **Runtime**: Select `Docker`.
4. Set the following environment variables in the **Environment** tab:
   - `DATABASE_URL`: PostgreSQL connection string.
   - `GEMINI_API_KEY`: Google AI Generative API key.
   - `JWT_SECRET`: Random key for session management.
5. Click **Deploy Web Service**.
6. Set up a cron job (using Render Cron Jobs or external uptime monitoring) to keep the free tier awake if necessary.

---

## 3. Frontend Deployment (Vercel)

1. Import your repository into [Vercel](https://vercel.com/).
2. Point the project root to `frontend/`.
3. Select the **Next.js** framework preset.
4. Set the environment variables:
   - `NEXT_PUBLIC_API_URL`: The URL of your deployed Render backend (e.g., `https://your-backend.onrender.com/api/v1`).
5. Click **Deploy**.
