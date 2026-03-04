# ⚡ FlowAI – Persönlicher Workflow-Optimizer

KI-gestütztes Tool mit React (Vite) Frontend und Flask Backend.

## Voraussetzungen

- Node.js 18+
- Python 3.10+
- optional: Docker Desktop

## Lokaler Start (ohne Docker)

1) Abhängigkeiten installieren

```bash
cd backend
pip install -r requirements.txt

cd ../frontend
npm install
```

2) Umgebungsvariablen (optional, für echte KI-Antworten)

```bash
cd backend
cp .env.example .env
```

In `.env` eintragen:

```env
GROQ_API_KEY=gsk_...
```

3) Backend starten

```bash
cd backend
python app.py
```

Backend: http://localhost:5000

4) Frontend starten (zweites Terminal)

```bash
cd frontend
npm run dev
```

Frontend: http://localhost:5173

## Start mit Docker (empfohlen)

1) Optional `.env` anlegen

```bash
cd backend
cp .env.example .env
```

Optional bei Port-Konflikten in `.env`:

```env
BACKEND_PORT=5001
FRONTEND_PORT=5174
```

2) Container bauen und starten

```bash
docker compose up --build
```

Frontend: `http://localhost:<FRONTEND_PORT>` (Standard `5173`)  
Backend-API: `http://localhost:<BACKEND_PORT>` (Standard `5000`)

3) Stoppen

```bash
docker compose down
```

Wenn du die persistente SQLite-Datenbank ebenfalls löschen willst:

```bash
docker compose down -v
```

## API-Endpunkte

- `GET /api/profile`
- `POST /api/profile`
- `POST /api/recommendation`
- `GET /api/health`

## Hinweise

- Ohne `GROQ_API_KEY` läuft die App im Demo-Modus (Fallback-Empfehlungen).
- Die Datenbank wird als SQLite-Datei gespeichert (in Docker als persistentes Volume).
