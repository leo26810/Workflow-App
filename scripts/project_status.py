# WICHTIG: Dieses Skript muss bei jeder Projektänderung mitgepflegt werden.
# Neue Tabellen, Endpunkte und Dateien hier ergänzen.

import json
import os
import re
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
    Path("scripts/project_status.py"),
    Path("scripts/import_all_data.py"),
    Path("scripts/import_tools.py"),
    Path("scripts/cleanup_db.py"),
    Path("backend/app.py"),
    Path("backend/models.py"),
    Path("backend/requirements.txt"),
    Path("backend/.env.example"),
    Path("frontend/package.json"),
    Path("frontend/vite.config.js"),
    Path("frontend/index.html"),
    Path("frontend/src/App.jsx"),
    Path("frontend/src/main.jsx"),
    Path("frontend/src/pages/Dashboard.jsx"),
    Path("frontend/src/pages/ProfilePage.jsx"),
    Path("frontend/src/pages/SchoolPage.jsx"),
    Path("frontend/src/pages/ResearchPage.jsx"),
    Path("docker-compose.yml"),
    Path("README.md"),
]

REQUIRED_DB_TABLES = [
    "workflow_categories",
    "sub_categories",
    "task_templates",
    "user_context",
    "research_sessions",
    "school_projects",
]

REQUIRED_ENDPOINTS = [
    "/api/health",
    "/api/categories",
    "/api/task-templates",
    "/api/research-session",
    "/api/school-projects",
    "/api/user-context",
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

    connection.close()
    return report


def extract_model_fallback_list(app_path: Path) -> list[str]:
    if not app_path.exists():
        return []

    text = app_path.read_text(encoding="utf-8", errors="ignore")
    block_match = re.search(r"candidate_models\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not block_match:
        return []

    block = block_match.group(1)
    return re.findall(r"['\"]([^'\"]+)['\"]", block)


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

    app_path = ROOT / "backend" / "app.py"
    report.append("API-Endpunkt-Checks (app.py):")
    if app_path.exists():
        app_content = app_path.read_text(encoding="utf-8", errors="ignore")
        for endpoint in REQUIRED_ENDPOINTS:
            status = "✅" if endpoint in app_content else "❌"
            report.append(f"  {status} {endpoint}")

        report.append("Telegram-Code-Checks (app.py):")
        has_parse_mode_html = "'parse_mode': 'HTML'" in app_content
        has_chat_filter = "def is_chat_allowed(" in app_content
        has_polling_loop = "def telegram_polling_loop(" in app_content
        has_worker_loop = "def telegram_worker_loop(" in app_content
        report.append(f"  {'✅' if has_parse_mode_html else '⚠️'} parse_mode HTML in sendMessage")
        report.append(f"  {'✅' if has_chat_filter else '❌'} Allowlist-Filter vorhanden")
        report.append(f"  {'✅' if has_polling_loop else '❌'} Polling-Loop vorhanden")
        report.append(f"  {'✅' if has_worker_loop else '❌'} Worker-Loop vorhanden")

        fallback_models = extract_model_fallback_list(app_path)
        if fallback_models:
            report.append("Groq Modell-Fallback-Liste:")
            for model in fallback_models:
                report.append(f"  - {model}")
        else:
            report.append("Groq Modell-Fallback-Liste: nicht gefunden")

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
    else:
        report.append("  ❌ backend/app.py fehlt")

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
    school_page = ROOT / "frontend" / "src" / "pages" / "SchoolPage.jsx"
    research_page = ROOT / "frontend" / "src" / "pages" / "ResearchPage.jsx"
    app_page = ROOT / "frontend" / "src" / "App.jsx"
    report.append(f"  {'✅' if school_page.exists() else '❌'} frontend/src/pages/SchoolPage.jsx")
    report.append(f"  {'✅' if research_page.exists() else '❌'} frontend/src/pages/ResearchPage.jsx")

    report.append("Sidebar-Vereinfachungscheck (App.jsx):")
    if app_page.exists():
        app_content = app_page.read_text(encoding="utf-8", errors="ignore")
        has_old_expandable_nav = "KI-Verwendung" in app_content
        report.append(f"  {'❌' if has_old_expandable_nav else '✅'} Kein alter Nav-Kategorie-Text 'KI-Verwendung' in App.jsx")
    else:
        report.append("  ❌ frontend/src/App.jsx fehlt")

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

    report.append("Seiten-Zeilenzahl-Check (Mindestziel: 200):")
    if school_page.exists():
        school_lines = count_lines(school_page)
        school_status = "⚠️" if school_lines < 200 else "✅"
        report.append(f"  {school_status} frontend/src/pages/SchoolPage.jsx: {school_lines} Zeilen")
    else:
        report.append("  ❌ frontend/src/pages/SchoolPage.jsx: fehlt")

    if research_page.exists():
        research_lines = count_lines(research_page)
        research_status = "⚠️" if research_lines < 200 else "✅"
        report.append(f"  {research_status} frontend/src/pages/ResearchPage.jsx: {research_lines} Zeilen")
    else:
        report.append("  ❌ frontend/src/pages/ResearchPage.jsx: fehlt")

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
        sys.stdout.reconfigure(encoding="utf-8")
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
    out.append("BACKEND")
    out.append("-" * 80)
    out.extend(get_backend_report())

    out.append("")
    out.append("FRONTEND")
    out.append("-" * 80)
    out.extend(get_frontend_report())

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
