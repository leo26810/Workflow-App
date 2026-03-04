# PROJEKT-DOKUMENTATION (Vollständig)

## 1) Projektüberblick

**Name:** FlowAI – persönlicher Workflow-Optimizer für Schule, Recherche und KI-gestützte Aufgaben.

**Ziel:**
- Aufgaben in natürlicher Sprache entgegennehmen.
- Kontext aus Nutzerprofil + Verlauf + gespeicherten Kontextfeldern berücksichtigen.
- Eine personalisierte Empfehlung (Workflow, Toolliste, Prompt, Tipps, nächster Schritt) erzeugen.
- Ergebnisse speichern, bewerten und wiederverwerten.

**Architektur:**
- Frontend: React + Vite (`frontend/`)
- Backend: Flask + SQLAlchemy + SQLite (`backend/`)
- Wartung/Diagnose: Python-Skripte (`scripts/`)
- Containerbetrieb: Docker Compose + zwei Services (frontend/backend)

**Hauptdatenfluss:**
1. User startet Empfehlung im Dashboard.
2. Frontend sendet `POST /api/recommendation`.
3. Backend klassifiziert Aufgabe, zieht Profil-/Historien-/Kontextdaten.
4. Backend versucht Groq-LLM (Modell-Fallback); bei Fehler fallback auf regelbasiert.
5. Backend normalisiert Output, speichert Verlauf, liefert JSON zurück.
6. Frontend zeigt Ergebnis, optional mit Sterne-Feedback und Session-Speicherung.

---

## 2) Repository-Struktur

```text
.
├─ backend/
│  ├─ app.py
│  ├─ models.py
│  ├─ requirements.txt
│  ├─ .env
│  ├─ .env.example
│  └─ instance/             # SQLite DB-Datei im Betrieb (workflow.db)
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ src/
│  │  ├─ main.jsx
│  │  ├─ App.jsx
│  │  ├─ index.css
│  │  └─ pages/
│  │     ├─ Dashboard.jsx
│  │     ├─ ProfilePage.jsx
│  │     ├─ SchoolPage.jsx
│  │     └─ ResearchPage.jsx
├─ scripts/
│  ├─ project_status.py
│  ├─ cleanup_db.py
│  ├─ import_all_data.py
│  └─ import_tools.py
├─ docker-compose.yml
├─ Dockerfile.backend
├─ Dockerfile.frontend
├─ pyrightconfig.json
├─ .dockerignore
├─ README.md
└─ logs/                    # Status-Reports (durch project_status.py)
```

---

## 3) Technologien & Versionen

### Backend (`backend/requirements.txt`)
- `flask==3.0.3`
- `flask-sqlalchemy==3.1.1`
- `flask-cors==4.0.1`
- `flask-compress==1.15`
- `requests==2.32.3`
- `python-dotenv==1.0.1`

### Frontend (`frontend/package.json`)
- Laufzeit:
  - `react` 18.x
  - `react-dom` 18.x
  - `react-router-dom` 6.x
- Build/Dev:
  - `vite` 5.x
  - `@vitejs/plugin-react`
  - `tailwindcss` 3.x (+ postcss/autoprefixer)

---

## 4) Umgebungsvariablen

### Backend `.env` / `.env.example`
- `GROQ_API_KEY`
  - leer/placeholder ⇒ Demo-/Fallback-Modus
  - gesetzt ⇒ Versuch echter KI-Antwort über Groq API

### Laufzeitvariablen (Compose/Backend)
- `CORS_ORIGINS` (CSV-Liste)
- `PORT` (Backend-Port, standardmäßig `5000`)
- `FLASK_DEBUG` (`true`/`false`)
- `DATABASE_URL` (optional; sonst lokale SQLite in `backend/instance/workflow.db`)

---

## 5) Backend-Architektur (`backend/app.py`)

### 5.1 Initialisierung
- Flask-App + `flask_compress` aktiviert (komprimierte API-Responses).
- CORS mit Origins aus `CORS_ORIGINS`.
- SQLite-Defaultpfad: `backend/instance/workflow.db`.
- DB-Setup über SQLAlchemy (`db.init_app(app)`).

### 5.2 Caching/Performance
1. **TTL-Decorator (`ttl_cache`)** für zeitbasiertes In-Memory-Caching.
2. **LRU + TTL** auf:
   - `get_tools_page_cached(page, limit)`
   - `get_skills_page_cached(page, limit)`
   - `get_profile_payload_cached(page, limit)`
   - `get_tool_scores()`
