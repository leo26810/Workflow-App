# PROJEKT-DOKUMENTATION (Aktueller Stand)

## 1) Überblick

**FlowAI** ist ein Fullstack-Assistent zur KI-gestützten Aufgabenplanung und Tool-Empfehlung.

Ziele:
- Freitext-Aufgaben entgegennehmen.
- Nutzerprofil, Verlauf und User-Context in die Empfehlung einbeziehen.
- Konkrete Ausgabe liefern: Workflow, empfohlene Tools, optimierter Prompt, Tips, naechster Schritt.
- Empfehlungen und Feedback persistieren und fuer KPI/Ranking wiederverwenden.

Technik-Stack:
- Frontend: React 18 + Vite 5 + React Router 6.
- Backend: Flask 3 + SQLAlchemy + SQLite.
- Betrieb: Docker Compose (`workflow-backend`, `workflow-frontend`).


## 2) Architektur

### 2.1 Backend-Schichten

- `backend/app.py`
  - Entrypoint, Startlogik, Health-Payload, `db.create_all()`, Seeding-Thread, Worker/Scheduler Start.
- `backend/app_factory.py`
  - App-Factory (`create_app()`), CORS/Compress/DB-Konfiguration, Blueprint-Registrierung.
- `backend/extensions.py`
  - Zentrale Singletons fuer `db`, `cors`, `compress`.
- `backend/routes/`
  - Endpoint-Definitionen je Domäne.
- `backend/services/`
  - Fachlogik (Profile, Recommendations, Telegram, KPI, History, Research, Cache, Seed).
- `backend/models.py`
  - SQLAlchemy-Modelle und `to_dict()`-Serialisierung.

### 2.2 Frontend-Schichten

- `frontend/src/App.jsx`
  - Layout + Sidebar-Navigation + Route-Mapping.
- `frontend/src/pages/`
  - `Dashboard.jsx`, `HistoryPage.jsx`, `ConfigPage.jsx`, `ProfilePage.jsx`.
- `frontend/vite.config.js`
  - Dev-Proxy `/api -> http://backend:5000`.


## 3) Aktuelle Repository-Struktur

```text
.
├─ backend/
│  ├─ app.py
│  ├─ app_factory.py
│  ├─ extensions.py
│  ├─ models.py
│  ├─ requirements.txt
│  ├─ .env.example
│  ├─ routes/
│  │  ├─ domains.py
│  │  ├─ system.py
│  │  ├─ profile.py
│  │  ├─ tools.py
│  │  ├─ recommendations.py
│  │  ├─ history.py
│  │  ├─ kpis.py
│  │  ├─ research.py
│  │  └─ telegram.py
│  ├─ services/
│  │  ├─ recommendation_service.py
│  │  ├─ groq_service.py
│  │  ├─ profile_service.py
│  │  ├─ tools_service.py
│  │  ├─ history_service.py
│  │  ├─ kpi_service.py
│  │  ├─ telegram_service.py
│  │  ├─ research_service.py
│  │  ├─ data_cache_service.py
│  │  ├─ feedback_service.py
│  │  └─ seed_service.py
│  ├─ utils/
│  │  └─ cache_utils.py
│  └─ instance/
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.js
│  └─ src/
│     ├─ App.jsx
│     ├─ main.jsx
│     ├─ index.css
│     └─ pages/
│        ├─ Dashboard.jsx
│        ├─ HistoryPage.jsx
│        ├─ ConfigPage.jsx
│        └─ ProfilePage.jsx
├─ scripts/
│  ├─ project_status.py
│  ├─ data_quality_check.py
│  ├─ migrate_schema_preserve.py
│  ├─ import_knowledge.py
│  ├─ cleanup_db.py
│  └─ archive/
│     ├─ import_all_data.py
│     └─ import_tools.py
├─ data/
│  ├─ .gitkeep
│  └─ chatgbt_data.json
├─ docker-compose.yml
├─ Dockerfile.backend
├─ Dockerfile.frontend
└─ PROJEKT_DOKUMENTATION.md
```


## 4) Frontend (Ist-Zustand)

Routen (`frontend/src/App.jsx`):
- `/` und `/dashboard` -> Dashboard
- `/history` -> Verlauf
- `/config` -> Konfiguration / KPI / Systemstatus
- `/profile` -> Profil

Hinweise:
- Die Navigation zeigt einen KI-Statusindikator basierend auf `/api/health` (`groq_configured`).
- Es gibt aktuell keine separate Frontend-Seite mehr fuer `ResearchPage`.
- Research-Daten sind im Backend weiterhin als API vorhanden.
- Dashboard zeigt Wissensmetriken (Domain-/Kategorie-/Tool-Anzahl, Tag-Abdeckung).
- Tool-Karten in Dashboard und Profil zeigen strukturierte Wissensfelder: `domain`, `tags`, `use_case`, `platform`, `pricing_model`, `skill_requirement`.


## 5) Backend-Endpunkte

### 5.1 System

