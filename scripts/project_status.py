# WICHTIG: Dieses Skript muss bei jeder Projektänderung mitgepflegt werden.
# Neue Tabellen, Endpunkte und Dateien hier ergänzen.

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parent.parent
IGNORED_DIRS = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist"}

CORE_FILES = [
    Path(".github/workflows/test.yml"),
    Path("scripts/project_status.py"),
    Path("scripts/data_quality_check.py"),
    Path("scripts/migrate_schema_preserve.py"),
    Path("scripts/import_knowledge.py"),
    Path("scripts/kpi_auto_report.py"),
    Path("scripts/cleanup_db.py"),
    Path("scripts/start_day.ps1"),
    Path("backend/app.py"),
    Path("backend/models.py"),
    Path("backend/requirements.txt"),
    Path("backend/conftest.py"),
    Path("backend/pytest.ini"),
    Path("backend/tests/test_api_endpoints.py"),
    Path("backend/tests/test_feedback_service.py"),
    Path("backend/tests/test_recommendation_service.py"),
    Path("backend/tests/test_scripts/test_data_quality_check.py"),
    Path("backend/.env.example"),
    Path("backend/routes/domains.py"),
    Path("frontend/package.json"),
    Path("frontend/package-lock.json"),
    Path("frontend/vite.config.js"),
    Path("frontend/vitest.config.js"),
    Path("frontend/src/setup.test.js"),
    Path("frontend/src/__tests__/App.test.jsx"),
    Path("frontend/index.html"),
    Path("frontend/src/App.jsx"),
    Path("frontend/src/main.jsx"),
    Path("frontend/src/pages/Dashboard.jsx"),
    Path("frontend/src/pages/ProfilePage.jsx"),
    Path("frontend/src/pages/HistoryPage.jsx"),
    Path("frontend/src/pages/ConfigPage.jsx"),
    Path("docker-compose.yml"),
    Path("README.md"),
]

REQUIRED_DB_TABLES = [
    "workflow_categories",
    "sub_categories",
    "task_templates",
    "user_context",
    "research_sessions",
    "recommendation_feedback",
]

REQUIRED_ENDPOINTS = [
    "/api/health",
    "/api/system/stats",
    "/api/recommendation",
    "/api/workflow-history",
    "/api/tools",
    "/api/domains",
    "/api/categories",
    "/api/task-templates",
    "/api/research-session",
    "/api/research-sessions",
    "/api/user-context",
    "/api/kpis",
    "/api/kpis/targets",
    "/api/kpis/report",
    "/api/kpis/scheduler-status",
    "/api/recommendation-feedback",
    "/api/telegram/status",
    "/api/telegram/setup-webhook",
    "/api/telegram/webhook/<secret>",
]

TELEGRAM_ENV_KEYS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "TELEGRAM_WEBHOOK_BASE_URL",
    "TELEGRAM_ALLOWED_CHAT_IDS",
    "TELEGRAM_MODE",
]

KPI_ENV_KEYS = [
    "KPI_AUTOREPORT_ENABLED",
    "KPI_AUTOREPORT_INTERVAL_MINUTES",
    "KPI_REPORT_WINDOW_DAYS",
]

LOG_DIR = ROOT / "logs"
LOG_RETENTION_DAYS = 7


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def build_tree_lines(base: Path) -> list[str]:
    lines = [str(base)]

    def walk(current: Path, prefix: str = ""):
        try:
            children = [c for c in sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())) if not should_ignore(c.relative_to(base))]
        except (PermissionError, OSError):
            return

        for idx, child in enumerate(children):
            is_last = idx == len(children) - 1
            branch = "└── " if is_last else "├── "
            name = child.name + ("/" if child.is_dir() else "")
            lines.append(prefix + branch + name)
            if child.is_dir():
                extension = "    " if is_last else "│   "
                walk(child, prefix + extension)

    walk(base)
    return lines


def find_db_path() -> Path | None:
    preferred = ROOT / "backend" / "instance" / "workflow.db"
    if preferred.exists():
        return preferred

    candidates = []
    for candidate in ROOT.rglob("*.db"):
        if should_ignore(candidate.relative_to(ROOT)):
            continue
        candidates.append(candidate)

    return candidates[0] if candidates else None