3. **Request-Dedup** für Empfehlungen:
   - identische `task_description` wird 60s dedupliziert
   - liefert gecachte Payload, wenn vollständig vorhanden
4. **Cache-Invalidierung** über `clear_data_caches()` bei Profil-/Tool-/Skill-/Goal-Änderungen.

### 5.3 Seeding
- `seed_database()` erzeugt Initialdaten (User, Skills, Goals, Tools), wenn leer.
- `seed_extended_data()` ergänzt/normalisiert Felder, erzeugt Nutzungsdaten, PromptTemplates, WorkflowHistory, UserPreferences, SkillProgress.
- `seed_categories()` erstellt Kategorien, Unterkategorien und TaskTemplates idempotent.
- Beim Start:
  - `db.create_all()` im App-Kontext
  - Seeding läuft in Hintergrund-Thread

---

## 6) Datenmodell (`backend/models.py`)

### 6.1 Tabellen (Modelle)
1. `users`
   - Felder: `id`, `name`
2. `skills`
   - Felder: `id`, `name`, `level`
3. `goals`
   - Felder: `id`, `description`
4. `tools`
   - Felder: `id`, `name`, `category`, `url`, `notes`, `is_free`, `free_tier_details`, `skill_requirement`, `best_for`, `prompt_template`, `rating`
5. `tool_usage_logs`
   - Felder: `id`, `tool_id`, `task_description`, `rating`, `timestamp`, `was_helpful`
6. `prompt_templates`
   - Felder: `id`, `title`, `prompt_text`, `category`, `tool_id`, `use_count`, `created_at`
7. `workflow_history`
   - Felder: `id`, `task_description`, `recommendation_json`, `created_at`, `user_rating`
8. `user_preferences`
   - Felder: `id`, `key`, `value`
9. `skill_progress`
   - Felder: `id`, `skill_id`, `date`, `level`, `note`
10. `workflow_categories`
    - Felder: `id`, `name`, `icon`, `description`
11. `sub_categories`
    - Felder: `id`, `category_id`, `name`, `description`
12. `task_templates`
    - Felder: `id`, `subcategory_id`, `title`, `description`, `example_input`, `tags`
13. `user_context`
    - Felder: `id`, `area`, `key`, `value`, `updated_at`
14. `research_sessions`
    - Felder: `id`, `query`, `sources` (JSON), `summary`, `created_at`, `tags`
15. `school_projects`
    - Felder: `id`, `title`, `subject`, `deadline`, `status`, `description`, `notes`, `created_at`

### 6.2 Wichtige Relationen
- `Tool` → viele `ToolUsageLog`
- `Tool` → viele `PromptTemplate`
- `WorkflowCategory` → viele `SubCategory`
- `SubCategory` → viele `TaskTemplate`
- `Skill` → viele `SkillProgress`

---

## 7) Seed-Inhalte (fachlich)

### 7.1 Hauptkategorien
1. `KI-Verwendung`
2. `Internet-Recherche`
3. `Schule`

### 7.2 Unterkategorien
- KI-Verwendung:
  - Bilderstellung
  - Programmierung
  - Promptgeneration
  - Analysen & Zusammenfassung
- Internet-Recherche:
  - Bildersuche
  - Informationsrecherche
- Schule:
  - Mitschreiben & Dokumente
  - Schulprojekte
  - Lernen & Üben

### 7.3 TaskTemplate-Titel (Seed)
- Bilderstellung:
  - Logo für AG erstellen
  - Titelbild für Referat
  - Infografik-Visual erzeugen
- Programmierung:
  - Python-Hausaufgabe debuggen
  - Mini-Tool für Lernplan
  - Code erklären lassen
- Promptgeneration:
  - Prompt für Zusammenfassung
  - Prompt für Lernkarten
  - Prompt für Mathe-Erklärung
- Analysen & Zusammenfassung:
  - Kapitelanalyse Deutsch
  - Quellenvergleich Geschichte
  - Lernzettel aus Mitschrift
- Bildersuche:
  - Quellenbild für Referat
  - Vergleichsbilder sammeln
  - Kartenmaterial finden
- Informationsrecherche:
  - Facharbeit Grundlagen sammeln
  - Pro-Contra Recherche
  - Schnellbriefing für Referat
- Mitschreiben & Dokumente:
  - Mitschrift ordnen
  - Lernblatt erstellen
  - Protokoll für Gruppenarbeit
- Schulprojekte:
  - Projektplan mit Deadlines
  - Rollen im Team verteilen
  - Abschlusspräsentation vorbereiten
