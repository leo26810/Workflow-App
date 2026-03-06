import argparse
import json
import sys, os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app_factory import create_app
from extensions import db
from models import Domain, SubCategory, TaskTemplate, Tool, WorkflowCategory


def _normalize_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        clean = value.strip()
        return clean if clean else None
    return str(value).strip() or None


def _to_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in {'true', '1', 'yes', 'ja', 'y'}:
            return True
        if clean in {'false', '0', 'no', 'nein', 'n'}:
            return False
    return bool(value)


def _to_float(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('JSON root muss ein Objekt sein.')

    if 'domain' in payload and payload['domain'] is not None and not isinstance(payload['domain'], dict):
        raise ValueError('"domain" muss ein Objekt sein.')

    categories = payload.get('categories', [])
    if categories is None:
        categories = []
    if not isinstance(categories, list):
        raise ValueError('"categories" muss ein Array sein.')

    for category in categories:
        if not isinstance(category, dict):
            raise ValueError('Jeder Kategorie-Eintrag muss ein Objekt sein.')
        if not _normalize_text(category.get('name')):
            raise ValueError('Jede Kategorie braucht ein nicht-leeres Feld "name".')

        subcategories = category.get('subcategories', [])
        if subcategories is None:
            subcategories = []
        if not isinstance(subcategories, list):
            raise ValueError(f'Subcategories von Kategorie {category.get("name")} muessen ein Array sein.')

        for subcategory in subcategories:
            if not isinstance(subcategory, dict):
                raise ValueError('Jeder SubCategory-Eintrag muss ein Objekt sein.')
            if not _normalize_text(subcategory.get('name')):
                raise ValueError('Jede Unterkategorie braucht ein nicht-leeres Feld "name".')

            templates = subcategory.get('task_templates', [])
            if templates is None:
                templates = []
            if not isinstance(templates, list):
                raise ValueError(f'Task templates von Unterkategorie {subcategory.get("name")} muessen ein Array sein.')

            for template in templates:
                if not isinstance(template, dict):
                    raise ValueError('Jedes TaskTemplate muss ein Objekt sein.')
                if not _normalize_text(template.get('title')):
                    raise ValueError('Jedes TaskTemplate braucht ein nicht-leeres Feld "title".')

    tools = payload.get('tools', [])
    if tools is None:
        tools = []
    if not isinstance(tools, list):
        raise ValueError('"tools" muss ein Array sein.')

    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError('Jeder Tool-Eintrag muss ein Objekt sein.')
        if not _normalize_text(tool.get('name')):
            raise ValueError('Jedes Tool braucht ein nicht-leeres Feld "name".')


def import_payload(payload, counters):
    domain_map = {}

    try:
        domain_data = payload.get('domain') or None
        root_domain_name = None

        if isinstance(domain_data, dict):
            root_domain_name = _normalize_text(domain_data.get('name'))
            if root_domain_name:
                domain = Domain.query.filter_by(name=root_domain_name).first()
                is_new = domain is None
                if is_new:
                    domain = Domain()
                    domain.name = root_domain_name
                    db.session.add(domain)
                    counters['new_domains'] += 1
                    status = 'neu'
                else:
                    counters['updated_domains'] += 1
                    status = 'aktualisiert'

                domain.icon = _normalize_text(domain_data.get('icon'))
                domain.description = _normalize_text(domain_data.get('description'))
                domain.tags = _normalize_text(domain_data.get('tags'))
                sort_order = domain_data.get('sort_order')
                domain.sort_order = int(sort_order) if isinstance(sort_order, int) else (domain.sort_order or 0)
                db.session.flush()

                domain_map[root_domain_name] = domain
                print(f'  ✅ Domain: {root_domain_name} ({status})')

        for category_data in payload.get('categories', []) or []:
            category_name = _normalize_text(category_data.get('name'))
            if not category_name:
                continue

            category = WorkflowCategory.query.filter_by(name=category_name).first()
            category_new = category is None
            if category_new:
                category = WorkflowCategory()
                category.name = category_name
                counters['new_categories'] += 1
                status = 'neu'
                db.session.add(category)
            else:
                status = 'aktualisiert'

            assert category is not None

            category.icon = _normalize_text(category_data.get('icon')) or category.icon or '📁'
            category.description = _normalize_text(category_data.get('description'))
            category.tags = _normalize_text(category_data.get('tags'))

            category_domain_name = _normalize_text(category_data.get('domain')) or root_domain_name
            if category_domain_name:
                linked_domain = domain_map.get(category_domain_name)
                if linked_domain is None:
                    linked_domain = Domain.query.filter_by(name=category_domain_name).first()
                    if linked_domain:
                        domain_map[category_domain_name] = linked_domain
                category.domain_id = linked_domain.id if linked_domain else None
                domain_label = category_domain_name
            else:
                domain_label = 'ohne Domain'

            print(f'  ✅ Kategorie: {category_name} → {domain_label} ({status})')

            db.session.flush()

            for subcategory_data in category_data.get('subcategories', []) or []:
                subcategory_name = _normalize_text(subcategory_data.get('name'))
                if not subcategory_name:
                    continue

                subcategory = SubCategory.query.filter_by(name=subcategory_name, category_id=category.id).first()
                subcategory_new = subcategory is None
                if subcategory_new:
                    subcategory = SubCategory()
                    subcategory.name = subcategory_name
                    subcategory.category_id = category.id
                    counters['new_subcategories'] += 1
                    status = 'neu'
                    db.session.add(subcategory)
                else:
                    status = 'aktualisiert'

                assert subcategory is not None

                subcategory.description = _normalize_text(subcategory_data.get('description'))
                print(f'  ✅ Unterkategorie: {subcategory_name} ({status})')

                db.session.flush()

                for template_data in subcategory_data.get('task_templates', []) or []:
                    template_title = _normalize_text(template_data.get('title'))
                    if not template_title:
                        continue

                    template = TaskTemplate.query.filter_by(title=template_title, subcategory_id=subcategory.id).first()
                    template_new = template is None
                    if template_new:
                        template = TaskTemplate()
                        template.title = template_title
                        template.subcategory_id = subcategory.id
                        counters['new_templates'] += 1
                        status = 'neu'
                        db.session.add(template)
                    else:
                        status = 'aktualisiert'

                    assert template is not None

                    template.description = _normalize_text(template_data.get('description'))
                    template.example_input = _normalize_text(template_data.get('example_input'))
                    template.tags = _normalize_text(template_data.get('tags'))
                    print(f'  ✅ Template: {template_title} ({status})')

        for tool_data in payload.get('tools', []) or []:
            tool_name = _normalize_text(tool_data.get('name'))
            if not tool_name:
                continue

            tool = Tool.query.filter(db.func.lower(Tool.name) == tool_name.lower()).first()
            tool_new = tool is None
            if tool_new:
                tool = Tool()
                tool.name = tool_name
                db.session.add(tool)
                counters['new_tools'] += 1
                status = 'neu'
            else:
                counters['updated_tools'] += 1
                status = 'aktualisiert'

            assert tool is not None

            tool.name = tool_name
            tool.domain = _normalize_text(tool_data.get('domain'))
            tool.category = _normalize_text(tool_data.get('category')) or 'Allgemein'
            tool.tags = _normalize_text(tool_data.get('tags'))
            tool.url = _normalize_text(tool_data.get('url'))
            tool.best_for = _normalize_text(tool_data.get('best_for'))
            tool.use_case = _normalize_text(tool_data.get('use_case'))
            tool.platform = _normalize_text(tool_data.get('platform'))
            tool.pricing_model = _normalize_text(tool_data.get('pricing_model'))
            tool.is_free = _to_bool(tool_data.get('is_free'), default=True)
            tool.skill_requirement = _normalize_text(tool_data.get('skill_requirement'))
            tool.rating = _to_float(tool_data.get('rating'))
            tool.notes = _normalize_text(tool_data.get('notes'))
            tool.free_tier_details = _normalize_text(tool_data.get('free_tier_details'))
            tool.prompt_template = _normalize_text(tool_data.get('prompt_template'))

            print(f'  ✅ Tool: {tool_name} ({status})')

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _print_summary(counters):
    print('  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print('  Import abgeschlossen:')
    print(f"  Domains:       {counters['new_domains']} neu, {counters['updated_domains']} aktualisiert")
    print(f"  Kategorien:    {counters['new_categories']} neu")
    print(f"  Unterkategorien: {counters['new_subcategories']} neu")
    print(f"  Templates:     {counters['new_templates']} neu")
    print(f"  Tools:         {counters['new_tools']} neu, {counters['updated_tools']} aktualisiert")
    print('  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')


def _resolve_input_files(file_arg, dir_arg):
    if file_arg:
        path = Path(file_arg).expanduser()
        if not path.is_absolute():
            path = (Path(__file__).resolve().parent.parent / path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f'Datei nicht gefunden: {file_arg}')
        if path.suffix.lower() != '.json':
            raise ValueError(f'Datei ist keine JSON-Datei: {path}')
        return [path]

    directory = Path(dir_arg).expanduser()
    if not directory.is_absolute():
        directory = (Path(__file__).resolve().parent.parent / directory).resolve()
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f'Ordner nicht gefunden: {dir_arg}')

    files = sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == '.json'])
    return files