def get_db_report(db_path: Path) -> list[str]:
    report = []
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        report.append("Keine Tabellen gefunden.")
        connection.close()
        return report

    table_counts: dict[str, int] = {}

    for table in tables:
        report.append(f"Tabelle: {table}")
        cursor.execute(f'PRAGMA table_info("{table}")')
        columns = cursor.fetchall()
        if columns:
            for column in columns:
                col_name = column[1]
                col_type = column[2] if column[2] else "UNKNOWN"
                report.append(f"  - {col_name}: {col_type}")
        else:
            report.append("  - Keine Spalteninformationen")

        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cursor.fetchone()[0]
        table_counts[table] = count
        report.append(f"  Einträge: {count}")

        report.append("  Vorschau (erste 2 Einträge):")
        cursor.execute(f'SELECT * FROM "{table}" LIMIT 2')
        rows = cursor.fetchall()
        if rows:
            for idx, row in enumerate(rows, 1):
                entry = {key: row[key] for key in row.keys()}
                report.append(f"    {idx}. {entry}")
        else:
            report.append("    (keine Einträge)")

    report.append("Spezialcheck neue Tabellen:")
    for table_name in REQUIRED_DB_TABLES:
        if table_name in table_counts:
            count = table_counts[table_name]
            status = "✅" if count > 0 else "⚠️"
            suffix = "hat Daten" if count > 0 else "vorhanden, aber leer"
            report.append(f"  {status} {table_name}: {count} Einträge ({suffix})")
        else:
            report.append(f"  ❌ {table_name}: fehlt")

    report.append("Tools-Mengencheck:")
    if "tools" in table_counts:
        tools_count = table_counts["tools"]
        tools_status = "⚠️" if tools_count < 60 else "✅"
        report.append(f"  {tools_status} tools: {tools_count} Einträge (Erwartung: mindestens 60)")
    else:
        report.append("  ❌ tools Tabelle fehlt")

    report.append("User-Context-Mengencheck:")
    if "user_context" in table_counts:
        context_count = table_counts["user_context"]
        context_status = "⚠️" if context_count < 8 else "✅"
        report.append(f"  {context_status} user_context: {context_count} Einträge (Erwartung: mindestens 8)")
    else:
        report.append("  ❌ user_context Tabelle fehlt")

    report.append("Workflow-History Personalisierungscheck:")
    if "workflow_history" in table_counts:
        cursor.execute('SELECT recommendation_json, created_at FROM "workflow_history" ORDER BY created_at DESC LIMIT 1')
        latest_row = cursor.fetchone()
        if latest_row and latest_row[0]:
            try:
                latest_json = json.loads(latest_row[0])
                has_personalization_note = isinstance(latest_json, dict) and "personalization_note" in latest_json
                has_next_step = isinstance(latest_json, dict) and "next_step" in latest_json
                report.append(f"  {'✅' if has_personalization_note else '❌'} personalization_note Feld vorhanden")
                report.append(f"  {'✅' if has_next_step else '❌'} next_step Feld vorhanden")
            except Exception:
                report.append("  ❌ recommendation_json im neuesten workflow_history-Eintrag ist kein valides JSON")
        else:
            report.append("  ⚠️ workflow_history ist leer")
    else:
        report.append("  ❌ workflow_history Tabelle fehlt")

    report.append("Feedback-/KPI-Check:")
    if "recommendation_feedback" in table_counts:
        feedback_count = table_counts["recommendation_feedback"]
        feedback_status = "✅" if feedback_count > 0 else "⚠️"
        report.append(f"  {feedback_status} recommendation_feedback: {feedback_count} Einträge")
    else:
        report.append("  ❌ recommendation_feedback Tabelle fehlt")

    connection.close()
    return report