- `GET /api/health`
  - Liefert u. a.:
    - `status`
    - `groq_configured`
    - `telegram_configured`
    - `feedback_records`
    - KPI Scheduler-Statusfelder

### 5.2 Profil / Kontext / Stammdaten

- `GET /api/profile?page=1&limit=20`
- `POST /api/profile`
  - `action`:
    - `add_skill`, `delete_skill`
    - `add_goal`, `delete_goal`
    - `update_name`
    - `add_tool`, `delete_tool`
- `GET /api/skills`
- `GET /api/goals`
- `GET /api/user-context`
- `POST /api/user-context`
  - Pflicht: `area`, `key`; optional: `value`

### 5.3 Taxonomie / Tools

- `GET /api/domains`
  - Domains inkl. zugeordneter Kategorien.
- `GET /api/categories`
  - Kategorien inkl. Unterkategorien und Task-Templates.
- `GET /api/task-templates?subcategory=<name>`
  - 400 bei fehlendem Query-Parameter.
  - 404 bei unbekannter Subcategory.
- `GET /api/tools?page=1&limit=20`
  - Antwortformat: `{ items, total, page, limit, pages }`

### 5.4 Recommendations / Feedback / History

- `POST /api/recommendation`
  - Input: `{ "task_description": "..." }`
  - Output enthaelt u. a.:
    - `recommendation` (workflow, recommended_tools, optimized_prompt, tips, difficulty, ...)
    - `mode` (`ai` oder `demo`)
    - `model_used`
    - `history_id`
    - `area`, `subcategory`
    - `personalization_note`, `next_step`
    - `ai_diagnostics`, `ai_attempts`, `fallback_variant`
- `GET /api/recommendation-feedback`
  - Paginierung + Filter (`search`, `min_rating`).
- `POST /api/recommendation-feedback`
  - Speichert/aktualisiert qualifiziertes Feedback zur Empfehlung.
- `GET /api/workflow-history`
  - Letzte 20 History-Eintraege.
- `POST /api/workflow-history`
  - Setzt Rating fuer History-Eintrag.
- `GET /api/workflow-history/<history_id>`

### 5.5 KPI

- `GET /api/kpis?days=30`
- `GET /api/kpis/targets`
- `GET /api/kpis/report?days=30`
- `GET /api/kpis/scheduler-status`

### 5.6 Telegram

- `GET /api/telegram/status`
- `POST /api/telegram/setup-webhook`
- `POST /api/telegram/webhook/<secret>`

### 5.7 Research

- `POST /api/research-session`
- `GET /api/research-sessions`


## 6) Recommendation-Pipeline

Kernservice: `backend/services/recommendation_service.py`

Pipeline (aktueller Stand):
1. Aufgabe klassifizieren (task_type, area, subcategory, confidence)
2. Personalisierungsdaten laden: Skills, Goals, UserContext, History, Tool-Scores
2b. 3-Stufen-Filter:
  Stufe 1 (SQL): detect_domains() erkennt relevante Domains,
  SQL-Query filtert Tools auf diese Domains
  → von N Tools auf ~50-200 relevante Tools
  Stufe 2 (Tags): Tag-Overlap-Filter reduziert weiter
  → ~15-50 Tools für Scoring
  Stufe 3 (Scoring): score_tool_relevance() auf gefilterten Tools
  → Top 5 Ergebnis
  Skaliert auf 10.000+ Tools ohne Performanceverlust.
3. DB-Engine: score_tool_relevance() bewertet die vorgefilterten Tools (0-100) nach Need-Match, Skill-Fit, Kategorie und Inhalt -> Top 5 Tools
4. Kontext-Zusammenfassung: summarize_user_context() verdichtet Profil auf max 3 Sätze (~400 Zeichen)
5. Micro-Prompt: build_micro_prompt() baut gezielten Prompt (~500 Tokens) mit Top-5-Tools + Zusammenfassung + Task-Profil + erkannten Domänen
6. KI-Aufruf: call_groq_with_micro_prompt() sendet Micro-Prompt an Groq (max 600 Token Antwort), KI verifiziert Tools und generiert Workflow/Prompt
7. Merge: KI-Output wird mit DB-Metadaten (URLs, Scores) zusammengeführt
8. Bei Fehlern: lokaler regelbasierter Fallback, final generischer Fallback
9. Normalisierung, Speicherung in workflow_history, Response zurückgeben

Caching: unverändert (TTL/LRU für Profil/Tools, Dedup 60s)


## 7) KPI- und Telegram-Runtime

### 7.1 KPI-Service

`backend/services/kpi_service.py`:
- Berechnet KPI-Snapshot aus `workflow_history` und `recommendation_feedback`.
- Auto-Report-Scheduler schreibt JSON-Reports nach `logs/kpi_report_*.json`.
- Zielwerte (`KPI_TARGETS`) sind im Service definiert.

### 7.2 Telegram-Service

`backend/services/telegram_service.py`:
- Modi: `webhook` oder `polling`.
- Queue-basierte Verarbeitung mit Worker-Thread.
- Deduplizierung via `update_id` mit TTL-Fenster.
- Antwort basiert auf derselben Recommendation-Pipeline wie das Dashboard.


