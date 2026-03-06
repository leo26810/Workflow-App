import argparse
import sqlite3
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "backend" / "instance" / "workflow.db"

VALID_PRICING = {"kostenlos", "freemium", "kostenpflichtig"}
VALID_SKILL = {"anfaenger", "einsteiger", "fortgeschritten", "experte"}


def norm_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_skill(value: str) -> str:
    clean = norm_text(value).lower()
    if clean in {"anfaenger", "einsteiger", "anfanger", "beginner"}:
        return "Anfaenger"
    if clean in {"fortgeschritten", "intermediate"}:
        return "Fortgeschritten"
    if clean in {"experte", "expert"}:
        return "Experte"
    return "Anfaenger"


def normalize_pricing(pricing: str, is_free: int) -> str:
    clean = norm_text(pricing).lower()
    if clean in VALID_PRICING:
        return clean
    return "kostenlos" if is_free else "kostenpflichtig"


def infer_domain_from_category(category: str) -> str:
    c = norm_text(category).lower()
    if any(k in c for k in ["marketing", "seo", "ads"]):
        return "Business & Marketing"
    if any(k in c for k in ["design", "grafik", "praesent"]):
        return "Design & Creativity"
    if any(k in c for k in ["programm", "entwick", "code", "api", "backend", "frontend"]):
        return "Coding & Development"
    if any(k in c for k in ["recherche", "analyse", "forschung", "research"]):
        return "Research & Analysis"
    if any(k in c for k in ["lernen", "schule", "education"]):
        return "Education & Learning"
    if any(k in c for k in ["data", "bi", "ml", "ai", "ki"]):
        return "Data & BI"
    if any(k in c for k in ["projekt", "workflow", "organisation", "planung"]):
        return "Productivity & Workflow"
    return "Productivity & Workflow"