def get_knowledge_base_report(db_path: Path) -> list[str]:
    report = []
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    counts = {
        "domains": None,
        "workflow_categories": None,
        "sub_categories": None,
        "task_templates": None,
        "tools": None,
    }

    for label, table_name in [
        ("domains", "domain"),
        ("workflow_categories", "workflow_categories"),
        ("sub_categories", "sub_categories"),
        ("task_templates", "task_templates"),
        ("tools", "tools"),
    ]:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            counts[label] = cursor.fetchone()[0]
        except sqlite3.Error:
            counts[label] = None

    domains_count = counts["domains"]
    if domains_count is None:
        report.append("  ❌ domains: Tabelle fehlt")
    else:
        status = "✅" if domains_count > 0 else "❌"
        report.append(f"  {status} domains: {domains_count} Einträge")

    for label in ["workflow_categories", "sub_categories", "task_templates"]:
        value = counts[label]
        if value is None:
            report.append(f"  ❌ {label}: Tabelle fehlt")
        else:
            report.append(f"  ✅ {label}: {value} Einträge")

    # Coverage checks for new taxonomy fields
    try:
        cursor.execute(
            'SELECT COUNT(*) FROM "workflow_categories" WHERE domain_id IS NOT NULL'
        )
        categories_with_domain = cursor.fetchone()[0]
        total_categories = counts["workflow_categories"] or 0
        category_domain_coverage = (categories_with_domain / total_categories * 100.0) if total_categories else 0.0
        report.append(
            f"  Kategorien mit Domain-Link: {category_domain_coverage:.1f}% ({categories_with_domain} von {total_categories})"
        )
    except sqlite3.Error:
        report.append("  Kategorien mit Domain-Link: n/a")

    tools_count = counts["tools"]
    if tools_count is None:
        report.append("  ❌ tools: Tabelle fehlt")
        report.append("  Tool-Tag-Abdeckung: n/a (0 von 0 Tools haben Tags)")
    else:
        report.append(f"  ✅ tools: {tools_count} Einträge (Ziel: 500+)")
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM "tools" WHERE tags IS NOT NULL AND LENGTH(tags) > 5'
            )
            tagged_tools = cursor.fetchone()[0]
        except sqlite3.Error:
            tagged_tools = 0

        coverage = (tagged_tools / tools_count * 100.0) if tools_count > 0 else 0.0
        report.append(
            f"  Tool-Tag-Abdeckung: {coverage:.1f}% ({tagged_tools} von {tools_count} Tools haben Tags)"
        )

        # Coverage checks for new tool metadata fields
        for field_name, label in [
            ("domain", "Tool-Domain-Abdeckung"),
            ("use_case", "Tool-UseCase-Abdeckung"),
            ("platform", "Tool-Plattform-Abdeckung"),
            ("pricing_model", "Tool-Pricing-Abdeckung"),
            ("skill_requirement", "Tool-Skill-Abdeckung"),
        ]:
            try:
                cursor.execute(
                    f'SELECT COUNT(*) FROM "tools" WHERE {field_name} IS NOT NULL AND LENGTH(TRIM({field_name})) > 0'
                )
                filled_count = cursor.fetchone()[0]
                field_coverage = (filled_count / tools_count * 100.0) if tools_count > 0 else 0.0
                report.append(
                    f"  {label}: {field_coverage:.1f}% ({filled_count} von {tools_count})"
                )
            except sqlite3.Error:
                report.append(f"  {label}: n/a")

    connection.close()
    return report


def parse_requirement_name(req_line: str) -> str:
    separators = ["==", ">=", "<=", "~=", "!=", ">", "<"]
    clean = req_line.strip()
    for sep in separators:
        if sep in clean:
            return clean.split(sep, 1)[0].strip()
    return clean


