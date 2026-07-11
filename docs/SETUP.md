# Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## Environment Configuration

From repository root:

```bash
cp .env.example .env
```

Important variables:
- `OPENROUTER_API_KEY` (required only for AI features)
- `NEXT_PUBLIC_API_URL` (frontend API base URL)

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install fastapi "uvicorn[standard]" sgp4 numpy scipy requests apscheduler python-dotenv
uvicorn main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`

Optional frontend env file:

```bash
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > frontend/.env.local
```

## Useful Commands

Frontend:
- `npm run dev`
- `npm run build`
- `npm run lint`

Backend:
- `uvicorn main:app --reload`