- Lernen & Üben:
  - Wochenlernplan erstellen
  - Prüfungsvorbereitung strukturieren
  - Wiederholung mit Quizfragen

---

## 8) API-Referenz

## 8.1 `GET /api/profile`
Liefert Nutzerprofil inkl. paginierter Skills/Tools und Goals.

**Query-Parameter:**
- `page` (default 1)
- `limit` (default 20, max 100)

**Response (gekürzt):**
```json
{
  "user": {"id": 1, "name": "Mein Profil"},
  "skills": [...],
  "goals": [...],
  "tools": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "skills_total": 0,
    "tools_total": 0,
    "skills_pages": 0,
    "tools_pages": 0
  }
}
```

## 8.2 `POST /api/profile`
CRUD-artige Aktionen über `action`:
- `add_skill` (`name`, optional `level`)
- `delete_skill` (`id`)
- `add_goal` (`description`)
- `delete_goal` (`id`)
- `update_name` (`name`)
- `add_tool` (`name`, optional `category`, `url`, `notes`)
- `delete_tool` (`id`)

## 8.3 `GET /api/categories`
Liefert alle Kategorien inkl. Subcategories und deren TaskTemplates.

## 8.4 `GET /api/task-templates?subcategory=...`
Liefert Templates für eine Unterkategorie.
- 400 bei fehlendem `subcategory`
- 404 bei unbekannter Unterkategorie

## 8.5 `POST /api/research-session`
Speichert Recherche-Session.

**Payload:**
```json
{
  "query": "...",
  "sources": [{"url": "...", "title": "..."}],
  "summary": "...",
  "tags": "tag1,tag2"
}
```

## 8.6 `GET /api/research-sessions`
Liefert gespeicherte Sessions absteigend nach `created_at`.

## 8.7 `GET /api/school-projects`
Liefert alle Schulprojekte.

## 8.8 `POST /api/school-projects`
Aktionen über `action`:
- `add` (title+subject Pflicht, optional deadline/status/description/notes)
- `update` (id Pflicht, partielle Feldänderungen)
- `delete` (id Pflicht)

`deadline`-Format: `YYYY-MM-DD`.

## 8.9 `GET /api/user-context`
Liefert alle gespeicherten Kontext-Key-Value-Einträge.

## 8.10 `POST /api/user-context`
Setzt/aktualisiert ein Kontextfeld.

**Payload:**
```json
{ "area": "ki", "key": "ki_erfahrung", "value": "Anfänger" }
```

## 8.11 `POST /api/recommendation`
Zentrale Empfehlungserzeugung.

**Input:**
```json
{ "task_description": "Ich brauche ..." }
```

**Output (gekürzt):**
```json
{
  "task": "...",
  "recommendation": {
    "workflow": ["..."],
    "recommended_tools": [{"name":"...","reason":"...","url":"...","specific_tip":"..."}],
    "optimized_prompt": "...",
    "tips": ["..."],
    "estimated_time": "...",
    "difficulty": "easy|medium|hard",
    "alternative_approach": "...",
    "why_these_tools": "...",
    "skill_gap": "...",
    "personalization_note": "...",
    "next_step": "..."
  },
  "mode": "ai|demo",
  "model_used": "...",
  "history_id": 123,
  "area": "...",
  "subcategory": "...",
  "classification": {"type":"...","confidence":0.0}
}
```

## 8.12 `GET /api/health`
```json
{ "status": "ok", "groq_configured": true }
```

## 8.13 `GET|POST /api/workflow-history`
- `GET`: letzte 20 Verlaufseinträge
- `POST`: Rating speichern (`id`/`workflow_history_id` + `rating` 1..5)

---

## 9) Empfehlungslogik im Detail

### 9.1 Klassifikation
- keywordbasierte Zuordnung zu Task-Typen (`IMAGE`, `RESEARCH`, `WRITING`, `MATH`, `PRESENTATION`, `LEARNING`, `CODE`, `TRANSLATION`).
- zusätzlich Bereichszuordnung über `AREA_KEYWORDS` auf Area/Subcategory.
- fallback ohne Treffer: `Schule / Lernen & Üben`, `GENERAL`, niedrige Confidence.

### 9.2 Personalisierung
In den Systemprompt fließen ein:
- Skills + Level
- Goals
- Workflow-Verlauf inkl. Ratings
- Top-Tools (aus UsageLog-Ratings)
- negativ bewertete Tools (Vermeidung)
- gespeicherter UserContext
- erkannter Bereich + Unterkategorie
- passende TaskTemplates
- gesamte Tool-Datenbank (strukturierte Felder)