def normalize_dist_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def get_backend_report() -> list[str]:
    report = []
    report.append(f"Python-Version: {sys.version.split()[0]}")

    installed = {normalize_dist_name(dist.metadata.get("Name", "")): dist.version for dist in metadata.distributions()}

    requirements_file = ROOT / "backend" / "requirements.txt"
    report.append("Packages aus requirements.txt:")
    if requirements_file.exists():
        for line in requirements_file.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            pkg = parse_requirement_name(raw)
            key = normalize_dist_name(pkg)
            if key in installed:
                report.append(f"  ✅ {raw} (installiert: {installed[key]})")
            else:
                report.append(f"  ❌ {raw} (nicht installiert)")
    else:
        report.append("  ❌ backend/requirements.txt fehlt")

    env_path = ROOT / "backend" / ".env"
    env_map: dict[str, str] = {}
    report.append(".env Key-Namen (ohne Werte):")
    if env_path.exists():
        keys = []
        for line in env_path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#") or "=" not in clean:
                continue
            key, value = clean.split("=", 1)
            key = key.strip()
            value = value.strip()
            keys.append(key)
            env_map[key] = value
        if keys:
            for key in keys:
                report.append(f"  - {key}")
        else:
            report.append("  (keine Keys gefunden)")
    else:
        report.append("  backend/.env nicht vorhanden")

    report.append("Telegram-Konfig-Checks (.env):")
    if env_path.exists():
        for key in TELEGRAM_ENV_KEYS:
            if key in env_map:
                value = env_map.get(key, "")
                if key in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET"}:
                    status = "✅" if bool(value) else "⚠️"
                elif key == "TELEGRAM_MODE":
                    status = "✅" if value in {"polling", "webhook"} else "⚠️"
                else:
                    status = "✅"
                report.append(f"  {status} {key}: vorhanden")
            else:
                report.append(f"  ❌ {key}: fehlt")
    else:
        report.append("  ❌ backend/.env fehlt")

    report.append("KPI-Konfig-Checks (.env, optional):")
    if env_path.exists():
        for key in KPI_ENV_KEYS:
            if key in env_map:
                report.append(f"  ✅ {key}: vorhanden")
            else:
                report.append(f"  ⚠️ {key}: nicht gesetzt (Default wird genutzt)")
    else:
        report.append("  ⚠️ backend/.env fehlt")

    app_path = ROOT / "backend" / "app.py"
    routes_dir = ROOT / "backend" / "routes"
    extensions_path = ROOT / "backend" / "extensions.py"
    runtime_path = ROOT / "backend" / "services" / "runtime.py"
    services_dir = ROOT / "backend" / "services"
    recommendation_service_path = services_dir / "recommendation_service.py"

    report.append("Refactor-Struktur-Checks:")
    report.append(f"  {'✅' if routes_dir.exists() else '❌'} backend/routes/ Ordner vorhanden")
    report.append(f"  {'✅' if extensions_path.exists() else '❌'} backend/extensions.py vorhanden")

    if app_path.exists():
        with app_path.open(encoding="utf-8", errors="ignore") as app_file:
            app_line_count = sum(1 for _ in app_file)
        if app_line_count < 100:
            report.append(f"  ✅ backend/app.py unter 100 Zeilen ({app_line_count})")
        elif app_line_count > 200:
            report.append(f"  ⚠️ backend/app.py ueber 200 Zeilen ({app_line_count})")
        else:
            report.append(f"  ⚠️ backend/app.py zwischen 100 und 200 Zeilen ({app_line_count})")
    else:
        report.append("  ❌ backend/app.py fehlt")

    source_paths = [app_path, runtime_path]
    if routes_dir.exists():
        source_paths.extend(sorted(routes_dir.glob("*.py")))
    if services_dir.exists():
        source_paths.extend(sorted(services_dir.glob("*.py")))

    backend_content = ""
    for source_path in source_paths:
        if source_path.exists():
            backend_content += "\n" + source_path.read_text(encoding="utf-8", errors="ignore")

    report.append("API-Endpunkt-Checks (backend app+routes+services):")
    if backend_content:
        for endpoint in REQUIRED_ENDPOINTS:
            status = "✅" if endpoint in backend_content else "❌"
            report.append(f"  {status} {endpoint}")

        report.append("Recommendation-Micro-Prompt-Checks (recommendation_service.py):")
        if recommendation_service_path.exists():
            recommendation_service_content = recommendation_service_path.read_text(encoding="utf-8", errors="ignore")
            required_recommendation_functions = [
                "summarize_user_context",
                "build_micro_prompt",
                "call_groq_with_micro_prompt",
            ]
            for function_name in required_recommendation_functions:
                marker = f"def {function_name}("
                status = "✅" if marker in recommendation_service_content else "❌"
                report.append(f"  {status} {function_name}")
        else:
            report.append("  ❌ backend/services/recommendation_service.py fehlt")

        report.append("Telegram-Code-Checks (backend app+services):")
        has_parse_mode_html = "'parse_mode': 'HTML'" in backend_content
        has_chat_filter = "def is_chat_allowed(" in backend_content
        has_polling_loop = "def telegram_polling_loop(" in backend_content
        has_worker_loop = "def telegram_worker_loop(" in backend_content
        report.append(f"  {'✅' if has_parse_mode_html else '⚠️'} parse_mode HTML in sendMessage")
        report.append(f"  {'✅' if has_chat_filter else '❌'} Allowlist-Filter vorhanden")
        report.append(f"  {'✅' if has_polling_loop else '❌'} Polling-Loop vorhanden")
        report.append(f"  {'✅' if has_worker_loop else '❌'} Worker-Loop vorhanden")

        if recommendation_service_path.exists():
            recommendation_service_content = recommendation_service_path.read_text(encoding="utf-8", errors="ignore")
            has_micro_prompt_call = "call_groq_with_micro_prompt" in recommendation_service_content
            has_tool_need_map = "TOOL_NEED_MAP" in recommendation_service_content
            report.append(f"{'✅' if has_micro_prompt_call else '❌'} Micro-Prompt-System: call_groq_with_micro_prompt vorhanden")
            report.append(f"{'✅' if has_tool_need_map else '❌'} Tool-Matching: TOOL_NEED_MAP vorhanden")
        else:
            report.append("❌ backend/services/recommendation_service.py fehlt")

        report.append("Telegram Runtime-Status (wenn Backend läuft):")
        try:
            with urlrequest.urlopen("http://localhost:5000/api/telegram/status", timeout=2) as response:
                if response.status != 200:
                    report.append(f"  ⚠️ /api/telegram/status HTTP {response.status}")
                else:
                    payload = json.loads(response.read().decode("utf-8"))
                    report.append(f"  ✅ enabled: {payload.get('enabled')}")
                    report.append(f"  ✅ mode: {payload.get('mode')}")
                    report.append(f"  ✅ worker_started: {payload.get('worker_started')}")
                    report.append(f"  ✅ receiver_started: {payload.get('receiver_started')}")
                    report.append(f"  ✅ allowed_chat_ids_configured: {payload.get('allowed_chat_ids_configured')}")
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report.append(f"  ⚠️ Nicht erreichbar oder ungültige Antwort: {exc}")

        report.append("KPI Runtime-Status (wenn Backend läuft):")
        try:
            with urlrequest.urlopen("http://localhost:5000/api/health", timeout=2) as response:
                if response.status != 200:
                    report.append(f"  ⚠️ /api/health HTTP {response.status}")
                else:
                    payload = json.loads(response.read().decode("utf-8"))
                    groq_configured = bool(payload.get("groq_configured"))
                    if groq_configured:
                        report.append("  ✅ KI-Modus: Micro-Prompt-System aktiv")
                    else:
                        report.append("  ⚠️ KI-Modus: Regel-Fallback aktiv")

            with urlrequest.urlopen("http://localhost:5000/api/kpis?days=30", timeout=2) as response:
                if response.status != 200:
                    report.append(f"  ⚠️ /api/kpis HTTP {response.status}")
                else:
                    payload = json.loads(response.read().decode("utf-8"))
                    report.append(f"  ✅ recommendation_count: {payload.get('recommendation_count')}")
                    report.append(f"  ✅ feedback_count: {payload.get('feedback_count')}")
                    report.append(f"  ✅ avg_user_rating: {payload.get('avg_user_rating')}")
                    report.append(f"  ✅ top3_hit_rate: {payload.get('top3_hit_rate')}")
                    report.append(f"  ✅ kpi_health_index: {payload.get('kpi_health_index')}")
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report.append(f"  ⚠️ KPI nicht erreichbar oder ungültig: {exc}")

        report.append("KPI Targets Runtime-Status (wenn Backend läuft):")
        try:
            with urlrequest.urlopen("http://localhost:5000/api/kpis/targets", timeout=2) as response:
                if response.status != 200:
                    report.append(f"  ⚠️ /api/kpis/targets HTTP {response.status}")
                else:
                    payload = json.loads(response.read().decode("utf-8"))
                    report.append(f"  ✅ target_count: {len(payload) if isinstance(payload, dict) else 0}")
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report.append(f"  ⚠️ KPI-Targets nicht erreichbar oder ungültig: {exc}")

        report.append("KPI Scheduler Runtime-Status (wenn Backend läuft):")
        try:
            with urlrequest.urlopen("http://localhost:5000/api/kpis/scheduler-status", timeout=2) as response:
                if response.status != 200:
                    report.append(f"  ⚠️ /api/kpis/scheduler-status HTTP {response.status}")
                else:
                    payload = json.loads(response.read().decode("utf-8"))
                    report.append(f"  ✅ enabled: {payload.get('enabled')}")
                    report.append(f"  ✅ started: {payload.get('started')}")
                    report.append(f"  ✅ interval_minutes: {payload.get('interval_minutes')}")
                    report.append(f"  ✅ last_report_at: {payload.get('last_report_at')}")
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report.append(f"  ⚠️ KPI-Scheduler nicht erreichbar oder ungültig: {exc}")
    else:
        report.append("  ❌ Keine Backend-Quelldateien für Endpoint-Checks gefunden")

    return report


