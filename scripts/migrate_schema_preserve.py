"""Nicht-destruktive DB-Migration fuer die neue Wissensbasis.

Fuehrt nur additive Schema-Aenderungen aus:
- Tabelle `domain` erstellen (falls fehlend)
- Fehlende Spalten in `workflow_categories` und `tools` ergaenzen
- Indizes fuer Tool-Domain/Tags erstellen

Bestehende Daten bleiben unveraendert erhalten.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "backend" / "instance" / "workflow.db"


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def ensure_domain_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS domain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description VARCHAR(500),
            icon VARCHAR(10),
            tags VARCHAR(500),
            sort_order INTEGER DEFAULT 0
        )
        """
    )


def migrate_legacy_domains_table(conn: sqlite3.Connection) -> None:
    """Copy rows from legacy `domains` table into canonical `domain` table."""
    if not table_exists(conn, "domains"):
        return

    domain_cols = get_columns(conn, "domains")
    has_tags = "tags" in domain_cols

    if has_tags:
        rows = conn.execute(
            "SELECT name, description, icon, tags, sort_order FROM domains"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT name, description, icon, sort_order FROM domains"
        ).fetchall()

    copied = 0
    for row in rows:
        if has_tags:
            name, description, icon, tags, sort_order = row
        else:
            name, description, icon, sort_order = row
            tags = None

        exists = conn.execute(
            "SELECT 1 FROM domain WHERE name = ? LIMIT 1",
            (name,),
        ).fetchone()
        if exists:
            continue

        conn.execute(
            """
            INSERT INTO domain (name, description, icon, tags, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, description, icon, tags, sort_order or 0),
        )
        copied += 1

    if copied:
        print(f"+ legacy domains -> domain: {copied} uebernommen")


def ensure_workflow_category_columns(conn: sqlite3.Connection) -> None:
    existing = get_columns(conn, "workflow_categories")
    if "domain_id" not in existing:
        conn.execute("ALTER TABLE workflow_categories ADD COLUMN domain_id INTEGER")
        print("+ workflow_categories.domain_id")
    if "tags" not in existing:
        conn.execute("ALTER TABLE workflow_categories ADD COLUMN tags VARCHAR(500)")
        print("+ workflow_categories.tags")
    if "sort_order" not in existing:
        conn.execute(
            "ALTER TABLE workflow_categories ADD COLUMN sort_order INTEGER DEFAULT 0"
        )
        print("+ workflow_categories.sort_order")


def ensure_tool_columns(conn: sqlite3.Connection) -> None:
    existing = get_columns(conn, "tools")
    if "domain" not in existing:
        conn.execute("ALTER TABLE tools ADD COLUMN domain VARCHAR(100)")
        print("+ tools.domain")
    if "tags" not in existing:
        conn.execute("ALTER TABLE tools ADD COLUMN tags VARCHAR(500)")
        print("+ tools.tags")
    if "use_case" not in existing:
        conn.execute("ALTER TABLE tools ADD COLUMN use_case VARCHAR(500)")
        print("+ tools.use_case")
    if "platform" not in existing:
        conn.execute("ALTER TABLE tools ADD COLUMN platform VARCHAR(100)")
        print("+ tools.platform")
    if "pricing_model" not in existing:
        conn.execute("ALTER TABLE tools ADD COLUMN pricing_model VARCHAR(100)")
        print("+ tools.pricing_model")


def ensure_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS ix_tool_domain ON tools(domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_tool_tags ON tools(tags)")


def seed_domains_if_empty(conn: sqlite3.Connection) -> int:
    count = conn.execute("SELECT COUNT(*) FROM domain").fetchone()[0]
    if count:
        return int(count)

    domains = [
        ("Coding & Development", "Programmierung, Debugging, Code-Reviews", "[CD]"),
        ("Research & Analysis", "Recherche, Quellenanalyse, Zusammenfassungen", "[RA]"),
        ("Writing & Content", "Texterstellung, Storytelling, SEO-Content", "[WC]"),
        ("Design & Creativity", "Grafik, Bildgenerierung, visuelle Konzepte", "[DC]"),
        ("Productivity & Workflow", "Planung, Automatisierung, Task-Management", "[PW]"),
        ("Education & Learning", "Lernen, Erklaeren, Uebungen, Didaktik", "[EL]"),
        ("Business & Marketing", "Strategie, Kampagnen, Marktanalysen", "[BM]"),
        ("Data & BI", "Datenanalyse, Dashboards, Insights", "[DB]"),
    ]

    for sort_order, (name, description, icon) in enumerate(domains, start=1):
        conn.execute(
            """
            INSERT INTO domain (name, description, icon, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, icon, sort_order),
        )

    return len(domains)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB nicht gefunden: {DB_PATH}")

    print(f"Migration startet fuer: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys=ON")

        if not table_exists(conn, "workflow_categories"):
            raise RuntimeError("Tabelle workflow_categories fehlt")
        if not table_exists(conn, "tools"):
            raise RuntimeError("Tabelle tools fehlt")

        ensure_domain_table(conn)
        migrate_legacy_domains_table(conn)
        ensure_workflow_category_columns(conn)
        ensure_tool_columns(conn)
        ensure_indexes(conn)
        seeded = seed_domains_if_empty(conn)

        conn.commit()

    print(f"Migration abgeschlossen. Domains vorhanden: {seeded}")


if __name__ == "__main__":
    main()
