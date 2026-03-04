import json
from pathlib import Path

from app import app
from models import db, Tool


def import_tools(json_path: Path) -> tuple[int, int, int]:
    with json_path.open('r', encoding='utf-8') as file:
        payload = json.load(file)

    added = 0
    updated = 0
    skipped = 0

    with app.app_context():
        existing = {tool.name.strip().lower(): tool for tool in Tool.query.all() if tool.name}

        for item in payload:
            name = (item.get('name') or '').strip()
            if not name:
                skipped += 1
                continue

            category = (item.get('category') or 'Allgemein').strip() or 'Allgemein'
            url = (item.get('url') or '').strip()

            notes_parts = []
            base_notes = (item.get('notes') or '').strip()
            if base_notes:
                notes_parts.append(base_notes)

            for key, label in [
                ('free_tier_details', 'Free Tier'),
                ('best_for', 'Best For'),
                ('skill_requirement', 'Skill Level'),
                ('workflow_integration', 'Workflow'),
                ('schueler_usecase', 'Schüler-Usecase'),
                ('prompt_template', 'Prompt-Template'),
            ]:
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    notes_parts.append(f"{label}: {value.strip()}")

            alternatives = item.get('alternatives')
            if isinstance(alternatives, list) and alternatives:
                cleaned = ', '.join(str(entry).strip() for entry in alternatives if str(entry).strip())
                if cleaned:
                    notes_parts.append(f"Alternativen: {cleaned}")

            final_notes = '\n\n'.join(notes_parts).strip()
            key = name.lower()

            if key in existing:
                tool = existing[key]
                tool.category = category
                tool.url = url
                tool.notes = final_notes[:1000] if final_notes else ''
                updated += 1
            else:
                tool = Tool(
                    name=name,
                    category=category,
                    url=url,
                    notes=final_notes[:1000] if final_notes else '',
                )
                db.session.add(tool)
                existing[key] = tool
                added += 1

        db.session.commit()

    return added, updated, skipped


if __name__ == '__main__':
    json_file = Path(__file__).with_name('tools_database.json')
    if not json_file.exists():
        raise FileNotFoundError(f'JSON-Datei nicht gefunden: {json_file}')

    added_count, updated_count, skipped_count = import_tools(json_file)
    print(
        f'Import abgeschlossen: added={added_count}, updated={updated_count}, skipped={skipped_count}'
    )