def get_frontend_report() -> list[str]:
    report = []

    try:
        node_version = subprocess.check_output(["node", "-v"], stderr=subprocess.STDOUT, text=True).strip()
        report.append(f"Node-Version: {node_version}")
    except Exception:
        report.append("Node-Version: Nicht gefunden")

    package_json_path = ROOT / "frontend" / "package.json"
    report.append("Packages aus package.json:")
    if package_json_path.exists():
        try:
            package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
            dependencies = package_data.get("dependencies", {})
            dev_dependencies = package_data.get("devDependencies", {})

            if dependencies:
                report.append("  dependencies:")
                for name in sorted(dependencies.keys()):
                    report.append(f"    - {name}: {dependencies[name]}")
            else:
                report.append("  dependencies: keine")

            if dev_dependencies:
                report.append("  devDependencies:")
                for name in sorted(dev_dependencies.keys()):
                    report.append(f"    - {name}: {dev_dependencies[name]}")
            else:
                report.append("  devDependencies: keine")
        except Exception as exc:
            report.append(f"  Fehler beim Lesen von package.json: {exc}")
    else:
        report.append("  ❌ frontend/package.json fehlt")

    node_modules_exists = (ROOT / "frontend" / "node_modules").exists()
    report.append(f"node_modules vorhanden: {'ja' if node_modules_exists else 'nein'}")

    report.append("Neue Seiten vorhanden:")
    history_page = ROOT / "frontend" / "src" / "pages" / "HistoryPage.jsx"
    config_page = ROOT / "frontend" / "src" / "pages" / "ConfigPage.jsx"
    research_page = ROOT / "frontend" / "src" / "pages" / "ResearchPage.jsx"
    app_page = ROOT / "frontend" / "src" / "App.jsx"
    report.append(f"  {'✅' if history_page.exists() else '❌'} frontend/src/pages/HistoryPage.jsx")
    report.append(f"  {'✅' if config_page.exists() else '❌'} frontend/src/pages/ConfigPage.jsx")
    report.append(f"  {'✅' if not research_page.exists() else '⚠️'} frontend/src/pages/ResearchPage.jsx entfernt")

    report.append("Navigation-Check (App.jsx):")
    if app_page.exists():
        app_content = app_page.read_text(encoding="utf-8", errors="ignore")
        has_history_route = "/history" in app_content
        has_config_route = "/config" in app_content
        has_profile_route = "/profile" in app_content
        has_old_research_route = "/research" in app_content
        has_history_import = "HistoryPage" in app_content
        has_config_import = "ConfigPage" in app_content
        report.append(f"  {'✅' if has_history_route else '❌'} Verlauf-Route vorhanden")
        report.append(f"  {'✅' if has_config_route else '❌'} Config-Route vorhanden")
        report.append(f"  {'✅' if has_profile_route else '❌'} Profil-Route vorhanden")
        report.append(f"  {'✅' if has_history_import else '❌'} HistoryPage eingebunden")
        report.append(f"  {'✅' if has_config_import else '❌'} ConfigPage eingebunden")
        report.append(f"  {'✅' if not has_old_research_route else '⚠️'} Recherche-Route entfernt")
    else:
        report.append("  ❌ frontend/src/App.jsx fehlt")

    report.append("Test-Infra-Check (Frontend):")
    vitest_config = ROOT / "frontend" / "vitest.config.js"
    setup_test = ROOT / "frontend" / "src" / "setup.test.js"
    app_test = ROOT / "frontend" / "src" / "__tests__" / "App.test.jsx"
    report.append(f"  {'✅' if vitest_config.exists() else '❌'} frontend/vitest.config.js")
    report.append(f"  {'✅' if setup_test.exists() else '❌'} frontend/src/setup.test.js")
    report.append(f"  {'✅' if app_test.exists() else '❌'} frontend/src/__tests__/App.test.jsx")

    report.append("CSS-Designsystem-Altklassencheck (index.css):")
    css_path = ROOT / "frontend" / "src" / "index.css"
    deprecated_css_classes = ["tag-beginner", "tag-advanced", "tag-expert"]
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8", errors="ignore")
        has_tag_beginner = "tag-beginner" in css_content
        report.append(f"  {'✅' if not has_tag_beginner else '❌'} tag-beginner nicht vorhanden")
        found = [cls for cls in deprecated_css_classes if cls in css_content]
        if found:
            report.append(f"  ❌ Veraltete Klassen noch vorhanden: {', '.join(found)}")
        else:
            report.append("  ✅ Keine veralteten Tag-Klassen in index.css")
    else:
        report.append("  ❌ frontend/src/index.css fehlt")

    report.append("Seiten-Zeilenzahl-Check (Mindestziel: 120):")
    if history_page.exists():
        history_lines = count_lines(history_page)
        history_status = "⚠️" if history_lines < 120 else "✅"
        report.append(f"  {history_status} frontend/src/pages/HistoryPage.jsx: {history_lines} Zeilen")
    else:
        report.append("  ❌ frontend/src/pages/HistoryPage.jsx: fehlt")

    if config_page.exists():
        config_lines = count_lines(config_page)
        config_status = "⚠️" if config_lines < 120 else "✅"
        report.append(f"  {config_status} frontend/src/pages/ConfigPage.jsx: {config_lines} Zeilen")
    else:
        report.append("  ❌ frontend/src/pages/ConfigPage.jsx: fehlt")

    report.append("Knowledge-UI-Checks (Dashboard/Profile):")
    dashboard_page = ROOT / "frontend" / "src" / "pages" / "Dashboard.jsx"
    profile_page = ROOT / "frontend" / "src" / "pages" / "ProfilePage.jsx"
    if dashboard_page.exists():
        dashboard_content = dashboard_page.read_text(encoding="utf-8", errors="ignore")
        dashboard_checks = [
            ("categoriesData", "Dashboard lädt Categories"),
            ("setToolsCatalog", "Dashboard lädt Tool-Katalog"),
            ("kpiSummary", "Dashboard zeigt KPI-Metriken"),
            ("pricing_model", "Dashboard zeigt Pricing"),
            ("skill_requirement", "Dashboard zeigt Skill-Level"),
            ("platform", "Dashboard zeigt Plattform"),
            ("use_case", "Dashboard zeigt Use-Case"),
        ]
        for marker, label in dashboard_checks:
            status = "✅" if marker in dashboard_content else "❌"
            report.append(f"  {status} {label}")
    else:
        report.append("  ❌ frontend/src/pages/Dashboard.jsx fehlt")

    if profile_page.exists():
        profile_content = profile_page.read_text(encoding="utf-8", errors="ignore")
        profile_checks = [
            ("toolStats", "Profile zeigt Tool-Coverage-Metriken"),
            ("categoryOptions", "Profile nutzt dynamische Kategorien"),
            ("tool.domain", "Profile zeigt Tool-Domain"),
            ("tool.pricing_model", "Profile zeigt Tool-Pricing"),
            ("tool.use_case", "Profile zeigt Tool-Use-Case"),
            ("getTagList", "Profile rendert Tool-Tags"),
        ]
        for marker, label in profile_checks:
            status = "✅" if marker in profile_content else "❌"
            report.append(f"  {status} {label}")
    else:
        report.append("  ❌ frontend/src/pages/ProfilePage.jsx fehlt")

    report.append("Frontend JSX-Dateien:")
    jsx_files = []
    frontend_src = ROOT / "frontend" / "src"
    if frontend_src.exists():
        for file_path in frontend_src.rglob("*.jsx"):
            rel = file_path.relative_to(ROOT)
            if should_ignore(rel):
                continue
            jsx_files.append(file_path)

    for file_path in sorted(jsx_files, key=lambda p: str(p.relative_to(ROOT)).lower()):
        rel = file_path.relative_to(ROOT)
        line_count = count_lines(file_path)
        modified = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        report.append(f"  - {rel} | Zeilen: {line_count} | Letzte Änderung: {modified}")

    return report


