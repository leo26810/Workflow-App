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

Optional bei Port-Konflikten in der Projekt-Root `.env` (für Docker Compose-Variablen):

```env
BACKEND_PORT=5001
FRONTEND_PORT=5174
```

Hinweis: `backend/.env` ist für Backend-Variablen wie `GROQ_API_KEY`.

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
- `GET /api/telegram/status`
- `POST /api/telegram/setup-webhook`
- `POST /api/telegram/webhook/<secret>`

## Telegram Bot Integration (stabil, optional)

Der Bot kann direkt in dasselbe Empfehlungs-System schreiben wie das Haupteingabefeld im Dashboard.

1) `backend/.env` ergänzen:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_WEBHOOK_SECRET=sehr-langes-zufalls-secret
TELEGRAM_WEBHOOK_BASE_URL=https://deine-domain.tld
TELEGRAM_ALLOWED_CHAT_IDS=123456789
TELEGRAM_MODE=webhook
```

Für lokale Entwicklung ohne öffentliche HTTPS-URL kannst du stattdessen Polling nutzen:

```env
TELEGRAM_MODE=polling
```

In Polling-Modus ist `TELEGRAM_WEBHOOK_BASE_URL` nicht nötig.

2) Backend neu starten.

3) Nur im Webhook-Modus: Webhook registrieren:

```bash
curl -X POST http://localhost:5000/api/telegram/setup-webhook
```

4) In Telegram den Bot anschreiben (`/start`) und danach Aufgaben als normale Nachricht senden.

Sicherheits-/Stabilitätsdetails:
- Webhook nutzt Secret im URL-Pfad und validiert den Telegram-Secret-Header.
- Eingehende Updates werden dedupliziert (`update_id`) und über Worker-Queue verarbeitet.
- Optionaler Chat-Whitelist-Filter via `TELEGRAM_ALLOWED_CHAT_IDS`.

## Hinweise

- Ohne `GROQ_API_KEY` läuft die App im Demo-Modus (Fallback-Empfehlungen).
- Die Datenbank wird als SQLite-Datei gespeichert (in Docker als persistentes Volume).

## Wartungs-Skripte

Alle Kontroll-/Import-/Cleanup-Skripte liegen zentral im Ordner `scripts/`:

```bash
python scripts/project_status.py
python scripts/cleanup_db.py
python scripts/import_all_data.py
python scripts/import_tools.py
```

Hinweis: Die ursprünglichen Seed-JSON-Dateien wurden nach dem Import entfernt. Die Import-Skripte laufen weiterhin und überspringen fehlende Dateien sauber.

Optional kannst du eigene JSON-Quellen angeben:

```bash
python scripts/import_all_data.py --data-dir ./dein-json-ordner
python scripts/import_tools.py --json ./dein-json-ordner/tools_database.json
```