def main():
    parser = argparse.ArgumentParser(description='Importiert Wissensdaten (Domains, Kategorien, Tools) aus JSON-Dateien.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', dest='file_path', help='Importiert eine einzelne JSON-Datei')
    group.add_argument('--dir', dest='dir_path', help='Importiert alle .json-Dateien aus einem Ordner')
    parser.add_argument('--dry-run', action='store_true', help='Validiert JSON-Dateien ohne Import in die Datenbank')
    args = parser.parse_args()

    try:
        input_files = _resolve_input_files(args.file_path, args.dir_path)
    except Exception as exc:
        print(f'❌ {exc}')
        raise SystemExit(1)

    if not input_files:
        print('⚠️ Keine JSON-Dateien gefunden. Nichts zu importieren.')
        raise SystemExit(0)

    app = create_app()

    counters = {
        'new_domains': 0,
        'updated_domains': 0,
        'new_categories': 0,
        'new_subcategories': 0,
        'new_templates': 0,
        'new_tools': 0,
        'updated_tools': 0,
    }

    for json_file in input_files:
        print(f'\n📄 Verarbeite: {json_file}')
        try:
            payload = json.loads(json_file.read_text(encoding='utf-8'))
            validate_payload(payload)

            if args.dry_run:
                print('  ✅ Dry-Run: JSON ist valide, kein Import ausgeführt.')
                continue

            with app.app_context():
                import_payload(payload, counters)

        except Exception as exc:
            print(f'  ❌ Fehler in {json_file.name}: {exc}')
            if not args.dry_run:
                with app.app_context():
                    db.session.rollback()
            raise SystemExit(1)

    if args.dry_run:
        print('\n✅ Dry-Run abgeschlossen.')
        return

    print()
    _print_summary(counters)


if __name__ == '__main__':
    main()