def get_scripts_report() -> list[str]:
    report = []

    script_checks = [
        (ROOT / "scripts" / "import_knowledge.py", ["--dry-run", "validate_payload", "import_payload"], "Knowledge-Import"),
        (ROOT / "scripts" / "data_quality_check.py", ["--fix", "print_audit", "apply_fixes"], "Data-Quality-Check"),
        (ROOT / "scripts" / "migrate_schema_preserve.py", ["ALTER TABLE", "domain", "ix_tool_domain"], "Schema-Migration"),
        (ROOT / "scripts" / "start_day.ps1", ["project_status.py", "python", "Write-Host"], "Tagesstart-Automation"),
    ]

    for path, markers, label in script_checks:
        if not path.exists():
            report.append(f"  ❌ {label}: {path.relative_to(ROOT)} fehlt")
            continue

        content = path.read_text(encoding="utf-8", errors="ignore")
        report.append(f"  ✅ {label}: {path.relative_to(ROOT)} vorhanden")
        for marker in markers:
            status = "✅" if marker in content else "⚠️"
            report.append(f"    {status} Marker `{marker}`")

    report.append("  Legacy-Importer (archiviert):")
    legacy_checks = [
        (ROOT / "scripts" / "archive" / "import_all_data.py", "scripts/archive/import_all_data.py"),
        (ROOT / "scripts" / "archive" / "import_tools.py", "scripts/archive/import_tools.py"),
    ]
    for path, label in legacy_checks:
        if path.exists():
            report.append(f"    ✅ {label} vorhanden (deprecated)")
        else:
            report.append(f"    ⚠️ {label} nicht gefunden (optional, da deprecated)")

    return report