def make_tags_from_text(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        chunk = norm_text(part)
        if not chunk:
            continue
        for token in chunk.replace("/", " ").replace("&", " ").replace("-", " ").split():
            t = token.strip().lower()
            if len(t) < 3:
                continue
            if t not in seen:
                seen.append(t)
    if not seen:
        return "allgemein"
    return ",".join(seen[:12])


def print_audit(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=== COUNTS ===")
    for table in ["domain", "workflow_categories", "sub_categories", "task_templates", "tools"]:
        c = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {c}")

    print("\n=== RELATION CHECKS ===")
    orphan_sub = cur.execute(
        """
        SELECT COUNT(*)
        FROM sub_categories s
        LEFT JOIN workflow_categories c ON c.id = s.category_id
        WHERE c.id IS NULL
        """
    ).fetchone()[0]
    orphan_tpl = cur.execute(
        """
        SELECT COUNT(*)
        FROM task_templates t
        LEFT JOIN sub_categories s ON s.id = t.subcategory_id
        WHERE s.id IS NULL
        """
    ).fetchone()[0]
    bad_domain_fk = cur.execute(
        """
        SELECT COUNT(*)
        FROM workflow_categories wc
        LEFT JOIN domain d ON d.id = wc.domain_id
        WHERE wc.domain_id IS NOT NULL AND d.id IS NULL
        """
    ).fetchone()[0]
    print(f"orphan_sub_categories: {orphan_sub}")
    print(f"orphan_task_templates: {orphan_tpl}")
    print(f"invalid_workflow_domain_fk: {bad_domain_fk}")

    print("\n=== MISSING FIELDS ===")
    checks = [
        ("domain", "icon"),
        ("domain", "description"),
        ("domain", "tags"),
        ("workflow_categories", "domain_id"),
        ("workflow_categories", "tags"),
        ("workflow_categories", "description"),
        ("sub_categories", "description"),
        ("task_templates", "description"),
        ("task_templates", "example_input"),
        ("task_templates", "tags"),
        ("tools", "domain"),
        ("tools", "tags"),
        ("tools", "use_case"),
        ("tools", "platform"),
        ("tools", "pricing_model"),
        ("tools", "url"),
        ("tools", "skill_requirement"),
        ("tools", "best_for"),
    ]
    for table, column in checks:
        q = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL OR TRIM(CAST({column} AS TEXT)) = ''"
        count = cur.execute(q).fetchone()[0]
        print(f"{table}.{column}: {count}")

    print("\n=== VALUE COMPATIBILITY ===")
    invalid_pricing = cur.execute(
        """
        SELECT COUNT(*)
        FROM tools
        WHERE pricing_model IS NOT NULL
          AND TRIM(pricing_model) <> ''
          AND LOWER(TRIM(pricing_model)) NOT IN ('kostenlos', 'freemium', 'kostenpflichtig')
        """
    ).fetchone()[0]
    invalid_skill = cur.execute(
        """
        SELECT COUNT(*)
        FROM tools
        WHERE skill_requirement IS NOT NULL
          AND TRIM(skill_requirement) <> ''
                    AND LOWER(REPLACE(TRIM(skill_requirement), 'ä', 'a')) NOT IN ('anfaenger', 'anfanger', 'einsteiger', 'fortgeschritten', 'experte')
        """
    ).fetchone()[0]
    bad_url = cur.execute(
        """
        SELECT COUNT(*)
        FROM tools
        WHERE url IS NOT NULL
          AND TRIM(url) <> ''
          AND LOWER(url) NOT LIKE 'http%'
        """
    ).fetchone()[0]
    print(f"invalid_pricing_model: {invalid_pricing}")
    print(f"invalid_skill_requirement: {invalid_skill}")
    print(f"bad_url: {bad_url}")

    dup_count = cur.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT LOWER(TRIM(name)) AS n
            FROM tools
            GROUP BY LOWER(TRIM(name))
            HAVING COUNT(*) > 1
        ) d
        """
    ).fetchone()[0]
    print(f"duplicate_tool_names: {dup_count}")


def apply_fixes(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    counters: Counter[str] = Counter()

    # Fill missing domain descriptions/tags
    domains = cur.execute("SELECT id, name, description, tags FROM domain").fetchall()
    for row in domains:
        updates = {}
        if not norm_text(row["description"]):
            updates["description"] = f"Fokusbereich fuer {row['name']} im FlowAI-Wissensmodell."
        if not norm_text(row["tags"]):
            updates["tags"] = make_tags_from_text(row["name"], row["description"])
        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [row["id"]]
            cur.execute(f"UPDATE domain SET {set_clause} WHERE id = ?", values)
            counters["domains_updated"] += 1

    # Fix workflow_categories domain/tags/description
    categories = cur.execute("SELECT id, name, domain_id, tags, description FROM workflow_categories").fetchall()
    domain_lookup = {
        row["name"]: row["id"] for row in cur.execute("SELECT id, name FROM domain").fetchall()
    }
    for row in categories:
        updates = {}
        if row["domain_id"] is None:
            inferred = infer_domain_from_category(row["name"])
            domain_id = domain_lookup.get(inferred)
            if domain_id:
                updates["domain_id"] = domain_id
        if not norm_text(row["tags"]):
            updates["tags"] = make_tags_from_text(row["name"])
        if not norm_text(row["description"]):
            updates["description"] = f"Aufgaben und Workflows rund um {row['name']}."

        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [row["id"]]
            cur.execute(f"UPDATE workflow_categories SET {set_clause} WHERE id = ?", values)
            counters["workflow_categories_updated"] += 1

    # Fill subcategory descriptions
    subcats = cur.execute("SELECT id, name, description FROM sub_categories").fetchall()
    for row in subcats:
        if not norm_text(row["description"]):
            cur.execute(
                "UPDATE sub_categories SET description = ? WHERE id = ?",
                (f"Spezialisierte Aufgaben im Bereich {row['name']}.", row["id"]),
            )
            counters["sub_categories_updated"] += 1

    # Fill template text fields
    templates = cur.execute(
        "SELECT id, title, description, example_input, tags FROM task_templates"
    ).fetchall()
    for row in templates:
        updates = {}
        if not norm_text(row["description"]):
            updates["description"] = f"Vorlage fuer: {row['title']}"
        if not norm_text(row["example_input"]):
            updates["example_input"] = row["title"]
        if not norm_text(row["tags"]):
            updates["tags"] = make_tags_from_text(row["title"], row["description"])
        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [row["id"]]
            cur.execute(f"UPDATE task_templates SET {set_clause} WHERE id = ?", values)
            counters["task_templates_updated"] += 1

    # Fill and normalize tool fields
    tools = cur.execute(
        """
        SELECT id, name, category, domain, tags, use_case, platform, pricing_model, url,
               skill_requirement, best_for, is_free
        FROM tools
        """
    ).fetchall()
    for row in tools:
        updates = {}
        inferred_domain = infer_domain_from_category(row["category"])
        if not norm_text(row["domain"]):
            updates["domain"] = inferred_domain
        if not norm_text(row["tags"]):
            updates["tags"] = make_tags_from_text(row["name"], row["category"], inferred_domain)
        if not norm_text(row["use_case"]):
            updates["use_case"] = f"Nutzung fuer Aufgaben im Bereich {row['category']}."
        if not norm_text(row["platform"]):
            updates["platform"] = "web"
        if not norm_text(row["pricing_model"]):
            updates["pricing_model"] = normalize_pricing("", int(row["is_free"] or 0))
        else:
            normalized_pricing = normalize_pricing(row["pricing_model"], int(row["is_free"] or 0))
            if normalized_pricing != norm_text(row["pricing_model"]).lower():
                updates["pricing_model"] = normalized_pricing
        if not norm_text(row["url"]):
            updates["url"] = "https://example.com"
        elif not norm_text(row["url"]).lower().startswith("http"):
            updates["url"] = f"https://{norm_text(row['url']).lstrip('/')}"
        if not norm_text(row["skill_requirement"]):
            updates["skill_requirement"] = "Anfaenger"
        else:
            updates["skill_requirement"] = normalize_skill(row["skill_requirement"])
        if not norm_text(row["best_for"]):
            updates["best_for"] = f"Aufgaben in {row['category']}"

        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [row["id"]]
            cur.execute(f"UPDATE tools SET {set_clause} WHERE id = ?", values)
            counters["tools_updated"] += 1

    conn.commit()
    print("=== FIX SUMMARY ===")
    for key in [
        "domains_updated",
        "workflow_categories_updated",
        "sub_categories_updated",
        "task_templates_updated",
        "tools_updated",
    ]:
        print(f"{key}: {counters.get(key, 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Data quality check and optional fix for FlowAI DB.")
    parser.add_argument("--fix", action="store_true", help="Apply automatic quality fixes")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        print_audit(conn)
        if args.fix:
            apply_fixes(conn)
            print("\n=== POST-FIX AUDIT ===")
            print_audit(conn)


if __name__ == "__main__":
    main()
