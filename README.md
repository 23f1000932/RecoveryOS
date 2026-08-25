# RecoveryOS

> AI-powered payment recovery orchestrator for Razorpay — Buildathon 2025

## Quick Start

### Backend
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
cp .env.example .env                             # fill in credentials
.venv\Scripts\uvicorn backend.main:app --reload
```
API available at `http://localhost:8000` · Docs at `http://localhost:8000/docs`

### Database
Apply `backend/db/schema.sql` via Supabase SQL Editor.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App available at `http://localhost:5173`

## Architecture
See `architecture_v2.md` · `techstack.md` · `design.md`

## Development Phases
See `implementation_plan.md` for the full 12-phase plan.