def get_docs_report() -> list[str]:
    report = []

    doc_path = ROOT / "PROJEKT_DOKUMENTATION.md"
    readme_path = ROOT / "README.md"

    report.append("Projektdoku-Checks:")
    if not doc_path.exists():
        report.append("  ❌ PROJEKT_DOKUMENTATION.md fehlt")
    else:
        content = doc_path.read_text(encoding="utf-8", errors="ignore")
        checks = [
            ("/api/domains", "Domains-Endpunkt dokumentiert"),
            ("import_knowledge.py", "Knowledge-Import dokumentiert"),
            ("data_quality_check.py", "Data-Quality-Check dokumentiert"),
            ("migrate_schema_preserve.py", "Schema-Migration dokumentiert"),
            ("pytest", "Backend-Tests dokumentiert"),
            ("Vitest", "Frontend-Tests dokumentiert"),
            (".github/workflows/test.yml", "CI-Workflow dokumentiert"),
            ("domain", "Domain-Modell dokumentiert"),
            ("pricing_model", "Erweiterte Tool-Felder dokumentiert"),
        ]
        for marker, label in checks:
            status = "✅" if marker in content else "⚠️"
            report.append(f"  {status} {label}")

    report.append("README-Checks:")
    if not readme_path.exists():
        report.append("  ❌ README.md fehlt")
    else:
        content = readme_path.read_text(encoding="utf-8", errors="ignore")
        checks = [
            ("/api/domains", "Domains-Endpunkt in README"),
            ("/api/categories", "Kategorien-Endpunkt in README"),
            ("import_knowledge.py", "Knowledge-Import in README"),
            ("data_quality_check.py", "Data-Quality-Check in README"),
            ("migrate_schema_preserve.py", "Schema-Migration in README"),
            ("python -m pytest", "Backend-Testbefehl in README"),
            ("npm run test", "Frontend-Testbefehl in README"),
            (".github/workflows/test.yml", "CI-Workflow in README"),
        ]
        for marker, label in checks:
            status = "✅" if marker in content else "⚠️"
            report.append(f"  {status} {label}")

    return report


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as file:
            return sum(1 for _ in file)
    except Exception:
        return 0