### 9.3 Tool-Ranking
- Basisscore je Tool
- Bonus bei Kategorie-Match zum Task-Typ
- Bonus bei präferierten Namen
- Malus bei schlechten Ratings (direkt + aus Verlauf)
- Anfänger bekommen Experten-Tools eher als optionale Challenge

### 9.4 KI/Fallback-Kette
- Modelle in Reihenfolge:
  1. `llama-3.3-70b-versatile`
  2. `llama-3.1-8b-instant`
  3. `mixtral-8x7b-32768`
- Bei HTTP 400/404 wird nächstes Modell probiert.
- Bei Parse-/API-Problemen: lokaler regelbasierter Fallback.
- Bei unerwartetem Fehler im Fallback: generischer Help-Fallback.

---

## 10) Frontend-Architektur

### 10.1 Routing (`frontend/src/App.jsx`)
- `/` und `/dashboard` → Dashboard
- `/school` → Schulprojekte
- `/research` → Recherche-Sessions
- `/profile` → Profil

Sidebar zeigt Health-Indikator (grün bei gesetztem Groq-Key, gelb sonst).

### 10.2 Dashboard (`Dashboard.jsx`)
Funktionen:
- Freitext-Aufgabe + Quick-Tasks
- optionales Autostart über Query-Parameter (`task`, `autostart`, `focus`, `subcategory`)
- lädt Kategorien/History/Profilname
- lädt Templates je Subcategory
- zeigt Empfehlung (Workflow, Tools, Prompt, Tipps, skill_gap, next_step)
- Prompt kopieren
- Sternebewertung via `/api/workflow-history`
- bei Recherche-Bereich: Session speichern via `/api/research-session`

### 10.3 Profile (`ProfilePage.jsx`)
Tabs:
- Fähigkeiten
- Ziele
- Tools
- Mein Kontext

Kontextfelder (autosave auf blur) in Bereichen:
- `schule` (schulform, hauptfaecher, staerken, schwaechen)
- `ki` (ki_erfahrung, genutzte_tools, bevorzugte_tool_typen)
- `allgemein` (lernstil, interessen, ziele, schwierigkeitsgrad)

### 10.4 School (`SchoolPage.jsx`)
- Mini-Kanban mit Statusspalten: `offen`, `in_arbeit`, `fertig`
- Projekt erstellen/bearbeiten/löschen
- Deadline-Countdown + Ampellogik
- Sidepanel für Inline-Editing
- „Workflow anfordern“ springt mit vorgefüllter Aufgabe ins Dashboard

### 10.5 Research (`ResearchPage.jsx`)
- Liste gespeicherter Recherche-Sessions
- Filter auf Query/Tags
- Expand/Collapse pro Session
- Quellenlinks
- „Als Basis nutzen“ übernimmt Query ins Dashboard

### 10.6 Styling (`index.css`)
- CSS-Variablen für Farben, Typografie, Radius
- Utility-Klassen (`card`, `btn-*`, `input-field`, `textarea-field`, etc.)
- Scrollbar-, Focus-, Selection-Styles

---

## 11) Docker & Deployment

### 11.1 Compose (`docker-compose.yml`)
Services:
1. `backend`
   - Build: Root-Kontext, `Dockerfile.backend`
   - Port: `5000:5000`
   - Volume: `./backend/instance:/workspace/backend/instance`
2. `frontend`
   - Build: `frontend` + `Dockerfile.frontend`
   - Port: `5173:5173`
   - Depends on backend

### 11.2 Backend-Image (`Dockerfile.backend`)
- Base: `python:3.11-slim`
- `WORKDIR /workspace`
- installiert `backend/requirements.txt`
- kopiert `backend/` und `scripts/`
- Start: `python backend/app.py`

### 11.3 Frontend-Image (`Dockerfile.frontend`)
- Base: `node:20-alpine`
- installiert npm dependencies
- Start Vite Dev Server auf `0.0.0.0:5173`

### 11.4 Proxy im Frontend
`frontend/vite.config.js` proxyt `/api` auf `http://backend:5000`.

---

## 12) Wartungs-Skripte (`scripts/`)

### 12.1 `project_status.py`
Erstellt umfassenden Projektstatus inkl.:
- Dateibaum
- Kerndatei-Prüfung
- DB-Tabellen + Spalten + Counts + Preview
- Checks auf neue Tabellen/Endpunkte
- Package-/Version-Checks
- Frontend-Dateiprüfungen
- Code-Overview
- schreibt Report nach `logs/status_YYYY-MM-DD_HH-MM-SS.txt`