## 8) Datenmodell (Kurzuebersicht)

Wesentliche Tabellen in `backend/models.py`:
- `domain` (`id`, `name`, `icon`, `description`, `tags`, `sort_order`)
- `users`, `skills`, `goals`, `tools`
- `workflow_history`, `recommendation_feedback`
- `workflow_categories`, `sub_categories`, `task_templates`
- `user_context`
- `research_sessions`
- zusaetzlich: `tool_usage_logs`, `prompt_templates`, `user_preferences`, `skill_progress`

Erweiterte Tool-Felder:
- `domain`, `tags`, `use_case`, `platform`, `pricing_model`

Wichtige Beziehungen:
- `Domain` 1:n `WorkflowCategory`
- `WorkflowCategory` 1:n `SubCategory`
- `SubCategory` 1:n `TaskTemplate`
- `Tool` 1:n `ToolUsageLog`
- `Skill` 1:n `SkillProgress`


## 9) Umgebungsvariablen

Beispiel: `backend/.env.example`

Pflicht/fachlich relevant:
- `GROQ_API_KEY`

Telegram (optional):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_WEBHOOK_BASE_URL`
- `TELEGRAM_ALLOWED_CHAT_IDS`
- `TELEGRAM_MODE` (`webhook` oder `polling`)

KPI (optional):
- `KPI_AUTOREPORT_ENABLED`
- `KPI_AUTOREPORT_INTERVAL_MINUTES`
- `KPI_REPORT_WINDOW_DAYS`

Weitere Runtime-Parameter (Compose/Backend):
- `CORS_ORIGINS`
- `PORT`
- `FLASK_DEBUG`
- optional `DATABASE_URL`


## 10) Docker und Start

`docker-compose.yml` startet zwei Services:
- `backend` (Containername `workflow-backend`)
- `frontend` (Containername `workflow-frontend`)

Ports:
- Backend: `5000:5000`
- Frontend: `5173:5173`

Persistenz:
- SQLite-Datei wird ueber `./backend/instance:/workspace/backend/instance` gemountet.

Start:
```bash
docker compose up --build
```


## 11) Wartungsskripte

Im Ordner `scripts/`:
- `project_status.py`
  - Struktur-, DB-, Endpoint- und Konfigchecks.
  - Prueft zusaetzlich Wissensabdeckung (Domain-/Tag-/Use-Case-/Pricing-/Skill-Coverage), Knowledge-UI und neue Wartungsskripte.
  - Schreibt Reportdateien nach `logs/status_*.txt`.
- `data_quality_check.py`
  - Vollstaendiger Datenqualitaetscheck fuer `domain`, `workflow_categories`, `sub_categories`, `task_templates`, `tools`.
  - Optionaler Auto-Fix (`--fix`) fuellt fehlende Felder und normalisiert kompatible Werte.
- `migrate_schema_preserve.py`
  - Nicht-destruktive SQLite-Migration (additive Schema-Updates, Daten bleiben erhalten).
- `cleanup_db.py`
  - Bereinigung von Tool-Textfeldern.
  - Hilft beim Entfernen fehlerhafter oder leerer Tool-Felder vor Re-Importen.
- `import_knowledge.py`
  - Neu: Haupt-Import fuer Wissensdaten (Domains, Kategorien, Tools) aus JSON-Dateien generiert durch ChatGPT/Perplexity/Gemini.
  - Upsert-Logik verhindert Duplikate.
  - Aufruf: `python scripts/import_knowledge.py --file <datei.json>`
  - Ordner-Import: `python scripts/import_knowledge.py --dir data`
- `scripts/archive/import_all_data.py`
  - Deprecated Legacy-Skript, nur fuer historische Batch-Importe.
- `scripts/archive/import_tools.py`
  - Deprecated Legacy-Skript, ersetzt durch `import_knowledge.py`.


## 12) Bekannte Grenzen

- Single-User-Modell (keine Auth, kein Mandantenkonzept).
- SQLite als lokale Persistenz; Tool-Wissensbasis ist konzeptionell skalierbar auf 10.000+ Tools.
- Viele Konfigurations- und Betriebsannahmen sind auf lokalen/dev-nahen Betrieb ausgelegt.
- recommendation_service.py ist der komplexeste Service (~900 Zeilen) und enthält Klassifikations-, Scoring-, Prompt- und Merge-Logik in einer Datei. Bei weiterer Erweiterung empfiehlt sich eine Aufteilung in classification_service.py und scoring_service.py.


## 13) Kurzfazit

Die Webapp ist aktuell konsistent auf eine vierseitige Navigation ausgelegt (`Dashboard`, `Verlauf`, `Config`, `Mein Profil`) und nutzt eine modularisierte Backend-Architektur mit klarer Trennung von Routes und Services. Recommendation-, KPI- und Telegram-Logik sind entkoppelt, das Micro-Prompt-System mit Tool-Blacklist ist produktiv integriert, und robuste Fallbacks greifen weiterhin auch ohne externen KI-Key.