def get_code_overview() -> list[str]:
    report = []
    files = []
    for pattern in ("*.py", "*.jsx"):
        for file_path in ROOT.rglob(pattern):
            rel = file_path.relative_to(ROOT)
            if should_ignore(rel):
                continue
            files.append(file_path)

    for file_path in sorted(files, key=lambda p: str(p.relative_to(ROOT)).lower()):
        rel = file_path.relative_to(ROOT)
        line_count = count_lines(file_path)
        modified = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        report.append(f"- {rel} | Zeilen: {line_count} | Letzte Änderung: {modified}")

    return report


def cleanup_old_logs(log_dir: Path, retention_days: int) -> None:
    if not log_dir.exists():
        return

    cutoff_timestamp = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
    for file_path in log_dir.glob("status_*.txt"):
        try:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_timestamp:
                file_path.unlink()
        except OSError:
            continue


def main():
    try:
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    except Exception:
        pass

    out = []

    out.append("PROJECT STATUS REPORT")
    out.append("=" * 80)

    out.append("")
    out.append("DATEISTRUKTUR")
    out.append("-" * 80)
    out.extend(build_tree_lines(ROOT))

    out.append("")
    out.append("Kerndateien")
    for rel in CORE_FILES:
        exists = (ROOT / rel).exists()
        out.append(f"{'✅' if exists else '❌'} {rel}")

    out.append("")
    out.append("DATENBANK")
    out.append("-" * 80)
    db_path = find_db_path()
    if db_path is None:
        out.append("Pfad zur .db Datei: Nicht gefunden")
    else:
        out.append(f"Pfad zur .db Datei: {db_path}")
        out.extend(get_db_report(db_path))

    out.append("")
    out.append("WISSENSBASIS-CHECK")
    out.append("\nWISSENSBASIS")
    out.append("-" * 80)
    if db_path is None:
        out.append("  ❌ Keine Datenbank gefunden")
    else:
        out.extend(get_knowledge_base_report(db_path))

    out.append("")
    out.append("BACKEND")
    out.append("-" * 80)
    out.extend(get_backend_report())

    out.append("")
    out.append("FRONTEND")
    out.append("-" * 80)
    out.extend(get_frontend_report())

    out.append("")
    out.append("SCRIPTS")
    out.append("-" * 80)
    out.extend(get_scripts_report())

    out.append("")
    out.append("DOKUMENTATION")
    out.append("-" * 80)
    out.extend(get_docs_report())

    out.append("")
    out.append("CODE-ÜBERBLICK")
    out.append("-" * 80)
    out.extend(get_code_overview())

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_old_logs(LOG_DIR, LOG_RETENTION_DAYS)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = LOG_DIR / f"status_{timestamp}.txt"
    relative_log_path = log_file.relative_to(ROOT).as_posix()
    log_line = f"Log gespeichert: {relative_log_path}"

    output = "\n".join(out) + "\n" + log_line
    print(output)

    with log_file.open("w", encoding="utf-8") as f:
        f.write(output)


if __name__ == "__main__":
    main()
