import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from models import db, PromptTemplate, Tool

BASE_DIR = Path(__file__).resolve().parent
CUSTOM_DATA_DIR: Path | None = None


def resolve_json_path(file_name: str) -> Path | None:
    candidates = [
        CUSTOM_DATA_DIR / file_name if CUSTOM_DATA_DIR else None,
        PROJECT_ROOT / file_name,
        BACKEND_DIR / file_name,
        BASE_DIR / file_name,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        if candidate.exists():
            return candidate
    return None


def load_json(file_name: str, required: bool = False):
    path = resolve_json_path(file_name)
    if path is None:
        if required:
            raise FileNotFoundError(f"JSON-Datei nicht gefunden: {file_name}")
        print(f"⚠️ Übersprungen (nicht gefunden): {file_name}")
        return []
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in {"true", "1", "yes", "ja"}:
            return True
        if clean in {"false", "0", "no", "nein"}:
            return False
    return bool(value)


def format_alternatives(value) -> str:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(parts)
    return str(value).strip() if value is not None else ""


def append_extra_notes(base_notes: str, item: dict) -> str:
    workflow = str(item.get("workflow_integration") or "").strip()
    schueler_usecase = str(item.get("schueler_usecase") or "").strip()
    alternatives = format_alternatives(item.get("alternatives"))

    if not workflow and not schueler_usecase and not alternatives:
        return base_notes

    extra_block = (
        f"Workflow: {workflow}\n"
        f"Schüler-Usecase: {schueler_usecase}\n"
        f"Alternativen: {alternatives}"
    )

    if base_notes:
        if extra_block in base_notes:
            return base_notes
        return f"{base_notes}\n\n{extra_block}"

    return extra_block


def import_data() -> None:
    counters = {
        "tools_vervollständigt": 0,
        "tools_neu": 0,
        "tools_updated": 0,
        "prompt_templates_neu": 0,
        "prompt_templates_updated": 0,
        "fehler": 0,
    }

    with app.app_context():
        # Datei 1: tool_vervollständigung.json (nur Updates bei exaktem Name-Match)
        tool_vervoll_data = load_json("tool_vervollständigung.json")
        update_fields = [
            "skill_requirement",
            "best_for",
            "free_tier_details",
            "prompt_template",
            "category",
        ]

        for entry in tool_vervoll_data:
            try:
                name = str(entry.get("name") or "").strip()
                if not name:
                    raise ValueError("tool_vervollständigung: name fehlt")

                tool = Tool.query.filter_by(name=name).first()
                if not tool:
                    continue

                has_any_field = False
                for field_name in update_fields:
                    if field_name in entry:
                        setattr(tool, field_name, entry.get(field_name))
                        has_any_field = True

                if has_any_field:
                    db.session.commit()
                    counters["tools_vervollständigt"] += 1
            except Exception:
                db.session.rollback()
                counters["fehler"] += 1

        # Datei 2: Tools.json (update oder insert)
        tools_data = load_json("Tools.json")
        tool_fields = [
            "name",
            "category",
            "url",
            "is_free",
            "free_tier_details",
            "skill_requirement",
            "best_for",
            "notes",
            "prompt_template",
        ]

        for entry in tools_data:
            try:
                name = str(entry.get("name") or "").strip()
                if not name:
                    raise ValueError("Tools.json: name fehlt")

                tool = Tool.query.filter_by(name=name).first()
                is_new = tool is None

                if is_new:
                    tool = Tool()
                    tool.name = name
                    tool.category = "Allgemein"
                    db.session.add(tool)

                if tool is None:
                    raise RuntimeError("Tool konnte nicht initialisiert werden")

                for field_name in tool_fields:
                    if field_name == "name":
                        setattr(tool, "name", name)
                    elif field_name == "is_free":
                        setattr(tool, "is_free", to_bool(entry.get("is_free", True)))
                    elif field_name == "category":
                        setattr(tool, "category", str(entry.get("category") or "Allgemein").strip() or "Allgemein")
                    else:
                        setattr(tool, field_name, entry.get(field_name))

                db.session.commit()
                if is_new:
                    counters["tools_neu"] += 1
                else:
                    counters["tools_updated"] += 1
            except Exception:
                db.session.rollback()
                counters["fehler"] += 1

        # Datei 3: tools_database.json (update oder insert + Zusatzfelder an notes anhängen)
        tools_database_data = load_json("tools_database.json")

        for entry in tools_database_data:
            try:
                name = str(entry.get("name") or "").strip()
                if not name:
                    raise ValueError("tools_database.json: name fehlt")

                tool = Tool.query.filter_by(name=name).first()
                is_new = tool is None

                if is_new:
                    tool = Tool()
                    tool.name = name
                    tool.category = "Allgemein"
                    db.session.add(tool)

                if tool is None:
                    raise RuntimeError("Tool konnte nicht initialisiert werden")

                base_notes = entry.get("notes")
                if base_notes is None and not is_new:
                    base_notes = tool.notes
                base_notes = str(base_notes or "").strip()

                merged_notes = append_extra_notes(base_notes, entry)

                tool.name = name
                tool.category = str(entry.get("category") or "Allgemein").strip() or "Allgemein"
                tool.url = entry.get("url")
                tool.is_free = to_bool(entry.get("is_free", True))
                tool.free_tier_details = entry.get("free_tier_details")
                tool.skill_requirement = entry.get("skill_requirement")
                tool.best_for = entry.get("best_for")
                tool.notes = merged_notes
                tool.prompt_template = entry.get("prompt_template")

                db.session.commit()
                if is_new:
                    counters["tools_neu"] += 1
                else:
                    counters["tools_updated"] += 1
            except Exception:
                db.session.rollback()
                counters["fehler"] += 1

        # Datei 4: prompt_templates.json (update oder insert nach title)
        prompt_templates_data = load_json("prompt_templates.json")

        for entry in prompt_templates_data:
            try:
                title = str(entry.get("title") or "").strip()
                if not title:
                    raise ValueError("prompt_templates.json: title fehlt")

                category = str(entry.get("category") or "Allgemein").strip() or "Allgemein"
                prompt_text = str(entry.get("prompt_text") or "").strip()
                use_case = str(entry.get("use_case") or "").strip()

                if use_case:
                    final_prompt_text = f"Anwendungsfall: {use_case}\n\n{prompt_text}"
                else:
                    final_prompt_text = prompt_text

                if not final_prompt_text:
                    raise ValueError(f"prompt_templates.json: prompt_text fehlt ({title})")

                template = PromptTemplate.query.filter_by(title=title).first()
                is_new = template is None

                if is_new:
                    template = PromptTemplate()
                    template.title = title
                    template.category = category
                    template.prompt_text = final_prompt_text
                    template.tool_id = None
                    db.session.add(template)
                else:
                    if template is None:
                        raise RuntimeError("PromptTemplate konnte nicht initialisiert werden")
                    template.title = title
                    template.category = category
                    template.prompt_text = final_prompt_text
                    template.tool_id = None

                db.session.commit()
                if is_new:
                    counters["prompt_templates_neu"] += 1
                else:
                    counters["prompt_templates_updated"] += 1
            except Exception:
                db.session.rollback()
                counters["fehler"] += 1

    print(f"tools_vervollständigt: {counters['tools_vervollständigt']}")
    print(f"tools_neu: {counters['tools_neu']}")
    print(f"tools_updated: {counters['tools_updated']}")
    print(f"prompt_templates_neu: {counters['prompt_templates_neu']}")
    print(f"prompt_templates_updated: {counters['prompt_templates_updated']}")
    print(f"fehler: {counters['fehler']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Importiert Tool- und Prompt-Daten aus JSON-Dateien.')
    parser.add_argument('--data-dir', dest='data_dir', default=None, help='Optionaler Ordner mit JSON-Dateien')
    args = parser.parse_args()

    if args.data_dir:
        candidate_dir = Path(args.data_dir).expanduser()
        if not candidate_dir.is_absolute():
            candidate_dir = (PROJECT_ROOT / candidate_dir).resolve()
        if not candidate_dir.exists() or not candidate_dir.is_dir():
            print(f"⚠️ Datenordner nicht gefunden: {args.data_dir}")
            raise SystemExit(1)
        CUSTOM_DATA_DIR = candidate_dir

    import_data()