### 12.2 `cleanup_db.py`
Bereinigt unerwünschte Citation-Artefakte und whitespace in Tool-Textfeldern:
- Felder: `free_tier_details`, `notes`, `best_for`, `prompt_template`

### 12.3 `import_tools.py`
Importiert Tooldaten aus JSON (`--json` optional):
- upsert nach Toolname
- baut Notes aus mehreren Metafeldern zusammen
- gibt Zähler aus: `added`, `updated`, `skipped`

### 12.4 `import_all_data.py`
Importiert mehrere JSON-Dateien (`--data-dir` optional):
- `tool_vervollständigung.json`
- `Tools.json`
- `tools_database.json`
- `prompt_templates.json`

Für fehlende optionale Dateien: sauberes Überspringen mit Hinweis.

---

## 13) Entwicklung lokal

### 13.1 Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 13.2 Frontend
```bash
cd frontend
npm install
npm run dev
```

### 13.3 Docker
```bash
docker compose up --build
```

---

## 14) Betrieb & Persistenz

- Primärspeicher: SQLite
- DB-Datei lokal: `backend/instance/workflow.db`
- DB-Datei im Container: `/workspace/backend/instance/workflow.db`
- Persistenz in Compose über gemountetes Host-Verzeichnis `backend/instance`

---

## 15) Qualitätssicherung & Analyse

### 15.1 Python-Analyse (`pyrightconfig.json`)
- Include: `backend`, `scripts`
- Execution Environment für `scripts` mit `extraPaths: ["backend"]`
- löst Importpfade `from app import ...` / `from models import ...` sauber auf

### 15.2 `.dockerignore`
Ignoriert u. a.:
- `node_modules`, `.venv`, `__pycache__`, `.git`, `backend/.env`, `backend/instance/workflow.db`

---

## 16) Bekannte fachliche Entscheidungen

1. **Single-User-Logik**
   - keine Auth, erster/einziger Nutzerdatensatz wird verwendet.

2. **Empfehlung auch ohne KI-Key**
   - System bleibt funktionsfähig (regelbasierte Empfehlungen).

3. **Keine harte Validierung aller Felder**
   - mehrere Endpunkte erlauben flexible, iterative Speicherung aus UI.

4. **Performance vor Perfektion**
   - In-Memory-Caches + Dedup verhindern unnötige Last.

5. **Prompt-/Tool-Personalisierung auf Verlauf**
   - negatives Feedback beeinflusst künftige Toolgewichtung.

---

## 17) Troubleshooting

### Backend startet, aber keine KI-Antwort
- Prüfen: `backend/.env` → gültiger `GROQ_API_KEY`.
- `GET /api/health` prüfen (`groq_configured`).

### Frontend lädt nicht / API-Fehler im Container
- Compose beide Container prüfen: `docker compose ps`.
- Proxy-Ziel in `frontend/vite.config.js` ist `backend:5000` (Service-Name muss stimmen).

### Import-Skripte tun „nichts“
- Bei fehlenden JSON-Dateien wird bewusst übersprungen (kein Crash).
- Eigene Dateien via `--json` / `--data-dir` übergeben.

### DB „weg“ nach Neustart
- Sicherstellen, dass `backend/instance` nicht gelöscht wurde.
- Bei `docker compose down -v` können Volumes/Daten verloren gehen.

---

## 18) Sicherheits- und Betriebsnotizen

- Keine eingebauten Auth-/Rollenmechanismen.
- CORS ist konfigurierbar und sollte in Produktion eingeschränkt werden.
- `.env` darf nicht ins VCS.
- SQLite ist für kleine/mittlere Last geeignet; bei Multi-User/Skalierung auf externe DB migrieren.

---

## 19) Erweiterungspunkte

- Authentifizierung + Multi-User-Datenmodell (User-FK in allen relevanten Tabellen).
- Asynchrone Job-Queue für Empfehlungen.
- Strukturierte Telemetrie/Tracing.
- Unit-/API-/E2E-Testabdeckung.
- Migrationssystem (z. B. Alembic).

---

## 20) Kurzfazit

Das Projekt ist ein vollständiger, lokal und in Docker lauffähiger Fullstack-Workflow-Assistent mit:
- personalisierter Empfehlungspipeline,
- modularen CRUD-/Kontext-/Projekt-/Recherche-Endpunkten,
- persistenter SQLite-Datenbasis,
- operationellen Wartungsskripten,
- robusten Fallbacks ohne externen KI-Key.

Diese Datei bildet den aktuell implementierten Zustand detailliert ab.
