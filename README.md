# ⚡ FlowAI – Persönlicher Workflow-Optimizer

KI-gestütztes Tool mit React (Vite) Frontend und Flask Backend.

## Projektstand

- Version: `v1.1.0` (Production-Hardening Stand `2026-03-06`)
- Enthalten: Test-Infrastruktur (pytest + Vitest + MSW), GitHub Actions CI, Coverage-Gates, Service-/Status-Fixes
- In Arbeit: schrittweise Stabilisierung und Erweiterung der neuen Testsuite

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

## Testen (lokal)

Backend:

```bash
cd backend
python -m pytest tests -v --no-cov
```

Frontend:

```bash
cd frontend
npm run test
```

Coverage:

```bash
cd backend
python -m pytest tests -v --cov=. --cov-report=term-missing --cov-report=xml

cd ../frontend
npm run test:coverage
```

Hinweis: Die Testsuite ist bereits produktiv eingebunden, wird aber weiterhin auf die vollständige Zielabdeckung hochgezogen.

## CI/CD

GitHub Actions Workflow:
- Datei: `.github/workflows/test.yml`
- Jobs: `backend-tests`, `frontend-tests`, `scripts-tests`
- Trigger: Push und Pull Requests auf `main`/`develop`
- Coverage-Gates sind aktiv (Backend und Frontend)

## API-Endpunkte

- `POST /api/recommendation`
- `GET /api/profile`
- `POST /api/profile`
- `GET /api/health`
- `GET /api/domains`
- `GET /api/categories`
- `GET /api/task-templates?subcategory=<name>`
- `GET /api/tools?page=1&limit=20`
- `GET /api/workflow-history`
- `POST /api/workflow-history`
- `GET /api/research-sessions`
- `POST /api/research-session`
- `GET /api/kpis`
- `GET /api/kpis/targets`
- `GET /api/kpis/report`
- `GET /api/kpis/scheduler-status`
- `POST /api/recommendation-feedback`
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
python scripts/data_quality_check.py
python scripts/data_quality_check.py --fix
python scripts/migrate_schema_preserve.py
python scripts/import_knowledge.py --file data/deine_datei.json
python scripts/import_knowledge.py --dir data --dry-run
python scripts/kpi_auto_report.py --days 30
python scripts/cleanup_db.py
powershell -ExecutionPolicy Bypass -File scripts/start_day.ps1
```

Hinweis: Seed-JSON-Dateien sind nach Bedarf im Ordner `data/` vorhanden.
- `chatgbt_data.json`: aktive Wissensbasis für Re-Importe.
- `test_import.json`: entfernt (war reine Test-Fixture).

Legacy-Importer wurden archiviert und sind nicht mehr der empfohlene Standardpfad:
- `scripts/archive/import_all_data.py` (deprecated)
- `scripts/archive/import_tools.py` (deprecated)
- Standard bleibt `import_knowledge.py`.

Optional kannst du eigene JSON-Quellen angeben:

```bash
python scripts/import_knowledge.py --file ./dein-json-ordner/deine_datei.json --dry-run
python scripts/import_knowledge.py --file ./dein-json-ordner/deine_datei.json
```

Empfohlener Ablauf fuer neue Wissensdaten:
1) `python scripts/import_knowledge.py --file data/<datei>.json --dry-run`
2) `python scripts/import_knowledge.py --file data/<datei>.json`
3) `python scripts/data_quality_check.py --fix`
4) `python scripts/project_status.py`
