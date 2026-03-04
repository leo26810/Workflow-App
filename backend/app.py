"""
app.py - Flask Backend für die Workflow-Optimierungs-App
REST-API mit Endpunkten für Profil und KI-Empfehlungen
"""

import os
import json
import time
import threading
import queue
import html
from typing import Any, TypeVar
from datetime import datetime
import requests
from functools import lru_cache, wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_compress import Compress
from dotenv import load_dotenv
from models import (
    db,
    User,
    Skill,
    Goal,
    Tool,
    ToolUsageLog,
    WorkflowHistory,
    WorkflowCategory,
    SubCategory,
    TaskTemplate,
    UserContext,
    ResearchSession,
    SchoolProject,
    seed_extended_data,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Flask App initialisieren
app = Flask(__name__)
Compress(app)  # Schritt: Aktiviert Response-Compression für alle API-Antworten.

# CORS aktivieren, damit das React-Frontend Anfragen stellen kann
cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000')
CORS(app, origins=[origin.strip() for origin in cors_origins.split(',') if origin.strip()])

# Datenbank-Konfiguration (SQLite)
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    default_sqlite_path = os.path.join(BASE_DIR, 'instance', 'workflow.db')
    normalized_sqlite_path = default_sqlite_path.replace('\\', '/')
    database_url = f"sqlite:///{normalized_sqlite_path}"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Groq API Konfiguration (kostenlose LLM-API)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

TELEGRAM_BOT_TOKEN = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
TELEGRAM_WEBHOOK_SECRET = (os.environ.get('TELEGRAM_WEBHOOK_SECRET') or '').strip()
TELEGRAM_ALLOWED_CHAT_IDS = (os.environ.get('TELEGRAM_ALLOWED_CHAT_IDS') or '').strip()
TELEGRAM_WEBHOOK_PATH = '/api/telegram/webhook'
TELEGRAM_API_BASE = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}' if TELEGRAM_BOT_TOKEN else ''
TELEGRAM_WEBHOOK_BASE_URL = (os.environ.get('TELEGRAM_WEBHOOK_BASE_URL') or '').strip().rstrip('/')
TELEGRAM_MODE = (os.environ.get('TELEGRAM_MODE') or 'webhook').strip().lower()
if TELEGRAM_MODE not in {'webhook', 'polling'}:
    TELEGRAM_MODE = 'webhook'


def parse_allowed_chat_ids(raw_value: str) -> set[int]:
    ids = set()
    if not raw_value:
        return ids

    for token in raw_value.split(','):
        token = token.strip()
        if not token:
            continue
        try:
            ids.add(int(token))
        except ValueError:
            app.logger.warning(f'Telegram config: invalid chat id ignored: {token}')
    return ids


ALLOWED_CHAT_IDS = parse_allowed_chat_ids(TELEGRAM_ALLOWED_CHAT_IDS)
telegram_update_queue = queue.Queue(maxsize=500)
telegram_worker_started = False
telegram_receiver_started = False
telegram_worker_lock = threading.Lock()
telegram_receiver_lock = threading.Lock()
telegram_processed_updates = {}
telegram_processed_lock = threading.Lock()
TELEGRAM_UPDATE_TTL_SECONDS = 600

# Datenbank mit App verbinden
db.init_app(app)

ModelT = TypeVar('ModelT')


def make_model(model_cls: type[ModelT], **values: Any) -> ModelT:
    instance = model_cls()
    for key, value in values.items():
        setattr(instance, key, value)
    return instance


def ttl_cache(ttl_seconds=300):
    """Schritt: Eigener TTL-Cache-Decorator mit zeitbasiertem Ablauf."""
    def decorator(func):
        cache = {}
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            with lock:
                cached = cache.get(key)
                if cached and now - cached[0] < ttl_seconds:
                    return cached[1]
                if cached:
                    cache.pop(key, None)

            result = func(*args, **kwargs)
            with lock:
                cache[key] = (now, result)
            return result

        def cache_clear():
            with lock:
                cache.clear()
            if hasattr(func, 'cache_clear'):
                func.cache_clear()

        setattr(wrapper, 'cache_clear', cache_clear)
        return wrapper

    return decorator


# Schritt: Request-Dedup-Cache für identische task_description-Anfragen (60 Sekunden).
recommendation_cache = {}
recommendation_cache_lock = threading.Lock()
RECOMMENDATION_DEDUP_TTL = 60


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=128)
def get_tools_page_cached(page: int, limit: int):
    """Schritt: Tool-Datenbank gecacht laden (TTL + LRU), nur bei Bedarf."""
    offset = (page - 1) * limit
    query = Tool.query.order_by(Tool.id.asc())
    total = query.count()
    tools = query.offset(offset).limit(limit).all()
    return {
        'items': [tool.to_dict() for tool in tools],
        'total': total,
    }


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=128)
def get_skills_page_cached(page: int, limit: int):
    """Schritt: Skills gecacht laden (TTL + LRU), nur bei Bedarf."""
    offset = (page - 1) * limit
    query = Skill.query.order_by(Skill.id.asc())
    total = query.count()
    skills = query.offset(offset).limit(limit).all()
    return {
        'items': [skill.to_dict() for skill in skills],
        'total': total,
    }


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=128)
def get_profile_payload_cached(page: int, limit: int):
    """Schritt: /api/profile Antwort gecacht berechnen (TTL 5 Minuten)."""
    user = User.query.first()
    goals = Goal.query.order_by(Goal.id.asc()).all()
    skills_payload = get_skills_page_cached(page, limit)
    tools_payload = get_tools_page_cached(page, limit)

    return {
        'user': user.to_dict() if user else {'name': 'Nutzer'},
        'skills': skills_payload['items'],
        'goals': [goal.to_dict() for goal in goals],
        'tools': tools_payload['items'],
        'pagination': {
            'page': page,
            'limit': limit,
            'skills_total': skills_payload['total'],
            'tools_total': tools_payload['total'],
            'skills_pages': (skills_payload['total'] + limit - 1) // limit,
            'tools_pages': (tools_payload['total'] + limit - 1) // limit,
        }
    }


def clear_data_caches():
    """Schritt: Daten-Caches nach Änderungen invalidieren."""
    get_profile_payload_cached.cache_clear()
    get_tools_page_cached.cache_clear()
    get_skills_page_cached.cache_clear()
    get_tool_scores.cache_clear()


def is_telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET)


def is_chat_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS


def telegram_api_call(method: str, payload: dict, timeout_seconds: int = 20) -> dict:
    if not TELEGRAM_API_BASE:
        raise RuntimeError('Telegram API nicht konfiguriert')

    response = requests.post(
        f'{TELEGRAM_API_BASE}/{method}',
        headers={'Content-Type': 'application/json'},
        json=payload,
        timeout=timeout_seconds,
    )

    if response.status_code != 200:
        raise RuntimeError(f'Telegram API Fehler: HTTP {response.status_code}')

    result = response.json()
    if not result.get('ok'):
        raise RuntimeError(f"Telegram API Fehler: {result.get('description', 'Unbekannt')}")
    return result


def send_telegram_message(chat_id: int, text: str, reply_to_message_id=None):
    payload = {
        'chat_id': chat_id,
        'text': (text or '').strip()[:4096],
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    if reply_to_message_id:
        payload['reply_to_message_id'] = reply_to_message_id

    return telegram_api_call('sendMessage', payload)


def format_telegram_recommendation(task_description: str, payload: dict) -> str:
    recommendation = payload.get('recommendation', {}) if isinstance(payload, dict) else {}
    workflow = recommendation.get('workflow') if isinstance(recommendation, dict) else []
    tools = recommendation.get('recommended_tools') if isinstance(recommendation, dict) else []
    next_step = (payload.get('next_step') or recommendation.get('next_step') or '').strip()
    area = (payload.get('area') or '').strip()
    subcategory = (payload.get('subcategory') or '').strip()
    optimized_prompt = (recommendation.get('optimized_prompt') or '').strip()

    lines = []

    if next_step:
        lines.append('<b>Jetzt</b>')
        lines.append(html.escape(next_step[:220]))

    if area or subcategory:
        lines.append('')
        lines.append('<b>Bereich</b>')
        lines.append(f"{html.escape((area or 'n/a')[:80])} | {html.escape((subcategory or 'n/a')[:80])}")

    tool_names = []
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict):
                name = (tool.get('name') or '').strip()
                if name:
                    tool_names.append(name)

    if isinstance(workflow, list) and workflow:
        lines.append('')
        lines.append('<b>Schritte</b>')
        for index, step in enumerate(workflow[:4]):
            step_text = str(step).strip()
            if not step_text:
                continue

            if index < len(tool_names):
                lines.append(
                    f"- {html.escape(step_text[:220])} (Tool: {html.escape(tool_names[index][:60])})"
                )
            else:
                lines.append(f"- {html.escape(step_text[:220])}")

    if optimized_prompt:
        lines.append('')
        lines.append('<b>Prompt</b>')
        lines.append(f"<pre>{html.escape(optimized_prompt[:900])}</pre>")

    return '\n'.join(lines)[:4096]


def remember_processed_update(update_id: int):
    now = time.time()
    with telegram_processed_lock:
        telegram_processed_updates[update_id] = now
        expired = [
            key for key, timestamp in telegram_processed_updates.items()
            if now - timestamp > TELEGRAM_UPDATE_TTL_SECONDS
        ]
        for key in expired:
            telegram_processed_updates.pop(key, None)


def is_duplicate_update(update_id: int) -> bool:
    with telegram_processed_lock:
        return update_id in telegram_processed_updates


def handle_telegram_update(update: dict):
    message = update.get('message') or update.get('edited_message') or {}
    if not message:
        return

    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    text = (message.get('text') or '').strip()
    message_id = message.get('message_id')

    if chat_id is None or not text:
        return

    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        return

    if not is_chat_allowed(chat_id):
        send_telegram_message(chat_id, 'Dieser Chat ist nicht freigeschaltet.', reply_to_message_id=message_id)
        return

    if text.lower() in {'/start', '/help'}:
        help_text = (
            'Sende mir deine Aufgabe als Nachricht.\n'
            'Ich antworte kurz mit Bereich, erstem Schritt und Toolvorschlag.\n\n'
            'Beispiel:\n'
            '"Ich recherchiere zu Kryptologie und brauche belastbare Quellen."'
        )
        send_telegram_message(chat_id, help_text, reply_to_message_id=message_id)
        return

    if text.startswith('/'):
        send_telegram_message(chat_id, 'Unbekannter Befehl. Nutze /help für Hinweise.', reply_to_message_id=message_id)
        return

    try:
        payload = build_recommendation_response(text)
        response_text = format_telegram_recommendation(text, payload)
        send_telegram_message(chat_id, response_text, reply_to_message_id=message_id)
    except Exception as err:
        app.logger.exception(f'Telegram processing failed: {err}')
        send_telegram_message(
            chat_id,
            'Beim Erstellen der Empfehlung ist ein Fehler aufgetreten. Bitte versuche es in 1 Minute erneut.',
            reply_to_message_id=message_id,
        )


def telegram_worker_loop():
    app.logger.info('Telegram worker: started')
    while True:
        update = telegram_update_queue.get()
        try:
            with app.app_context():
                handle_telegram_update(update)
        except Exception as err:
            app.logger.exception(f'Telegram worker unexpected error: {err}')
        finally:
            telegram_update_queue.task_done()


def telegram_polling_loop():
    app.logger.info('Telegram polling receiver: started')
    offset = 0
    backoff_seconds = 1

    while True:
        try:
            response = requests.post(
                f'{TELEGRAM_API_BASE}/getUpdates',
                headers={'Content-Type': 'application/json'},
                json={
                    'offset': offset,
                    'timeout': 25,
                    'allowed_updates': ['message', 'edited_message'],
                },
                timeout=35,
            )

            if response.status_code != 200:
                raise RuntimeError(f'getUpdates HTTP {response.status_code}')

            payload = response.json()
            if not payload.get('ok'):
                raise RuntimeError(payload.get('description', 'getUpdates failed'))

            updates = payload.get('result') or []
            for update in updates:
                update_id = update.get('update_id')
                try:
                    update_id = int(update_id)
                except (TypeError, ValueError):
                    continue

                offset = max(offset, update_id + 1)

                if is_duplicate_update(update_id):
                    continue
                remember_processed_update(update_id)

                try:
                    telegram_update_queue.put(update, timeout=2)
                except queue.Full:
                    app.logger.warning('Telegram polling: queue full, dropping update')

            backoff_seconds = 1
        except Exception as err:
            app.logger.warning(f'Telegram polling receiver error: {err}')
            time.sleep(backoff_seconds)
            backoff_seconds = min(30, backoff_seconds * 2)


def ensure_telegram_receiver_started():
    global telegram_receiver_started
    if not is_telegram_enabled():
        return
    if TELEGRAM_MODE != 'polling':
        return

    with telegram_receiver_lock:
        if telegram_receiver_started:
            return

        try:
            telegram_api_call('deleteWebhook', {'drop_pending_updates': False})
        except Exception as err:
            app.logger.warning(f'Telegram polling: deleteWebhook failed: {err}')

        receiver = threading.Thread(target=telegram_polling_loop, daemon=True, name='telegram-polling-receiver')
        receiver.start()
        telegram_receiver_started = True
        app.logger.info('Telegram polling receiver: initialized')


def ensure_telegram_worker_started():
    global telegram_worker_started
    if not is_telegram_enabled():
        return

    with telegram_worker_lock:
        if telegram_worker_started:
            return

        worker = threading.Thread(target=telegram_worker_loop, daemon=True, name='telegram-worker')
        worker.start()
        telegram_worker_started = True
        app.logger.info('Telegram worker: initialized')

    ensure_telegram_receiver_started()


def seed_database():
    """Befüllt die Datenbank mit Beispieldaten beim ersten Start"""
    # Nur seeden wenn die Tabellen leer sind
    if User.query.first():
        return
    
    # Standard-Nutzer anlegen
    user = make_model(User, name="Mein Profil")
    db.session.add(user)
    
    # Beispiel-Fähigkeiten
    skills = [
        make_model(Skill, name="Python-Grundlagen", level="Fortgeschritten"),
        make_model(Skill, name="Web-Recherche", level="Experte"),
        make_model(Skill, name="Bildbearbeitung", level="Anfänger"),
        make_model(Skill, name="Textschreiben", level="Fortgeschritten"),
        make_model(Skill, name="KI-Prompt-Engineering", level="Anfänger"),
    ]
    for skill in skills:
        db.session.add(skill)
    
    # Beispiel-Ziele
    goals = [
        make_model(Goal, description="Note in Mathe verbessern"),
        make_model(Goal, description="KI-Tools effektiver nutzen lernen"),
        make_model(Goal, description="Schulprojekte schneller abschließen"),
    ]
    for goal in goals:
        db.session.add(goal)
    
    # Nützliche kostenlose Tools
    tools = [
        make_model(
            Tool,
            name="Groq API (Llama 3)",
            category="KI-Textgenerierung",
            url="https://console.groq.com",
            notes="Sehr schnelle kostenlose Text-KI, ideal für Analysen und Schreiben"
        ),
        make_model(
            Tool,
            name="Stable Diffusion (DreamStudio)",
            category="Bilderstellung",
            url="https://dreamstudio.ai",
            notes="Kostenlose Credits für realistische KI-Bilder"
        ),
        make_model(
            Tool,
            name="Perplexity AI",
            category="Internet-Recherche",
            url="https://perplexity.ai",
            notes="KI-gestützte Suchmaschine mit Quellenangaben, kostenlos nutzbar"
        ),
        make_model(
            Tool,
            name="Zotero",
            category="Literaturverwaltung",
            url="https://zotero.org",
            notes="Kostenlose Literaturverwaltung für wissenschaftliche Arbeiten"
        ),
        make_model(
            Tool,
            name="Canva (Free)",
            category="Design & Präsentation",
            url="https://canva.com",
            notes="Kostenlose Designplattform für Präsentationen, Poster, Social Media"
        ),
        make_model(
            Tool,
            name="Anki",
            category="Lernen & Schule",
            url="https://apps.ankiweb.net",
            notes="Kostenlose Lernkarten-App mit intelligentem Wiederholungssystem"
        ),
        make_model(
            Tool,
            name="Wolfram Alpha",
            category="Mathe & Wissenschaft",
            url="https://wolframalpha.com",
            notes="Mächtiges Rechenwerkzeug für Mathematik, Physik, Chemie"
        ),
        make_model(
            Tool,
            name="DeepL",
            category="Übersetzung",
            url="https://deepl.com",
            notes="Hochqualitative kostenlose Übersetzungen"
        ),
        make_model(
            Tool,
            name="Bing Image Creator",
            category="Bilderstellung",
            url="https://www.bing.com/images/create",
            notes="Kostenlose KI-Bildgenerierung via DALL-E, kein Account nötig"
        ),
        make_model(
            Tool,
            name="NotebookLM",
            category="Recherche & Analyse",
            url="https://notebooklm.google.com",
            notes="Google-Tool zum Analysieren und Zusammenfassen von Dokumenten, kostenlos"
        ),
    ]
    for tool in tools:
        db.session.add(tool)
    
    db.session.commit()
    print("✅ Datenbank mit Beispieldaten befüllt.")


# ─────────────────────────────────────────────
# API ENDPUNKTE
# ─────────────────────────────────────────────

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Ruft das Nutzerprofil mit Fähigkeiten, Zielen und Tools ab (mit Pagination + Cache)."""
    # Schritt: Optionale Pagination für Skills/Tools via ?page=1&limit=20.
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    try:
        limit = max(1, min(100, int(request.args.get('limit', 20))))
    except ValueError:
        limit = 20

    return jsonify(get_profile_payload_cached(page, limit))


@app.route('/api/profile', methods=['POST'])
def update_profile():
    """Fügt neue Fähigkeiten und Ziele hinzu oder bearbeitet bestehende"""
    data = request.get_json()
    action = data.get('action')  # 'add_skill', 'delete_skill', 'add_goal', 'delete_goal', 'update_name'
    
    if action == 'add_skill':
        skill = make_model(Skill, name=data['name'], level=data.get('level', 'Anfänger'))
        db.session.add(skill)
        db.session.commit()
        clear_data_caches()
        return jsonify({'success': True, 'skill': skill.to_dict()})
    
    elif action == 'delete_skill':
        skill = Skill.query.get(data['id'])
        if skill:
            db.session.delete(skill)
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})
    
    elif action == 'add_goal':
        goal = make_model(Goal, description=data['description'])
        db.session.add(goal)
        db.session.commit()
        clear_data_caches()
        return jsonify({'success': True, 'goal': goal.to_dict()})
    
    elif action == 'delete_goal':
        goal = Goal.query.get(data['id'])
        if goal:
            db.session.delete(goal)
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})
    
    elif action == 'update_name':
        user = User.query.first()
        if user:
            user.name = data['name']
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})
    
    elif action == 'add_tool':
        tool = make_model(
            Tool,
            name=data['name'],
            category=data.get('category', 'Allgemein'),
            url=data.get('url', ''),
            notes=data.get('notes', '')
        )
        db.session.add(tool)
        db.session.commit()
        clear_data_caches()
        return jsonify({'success': True, 'tool': tool.to_dict()})
    
    elif action == 'delete_tool':
        tool = Tool.query.get(data['id'])
        if tool:
            db.session.delete(tool)
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Unbekannte Aktion'}), 400


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Gibt alle WorkflowCategories mit SubCategories und TaskTemplates zurück."""
    categories = WorkflowCategory.query.order_by(WorkflowCategory.id.asc()).all()
    payload = []

    for category in categories:
        category_payload = category.to_dict()
        category_payload['subcategories'] = []

        subcategories = SubCategory.query.filter_by(category_id=category.id).order_by(SubCategory.id.asc()).all()
        for subcategory in subcategories:
            sub_payload = subcategory.to_dict()
            templates = TaskTemplate.query.filter_by(subcategory_id=subcategory.id).order_by(TaskTemplate.id.asc()).all()
            sub_payload['task_templates'] = [template.to_dict() for template in templates]
            category_payload['subcategories'].append(sub_payload)

        payload.append(category_payload)

    return jsonify(payload)


@app.route('/api/task-templates', methods=['GET'])
def get_task_templates():
    """Gibt Templates für eine Unterkategorie zurück."""
    subcategory_name = (request.args.get('subcategory') or '').strip()
    if not subcategory_name:
        return jsonify({'error': 'Parameter subcategory fehlt'}), 400

    subcategory = SubCategory.query.filter_by(name=subcategory_name).first()
    if not subcategory:
        return jsonify({'error': 'Unterkategorie nicht gefunden'}), 404

    templates = TaskTemplate.query.filter_by(subcategory_id=subcategory.id).order_by(TaskTemplate.id.asc()).all()
    return jsonify({
        'subcategory': subcategory.name,
        'templates': [template.to_dict() for template in templates]
    })


@app.route('/api/research-session', methods=['POST'])
def create_research_session():
    """Speichert eine Recherche-Session (query, sources, summary)."""
    data = request.get_json() or {}

    query = (data.get('query') or '').strip()
    sources = data.get('sources')
    summary = (data.get('summary') or '').strip()
    tags = (data.get('tags') or '').strip()

    if not query:
        return jsonify({'error': 'query ist erforderlich'}), 400
    if not isinstance(sources, list):
        return jsonify({'error': 'sources muss ein JSON-Array sein'}), 400

    session = make_model(
        ResearchSession,
        query=query,
        sources=sources,
        summary=summary,
        tags=tags,
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({'success': True, 'session': session.to_dict()})


@app.route('/api/research-sessions', methods=['GET'])
def get_research_sessions():
    """Gibt alle gespeicherten Recherche-Sessions zurück."""
    sessions = db.session.query(ResearchSession).order_by(ResearchSession.created_at.desc()).all()
    return jsonify([session.to_dict() for session in sessions])


@app.route('/api/school-projects', methods=['GET'])
def get_school_projects():
    """Gibt alle Schulprojekte zurück."""
    projects = SchoolProject.query.order_by(SchoolProject.created_at.desc()).all()
    return jsonify([project.to_dict() for project in projects])


@app.route('/api/school-projects', methods=['POST'])
def upsert_school_project():
    """Projekt anlegen/bearbeiten/löschen über action=add|update|delete."""
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or '').strip().lower()

    if action == 'add':
        deadline_value = (data.get('deadline') or '').strip()
        deadline = None
        if deadline_value:
            try:
                deadline = datetime.strptime(deadline_value, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'deadline muss YYYY-MM-DD sein'}), 400

        project = make_model(
            SchoolProject,
            title=(data.get('title') or '').strip(),
            subject=(data.get('subject') or '').strip(),
            deadline=deadline,
            status=(data.get('status') or 'offen').strip() or 'offen',
            description=(data.get('description') or '').strip(),
            notes=(data.get('notes') or '').strip(),
        )
        if not project.title or not project.subject:
            return jsonify({'error': 'title und subject sind erforderlich'}), 400

        db.session.add(project)
        db.session.commit()
        return jsonify({'success': True, 'project': project.to_dict()})

    if action == 'update':
        project_id_raw = data.get('id')
        if project_id_raw is None:
            return jsonify({'error': 'id muss numerisch sein'}), 400
        try:
            project_id = int(str(project_id_raw).strip())
        except (TypeError, ValueError):
            return jsonify({'error': 'id muss numerisch sein'}), 400

        project = SchoolProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Projekt nicht gefunden'}), 404

        if 'title' in data:
            project.title = (data.get('title') or '').strip()
        if 'subject' in data:
            project.subject = (data.get('subject') or '').strip()
        if 'status' in data:
            project.status = (data.get('status') or 'offen').strip() or 'offen'
        if 'description' in data:
            project.description = (data.get('description') or '').strip()
        if 'notes' in data:
            project.notes = (data.get('notes') or '').strip()
        if 'deadline' in data:
            deadline_value = (data.get('deadline') or '').strip()
            if deadline_value:
                try:
                    project.deadline = datetime.strptime(deadline_value, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'deadline muss YYYY-MM-DD sein'}), 400
            else:
                project.deadline = None

        if not project.title or not project.subject:
            return jsonify({'error': 'title und subject dürfen nicht leer sein'}), 400

        db.session.commit()
        return jsonify({'success': True, 'project': project.to_dict()})

    if action == 'delete':
        project_id_raw = data.get('id')
        if project_id_raw is None:
            return jsonify({'error': 'id muss numerisch sein'}), 400
        try:
            project_id = int(str(project_id_raw).strip())
        except (TypeError, ValueError):
            return jsonify({'error': 'id muss numerisch sein'}), 400

        project = SchoolProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Projekt nicht gefunden'}), 404

        db.session.delete(project)
        db.session.commit()
        return jsonify({'success': True, 'id': project_id})

    return jsonify({'error': 'Unbekannte action. Erlaubt: add, update, delete'}), 400


@app.route('/api/user-context', methods=['GET'])
def get_user_context():
    """Gibt den kompletten UserContext zurück."""
    context_items = UserContext.query.order_by(UserContext.area.asc(), UserContext.key.asc()).all()
    return jsonify([item.to_dict() for item in context_items])


@app.route('/api/user-context', methods=['POST'])
def set_user_context():
    """Setzt Key-Value Paare im UserContext (area + key + value)."""
    data = request.get_json() or {}

    area = (data.get('area') or '').strip()
    key = (data.get('key') or '').strip()
    value = data.get('value')

    if not area or not key:
        return jsonify({'error': 'area und key sind erforderlich'}), 400

    context_item = UserContext.query.filter_by(area=area, key=key).first()
    if not context_item:
        context_item = make_model(UserContext, area=area, key=key, value='' if value is None else str(value))
        db.session.add(context_item)
    else:
        context_item.value = '' if value is None else str(value)

    db.session.commit()
    return jsonify({'success': True, 'item': context_item.to_dict()})


LEVEL_RANK = {
    'Anfänger': 1,
    'Fortgeschritten': 2,
    'Experte': 3,
}

TASK_TYPE_KEYWORDS = {
    'IMAGE': ['bild', 'foto', 'image', 'grafik', 'illustration', 'poster', 'design', 'logo'],
    'RESEARCH': ['recherche', 'quelle', 'quellen', 'fakten', 'hintergrund', 'zusammenhang'],
    'WRITING': ['aufsatz', 'essay', 'text', 'zusammenfassung', 'analyse', 'schreiben', 'gedicht'],
    'MATH': ['mathe', 'gleichung', 'rechnung', 'formel', 'integral', 'ableitung', 'physik'],
    'PRESENTATION': ['präsentation', 'vortrag', 'folien', 'slides', 'referat'],
    'LEARNING': ['lernen', 'klausur', 'prüfung', 'wiederholen', 'lernplan', 'lernkarten'],
    'CODE': ['code', 'python', 'javascript', 'debug', 'bug', 'api', 'programmieren'],
    'TRANSLATION': ['übersetze', 'übersetzung', 'translate', 'deutsch', 'englisch', 'sprache'],
}

TYPE_CATEGORY_HINTS = {
    'IMAGE': ['bild', 'design', 'grafik'],
    'RESEARCH': ['recherche', 'wissen', 'literatur'],
    'WRITING': ['text', 'schreiben', 'übersetzung'],
    'MATH': ['mathe', 'wissenschaft'],
    'PRESENTATION': ['präsentation', 'design'],
    'LEARNING': ['lernen', 'schule', 'lern'],
    'CODE': ['code', 'programm'],
    'TRANSLATION': ['übersetzung', 'text'],
}

AREA_KEYWORDS = {
    'ki_bild': ['bild', 'logo', 'foto', 'illustration', 'zeichnung', 'banner', 'thumbnail', 'poster'],
    'ki_code': ['code', 'programmier', 'script', 'python', 'javascript', 'bug', 'funktion', 'app'],
    'ki_prompt': ['prompt', 'anweisung', 'chatgpt', 'claude', 'formulier'],
    'ki_analyse': ['zusammenfassung', 'analysier', 'erkläre', 'versteh', 'übersetz', 'bewert'],
    'recherche_bild': ['bild suchen', 'foto finden', 'stock', 'bildquelle'],
    'recherche_info': ['recherche', 'informationen', 'suche', 'quellen', 'fakten', 'wer ist', 'was ist'],
    'schule_docs': ['mitschreiben', 'notizen', 'dokument', 'aufsatz', 'essay', 'referat', 'facharbeit'],
    'schule_projekt': ['schulprojekt', 'präsentation', 'vortrag', 'hausaufgabe', 'abgabe'],
    'schule_lernen': ['lernen', 'üben', 'vorbereitung', 'klausur', 'prüfung', 'wiederholen', 'karteikarten'],
    'alltag_planung': ['planung', 'organisieren', 'struktur', 'todo', 'to-do', 'zeitplan', 'wochenplan', 'routine'],
    'alltag_kommunikation': ['email', 'e-mail', 'nachricht', 'kommunikation', 'feedback', 'abstimmung', 'meeting'],
    'alltag_priorisierung': ['priorisierung', 'priorität', 'entscheiden', 'entscheidung', 'fokus', 'dringend', 'wichtig'],
    'karriere_bewerbung': ['bewerbung', 'lebenslauf', 'cv', 'anschreiben', 'portfolio', 'praktikum', 'ferienjob'],
    'karriere_skills': ['weiterbildung', 'roadmap', 'skill', 'karriere', 'zertifikat', 'kurs', 'lernpfad'],
    'karriere_business': ['business', 'geschäftsidee', 'selbstständig', 'freelance', 'angebot', 'kunde', 'crm']
}

AREA_MAPPING = {
    'ki_bild': ('KI-Verwendung', 'Bilderstellung'),
    'ki_code': ('KI-Verwendung', 'Programmierung'),
    'ki_prompt': ('KI-Verwendung', 'Promptgeneration'),
    'ki_analyse': ('KI-Verwendung', 'Analysen & Zusammenfassung'),
    'recherche_bild': ('Internet-Recherche', 'Bildersuche'),
    'recherche_info': ('Internet-Recherche', 'Informationsrecherche'),
    'schule_docs': ('Schule', 'Mitschreiben & Dokumente'),
    'schule_projekt': ('Schule', 'Schulprojekte'),
    'schule_lernen': ('Schule', 'Lernen & Üben'),
    'alltag_planung': ('Alltag & Produktivität', 'Planung & Organisation'),
    'alltag_kommunikation': ('Alltag & Produktivität', 'Kommunikation'),
    'alltag_priorisierung': ('Alltag & Produktivität', 'Entscheidungen & Priorisierung'),
    'karriere_bewerbung': ('Karriere & Zukunft', 'Bewerbung & Portfolio'),
    'karriere_skills': ('Karriere & Zukunft', 'Skills & Weiterbildung'),
    'karriere_business': ('Karriere & Zukunft', 'Business & Selbstständigkeit'),
}

SUBCATEGORY_FALLBACK_KEYWORDS = {
    'Bilderstellung': ['bild', 'grafik', 'cover', 'visual', 'poster', 'illustration'],
    'Programmierung': ['code', 'bug', 'debug', 'script', 'python', 'javascript', 'api'],
    'Promptgeneration': ['prompt', 'anweisung', 'system prompt', 'formulierung'],
    'Analysen & Zusammenfassung': ['analyse', 'zusammenfassung', 'auswertung', 'interpretation'],
    'Bildersuche': ['bildquelle', 'lizenzfrei', 'stockfoto', 'bildersuche'],
    'Informationsrecherche': ['quelle', 'quellen', 'recherche', 'faktencheck', 'literatur'],
    'Mitschreiben & Dokumente': ['notizen', 'mitschrift', 'dokument', 'protokoll'],
    'Schulprojekte': ['projekt', 'team', 'referat', 'präsentation'],
    'Lernen & Üben': ['lernen', 'klausur', 'prüfung', 'üben', 'lernplan'],
    'Planung & Organisation': ['planung', 'organisieren', 'to-do', 'todo', 'zeitplan', 'routine'],
    'Kommunikation': ['email', 'nachricht', 'feedback', 'kommunikation', 'abstimmung'],
    'Entscheidungen & Priorisierung': ['priorisierung', 'priorität', 'entscheiden', 'entscheidung', 'fokus'],
    'Bewerbung & Portfolio': ['bewerbung', 'lebenslauf', 'cv', 'anschreiben', 'portfolio'],
    'Skills & Weiterbildung': ['weiterbildung', 'skill', 'roadmap', 'lernpfad', 'zertifikat'],
    'Business & Selbstständigkeit': ['business', 'selbstständig', 'freelance', 'angebot', 'kunde'],
}


def infer_area_key_from_subcategory_keywords(task_text: str) -> tuple[str | None, int]:
    lowered = (task_text or '').lower()
    best_subcategory = None
    best_score = 0

    for subcategory_name, keywords in SUBCATEGORY_FALLBACK_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_score = score
            best_subcategory = subcategory_name

    if not best_subcategory or best_score <= 0:
        return None, 0

    for area_key, (_, mapped_subcategory) in AREA_MAPPING.items():
        if mapped_subcategory == best_subcategory:
            return area_key, best_score

    return None, 0


def classify_task(task_text: str) -> dict:
    lowered = (task_text or '').lower()
    scores = {task_type: 0 for task_type in TASK_TYPE_KEYWORDS}

    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        scores[task_type] = hits

    if any(token in lowered for token in ['def ', 'function', 'class ', 'traceback', 'error', 'exception']):
        scores['CODE'] += 2

    if any(token in lowered for token in ['folien', 'slides', 'pitch deck']):
        scores['PRESENTATION'] += 1

    area_scores = {}
    for area_key, keywords in AREA_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        area_scores[area_key] = hits

    best_area_key = max(area_scores, key=lambda key: area_scores[key]) if area_scores else None
    best_area_score = area_scores.get(best_area_key, 0) if best_area_key else 0

    fallback_area_key, fallback_area_score = infer_area_key_from_subcategory_keywords(task_text)
    if fallback_area_key and fallback_area_score > best_area_score:
        best_area_key = fallback_area_key
        best_area_score = fallback_area_score

    best_type = max(scores, key=lambda key: scores[key]) if scores else 'GENERAL'
    best_score = scores.get(best_type, 0)

    if best_score <= 0:
        return {
            'type': 'GENERAL',
            'confidence': 0.3,
            'area_key': best_area_key or 'schule_lernen',
            'area': AREA_MAPPING.get(best_area_key or 'schule_lernen', ('Schule', 'Lernen & Üben'))[0],
            'subcategory': AREA_MAPPING.get(best_area_key or 'schule_lernen', ('Schule', 'Lernen & Üben'))[1],
        }

    confidence = min(1.0, 0.3 + 0.1 * best_score + 0.08 * best_area_score)
    if best_area_score <= 0 or best_area_key not in AREA_MAPPING:
        best_area_key = 'schule_lernen'

    area_name, subcategory_name = AREA_MAPPING.get(best_area_key, ('Schule', 'Lernen & Üben'))
    return {
        'type': best_type,
        'confidence': round(confidence, 2),
        'area_key': best_area_key,
        'area': area_name,
        'subcategory': subcategory_name,
    }


def get_specialized_sub_prompt(area_key: str) -> str:
    specialized_prompts = {
        'ki_bild': (
            'Spezialfokus KI-Bild: Erstelle konkrete Prompt-Bausteine für Bildgeneratoren inkl. Style-Keywords, '\
            'Komposition, Licht, Kamera/Perspektive und negative prompts.'
        ),
        'ki_code': (
            'Spezialfokus KI-Code: Liefere Debugging-Schritte, Erklärungen in Lernreihenfolge, Testideen und nenne passende '\
            'KI-Tools für Code-Unterstützung.'
        ),
        'ki_prompt': (
            'Spezialfokus Promptgeneration: Formuliere präzise Prompt-Frameworks mit Ziel, Kontext, Output-Format und Qualitätskriterien.'
        ),
        'ki_analyse': (
            'Spezialfokus Analyse/Zusammenfassung: Gib Struktur für Zusammenfassungen, zentrale Kriterien und verständliche Erklärstufen.'
        ),
        'recherche_bild': (
            'Spezialfokus Recherche-Bild: Zeige Suchstrategie für Bildquellen, Lizenzprüfung und richtige Quellenangabe.'
        ),
        'recherche_info': (
            'Spezialfokus Recherche-Info: Zeige Suchstrategie, Query-Varianten, Quellenbewertung und welche Suchmaschinen wofür geeignet sind.'
        ),
        'schule_docs': (
            'Spezialfokus Schule-Dokumente: Arbeite mit klarer Gliederung, sauberer Formatierung und passendem Zitierstil.'
        ),
        'schule_projekt': (
            'Spezialfokus Schule-Projekt: Baue Zeitplanung mit Meilensteinen, Aufgabenaufteilung im Team und Präsentationstipps ein.'
        ),
        'schule_lernen': (
            'Spezialfokus Schule-Lernen: Nutze Lernmethoden wie Pomodoro, Spaced Repetition und Lernkarten-Generierung.'
        ),
        'alltag_planung': (
            'Spezialfokus Planung/Organisation: Gib konkrete Zeitblöcke, Prioritäten und einen sofort umsetzbaren Tagesstart.'
        ),
        'alltag_kommunikation': (
            'Spezialfokus Kommunikation: Formuliere klar, kurz und adressatengerecht mit konkreten Vorschlägen für Ton und Struktur.'
        ),
        'alltag_priorisierung': (
            'Spezialfokus Priorisierung: Nutze Kriterien, reduziere Komplexität und leite den wichtigsten nächsten Schritt ab.'
        ),
        'karriere_bewerbung': (
            'Spezialfokus Bewerbung/Portfolio: Liefere präzise Textbausteine, Wirkungskriterien und klare Verbesserungen.'
        ),
        'karriere_skills': (
            'Spezialfokus Skills/Weiterbildung: Erstelle Roadmaps mit Meilensteinen, Übungen und überprüfbaren Ergebnissen.'
        ),
        'karriere_business': (
            'Spezialfokus Business/Selbstständigkeit: Arbeite mit Zielgruppe, Angebotsschärfung und einfachen Validierungsschritten.'
        ),
    }
    return specialized_prompts.get(area_key, specialized_prompts['schule_lernen'])


def get_templates_for_subcategory(subcategory_name: str, limit: int = 5):
    subcategory = SubCategory.query.filter_by(name=subcategory_name).first()
    if not subcategory:
        return []
    templates = TaskTemplate.query.filter_by(subcategory_id=subcategory.id).order_by(TaskTemplate.id.asc()).limit(limit).all()
    return [template.to_dict() for template in templates]


def get_user_context_key_map() -> dict:
    key_map = {}
    context_items = UserContext.query.order_by(UserContext.area.asc(), UserContext.key.asc()).all()
    for item in context_items:
        key_map[item.key] = item.value
    return key_map


def get_frequently_used_tools(limit: int = 3) -> list[str]:
    rows = (
        db.session.query(Tool.name, db.func.count(ToolUsageLog.id).label('usage_count'))
        .join(ToolUsageLog, ToolUsageLog.tool_id == Tool.id)
        .group_by(Tool.id, Tool.name)
        .order_by(db.func.count(ToolUsageLog.id).desc())
        .limit(limit)
        .all()
    )
    return [row.name for row in rows]


def get_low_rated_tools() -> list[str]:
    tools = Tool.query.filter(Tool.rating.isnot(None), Tool.rating < 3).order_by(Tool.rating.asc()).all()
    return [tool.name for tool in tools]


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=16)
def get_tool_scores() -> dict:
    tool_scores = {}

    for tool in Tool.query.all():
        score = 1.0
        if tool.rating is not None:
            if tool.rating < 3:
                score -= 0.3
            elif tool.rating >= 4:
                score += 0.15
        tool_scores[tool.name] = score

    low_rating_counts = {}
    recent_history = WorkflowHistory.query.order_by(WorkflowHistory.created_at.desc()).limit(10).all()

    for history_entry in recent_history:
        rating = history_entry.user_rating
        if rating is None:
            continue

        try:
            recommendation_data = json.loads(history_entry.recommendation_json or '{}')
        except json.JSONDecodeError:
            continue

        recommended_tools = recommendation_data.get('recommended_tools', [])
        recommended_names = []
        for recommended_tool in recommended_tools:
            if isinstance(recommended_tool, dict):
                name = (recommended_tool.get('name') or '').strip()
            elif isinstance(recommended_tool, str):
                name = recommended_tool.strip()
            else:
                name = ''
            if name:
                recommended_names.append(name)

        if not recommended_names:
            continue

        if rating < 3:
            for name in recommended_names:
                tool_scores[name] = tool_scores.get(name, 1.0) - 0.25
                low_rating_counts[name] = low_rating_counts.get(name, 0) + 1
        elif rating >= 4:
            for name in recommended_names:
                tool_scores[name] = tool_scores.get(name, 1.0) + 0.1

    for name, count in low_rating_counts.items():
        if count >= 2:
            tool_scores[name] -= 0.2 * count

    for name in list(tool_scores.keys()):
        tool_scores[name] = round(max(0.1, min(2.5, tool_scores[name])), 2)

    return tool_scores


def get_user_level(skills: list) -> str:
    if not skills:
        return 'Anfänger'

    best_rank = max(LEVEL_RANK.get(skill.level, 1) for skill in skills)
    for level_name, rank_value in LEVEL_RANK.items():
        if rank_value == best_rank:
            return level_name
    return 'Anfänger'


def build_tool_recommendations(tools: list, task_type: str, user_level: str, tool_scores: dict, preferred_names=None, max_count=3):
    preferred_names = preferred_names or []
    preferred_lower = {name.strip().lower() for name in preferred_names if name}

    candidates = []
    challenge_candidates = []

    for tool in tools:
        base_score = tool_scores.get(tool.name, 1.0)
        category_lower = (tool.category or '').lower()

        hints = TYPE_CATEGORY_HINTS.get(task_type, [])
        if any(hint in category_lower for hint in hints):
            base_score += 0.35

        if tool.name.lower() in preferred_lower:
            base_score += 0.3

        required_rank = LEVEL_RANK.get((tool.skill_requirement or '').strip(), 1)
        user_rank = LEVEL_RANK.get(user_level, 1)

        if required_rank == 3 and user_rank == 1:
            challenge_candidates.append((base_score, tool))
            continue

        candidates.append((base_score, tool))

    candidates.sort(key=lambda item: item[0], reverse=True)
    challenge_candidates.sort(key=lambda item: item[0], reverse=True)

    selected = []
    for score, tool in candidates[:max_count]:
        reason = f"Passend für {task_type.lower()}-Aufgaben"
        if score < 0.9:
            reason += ", leicht depriorisiert wegen schwächerem Nutzer-Feedback"
        elif score >= 1.4:
            reason += ", häufig gut bewertet"

        selected.append({
            'name': tool.name,
            'reason': reason,
            'url': tool.url or ''
        })

    if user_level == 'Anfänger' and challenge_candidates:
        _, challenge_tool = challenge_candidates[0]
        selected.append({
            'name': challenge_tool.name,
            'reason': 'Challenge (optional): Experten-Tool zum schrittweisen Aufbauen fortgeschrittener Skills',
            'url': challenge_tool.url or ''
        })

    return selected


def normalize_recommendation_payload(recommendation: dict, task_description: str, task_type: str, confidence: float, tools: list, skills: list, tool_scores: dict) -> dict:
    user_level = get_user_level(skills)

    recommended_raw = recommendation.get('recommended_tools', []) if isinstance(recommendation, dict) else []
    preferred_names = []
    for item in recommended_raw:
        if isinstance(item, dict):
            name = (item.get('name') or '').strip()
            if name:
                preferred_names.append(name)

    recommended_tools = build_tool_recommendations(
        tools=tools,
        task_type=task_type,
        user_level=user_level,
        tool_scores=tool_scores,
        preferred_names=preferred_names,
    )

    workflow = recommendation.get('workflow') if isinstance(recommendation, dict) else None
    if not isinstance(workflow, list) or not workflow:
        workflow = [
            'Aufgabe präzisieren und Ziel definieren',
            'Passende Tools auswählen und strukturiert anwenden',
            'Ergebnis prüfen und verbessern',
        ]

    tips = recommendation.get('tips') if isinstance(recommendation, dict) else None
    if not isinstance(tips, list) or not tips:
        tips = [
            'Arbeite in kleinen, überprüfbaren Schritten.',
            'Nutze Quellenprüfung und kurze Zwischen-Reviews.',
        ]

    difficulty = recommendation.get('difficulty') if isinstance(recommendation, dict) else None
    if difficulty not in {'easy', 'medium', 'hard'}:
        if confidence < 0.45:
            difficulty = 'easy'
        elif confidence < 0.75:
            difficulty = 'medium'
        else:
            difficulty = 'hard'

    alternative_approach = recommendation.get('alternative_approach') if isinstance(recommendation, dict) else None
    if not alternative_approach:
        alternative_approach = 'Nutze eine manuelle Schritt-für-Schritt-Recherche und validiere Zwischenergebnisse mit einer zweiten Quelle.'

    optimized_prompt = recommendation.get('optimized_prompt') if isinstance(recommendation, dict) else None
    if not optimized_prompt:
        optimized_prompt = f"Hilf mir bei dieser Aufgabe: {task_description}. Gib mir einen klaren Workflow mit überprüfbaren Zwischenschritten."

    estimated_time = recommendation.get('estimated_time') if isinstance(recommendation, dict) else None
    if not estimated_time:
        estimated_time = '30–60 Minuten'

    why_these_tools = recommendation.get('why_these_tools') if isinstance(recommendation, dict) else None
    if not why_these_tools:
        why_these_tools = 'Die Tools passen zu Aufgabe, Skill-Level und bisherigen positiven Bewertungen.'

    skill_gap = recommendation.get('skill_gap') if isinstance(recommendation, dict) else None
    if not skill_gap:
        skill_gap = 'Vertiefe die Nutzung fortgeschrittener Prompt-Strategien und Qualitätskontrolle der Ergebnisse.'

    for tool_entry in recommended_tools:
        if not tool_entry.get('specific_tip'):
            tool_entry['specific_tip'] = 'Starte mit einem kleinen Test-Output und verfeinere anschließend iterativ.'

    return {
        'workflow': workflow,
        'recommended_tools': recommended_tools,
        'optimized_prompt': optimized_prompt,
        'tips': tips,
        'estimated_time': estimated_time,
        'difficulty': difficulty,
        'alternative_approach': alternative_approach,
        'why_these_tools': why_these_tools,
        'skill_gap': skill_gap,
    }


def generate_generic_help_recommendation(task_description: str) -> dict:
    return {
        'workflow': [
            'Aufgabe in 3 Teilprobleme aufteilen',
            'Für jedes Teilproblem eine kurze Lösung skizzieren',
            'Ergebnisse zusammenführen und final prüfen',
        ],
        'recommended_tools': [],
        'optimized_prompt': f"Bitte unterstütze mich Schritt für Schritt bei: {task_description}",
        'tips': ['Halte den Fokus auf den nächsten konkreten Schritt.'],
        'estimated_time': '20–45 Minuten',
        'difficulty': 'easy',
        'alternative_approach': 'Arbeite ohne KI mit einem klaren 3-Schritte-Plan und einer Checkliste.',
        'why_these_tools': 'Kein spezifisches Tool-Match verfügbar, daher neutraler Vorgehensplan.',
        'skill_gap': 'Baue systematische Aufgabenanalyse und Prompt-Präzision aus.',
    }


def save_workflow_history(task_description: str, recommendation: dict):
    history_entry = make_model(
        WorkflowHistory,
        task_description=task_description,
        recommendation_json=json.dumps(recommendation, ensure_ascii=False),
        created_at=datetime.utcnow(),
        user_rating=None,
    )
    db.session.add(history_entry)
    db.session.commit()
    get_tool_scores.cache_clear()
    return history_entry.id


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def build_personalized_context():
    skills = Skill.query.order_by(Skill.id.asc()).all()
    goals = Goal.query.order_by(Goal.id.asc()).all()
    history_entries = WorkflowHistory.query.order_by(WorkflowHistory.created_at.desc()).limit(5).all()

    top_tool_rows = (
        db.session.query(
            Tool.id,
            Tool.name,
            db.func.avg(ToolUsageLog.rating).label('avg_rating')
        )
        .join(ToolUsageLog, ToolUsageLog.tool_id == Tool.id)
        .group_by(Tool.id, Tool.name)
        .having(db.func.avg(ToolUsageLog.rating) > 3.5)
        .order_by(db.func.avg(ToolUsageLog.rating).desc())
        .all()
    )

    user_context_items = UserContext.query.order_by(UserContext.area.asc(), UserContext.key.asc()).all()

    tools = Tool.query.order_by(Tool.id.asc()).all()

    skills_with_level = [f"{skill.name} ({skill.level})" for skill in skills]
    goals_list = [goal.description for goal in goals]

    history_payload = []
    avoid_tools = set()
    for entry in history_entries:
        item = {
            'task': entry.task_description,
            'user_rating': entry.user_rating,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
        }
        history_payload.append(item)

        if entry.user_rating is not None and entry.user_rating < 3:
            try:
                recommendation_data = json.loads(entry.recommendation_json or '{}')
            except json.JSONDecodeError:
                recommendation_data = {}

            for recommended_tool in recommendation_data.get('recommended_tools', []):
                if isinstance(recommended_tool, dict):
                    tool_name = (recommended_tool.get('name') or '').strip()
                elif isinstance(recommended_tool, str):
                    tool_name = recommended_tool.strip()
                else:
                    tool_name = ''
                if tool_name:
                    avoid_tools.add(tool_name)

    top_tools = [
        {
            'name': row.name,
            'avg_rating': round(float(row.avg_rating), 2)
        }
        for row in top_tool_rows
    ]

    tools_structured = []
    for tool in tools:
        tools_structured.append({
            'name': tool.name,
            'category': tool.category,
            'best_for': tool.best_for or '',
            'skill_requirement': tool.skill_requirement or 'Anfänger',
            'prompt_template': tool.prompt_template or '',
            'free_tier_details': tool.free_tier_details or '',
            'url': tool.url or '',
            'rating': tool.rating,
        })

    context = {
        'skills_with_level': skills_with_level,
        'goals': goals_list,
        'workflow_history': history_payload,
        'top_tools': top_tools,
        'all_tools': tools_structured,
        'avoid_tools': sorted(avoid_tools),
        'user_context': [item.to_dict() for item in user_context_items],
    }

    def build_context_text(payload):
        return json.dumps(payload, ensure_ascii=False)

    context_text = build_context_text(context)
    if estimate_tokens(context_text) > 3000:
        truncated_history = context['workflow_history'][:3]
        sorted_tools = sorted(
            context['all_tools'],
            key=lambda item: (item.get('rating') is not None, item.get('rating') or 0),
            reverse=True,
        )
        truncated_tools = sorted_tools[:20]

        context['workflow_history'] = truncated_history
        context['all_tools'] = truncated_tools

    return context, skills, goals, tools


def generate_fallback_recommendation(task: str, tools: list, skills: list, task_type: str, confidence: float, tool_scores: dict) -> dict:
    workflow_templates = {
        'IMAGE': [
            'Motiv und Stil klar definieren',
            'Bild mit passendem KI-Tool erzeugen',
            'Auswahl treffen und visuell nachbearbeiten',
        ],
        'RESEARCH': [
            'Kernfrage formulieren',
            'Quellen sammeln und vergleichen',
            'Erkenntnisse strukturieren und zusammenfassen',
        ],
        'WRITING': [
            'Gliederung erstellen',
            'Entwurf schreiben',
            'Stil und Inhalt überarbeiten',
        ],
        'MATH': [
            'Problemtyp identifizieren',
            'Lösungsweg Schritt für Schritt ausführen',
            'Ergebnis mit Gegenprobe validieren',
        ],
        'PRESENTATION': [
            'Kernaussage und Storyline definieren',
            'Folienstruktur und Visuals erstellen',
            'Probevortrag und Feinschliff',
        ],
        'LEARNING': [
            'Lernziele und Themen priorisieren',
            'Lernblöcke mit Wiederholungen planen',
            'Wissensstand mit Mini-Tests prüfen',
        ],
        'CODE': [
            'Fehler oder Zielzustand präzise beschreiben',
            'Lösung schrittweise implementieren',
            'Tests/Checks durchführen und refaktorisieren',
        ],
        'TRANSLATION': [
            'Quelltext analysieren',
            'Zielsprachliche Übersetzung erstellen',
            'Ton, Terminologie und Konsistenz prüfen',
        ],
        'GENERAL': [
            'Aufgabe in Teilziele aufteilen',
            'Teilziele nacheinander umsetzen',
            'Qualität prüfen und Ergebnis finalisieren',
        ],
    }

    workflow = workflow_templates.get(task_type, workflow_templates['GENERAL'])
    recommendation = {
        'workflow': workflow,
        'recommended_tools': [],
        'optimized_prompt': f"Hilf mir bei folgender Aufgabe: {task}. Gib mir einen umsetzbaren Schritt-für-Schritt-Plan.",
        'tips': [
            'Ergebnisse nach jedem Schritt kurz validieren.',
            'Bei Unsicherheit mit kleinerem Teilproblem starten.',
        ],
        'estimated_time': '30–60 Minuten',
        'difficulty': 'medium' if confidence >= 0.5 else 'easy',
        'alternative_approach': 'Löse die Aufgabe ohne KI mit einer klaren Checkliste und Peer-Review.',
    }

    return normalize_recommendation_payload(
        recommendation=recommendation,
        task_description=task,
        task_type=task_type,
        confidence=confidence,
        tools=tools,
        skills=skills,
        tool_scores=tool_scores,
    )


def build_recommendation_response(task_description: str) -> dict:
    task_description = (task_description or '').strip()
    if not task_description:
        raise ValueError('Keine Aufgabenbeschreibung angegeben')

    task_key = task_description.strip().lower()
    now = time.time()

    # Schritt: Identische Requests innerhalb von 60 Sekunden deduplizieren.
    with recommendation_cache_lock:
        existing = recommendation_cache.get(task_key)
        if (
            existing
            and now - existing['timestamp'] <= RECOMMENDATION_DEDUP_TTL
            and isinstance(existing.get('payload'), dict)
            and 'area' in existing['payload']
            and 'subcategory' in existing['payload']
            and 'personalization_note' in existing['payload']
            and 'next_step' in existing['payload']
        ):
            return existing['payload']

        expired_keys = [
            key for key, value in recommendation_cache.items()
            if now - value['timestamp'] > RECOMMENDATION_DEDUP_TTL
        ]
        for key in expired_keys:
            recommendation_cache.pop(key, None)

    classification = classify_task(task_description)
    task_type = classification['type']
    confidence = classification['confidence']
    area_key = classification.get('area_key', 'schule_lernen')
    area = classification.get('area', 'Schule')
    subcategory = classification.get('subcategory', 'Lernen & Üben')

    personalized_context, skills, goals, tools = build_personalized_context()
    tool_scores = get_tool_scores()
    specialized_sub_prompt = get_specialized_sub_prompt(area_key)
    templates_for_subcategory = get_templates_for_subcategory(subcategory)
    user = User.query.first()
    user_context_map = get_user_context_key_map()
    low_rated_tools = get_low_rated_tools()
    frequently_used_tools = get_frequently_used_tools(limit=3)

    user_name = (user.name if user and user.name else 'Nutzer').strip()
    main_subjects = user_context_map.get('hauptfaecher') or user_context_map.get('schule_faecher') or 'nicht angegeben'
    ki_experience = user_context_map.get('ki_erfahrung') or 'nicht angegeben'
    learning_style = user_context_map.get('lernstil') or 'nicht angegeben'

    skills_text = '\n'.join([f"- {skill}" for skill in personalized_context['skills_with_level']]) or "- Keine Fähigkeiten angegeben"
    goals_text = '\n'.join([f"- {goal}" for goal in personalized_context['goals']]) or "- Keine Ziele angegeben"
    top_tools_text = '\n'.join([
        f"- {item['name']} (Ø Rating: {item['avg_rating']})"
        for item in personalized_context['top_tools']
    ]) or "- Keine bevorzugten Tools verfügbar"

    user_context_text = '\n'.join([
        f"- [{item.get('area')}] {item.get('key')}: {item.get('value')}"
        for item in personalized_context.get('user_context', [])
    ]) or '- Kein zusätzlicher Nutzerkontext gespeichert'

    history_text = '\n'.join([
        f"- Aufgabe: {item['task']} | Rating: {item['user_rating']} | Datum: {item['created_at']}"
        for item in personalized_context['workflow_history']
    ]) or "- Kein Verlauf verfügbar"

    tools_text = '\n'.join([
        (
            f"- Name: {item['name']} | Kategorie: {item['category']} | Best for: {item['best_for'] or 'n/a'} "
            f"| Skill-Requirement: {item['skill_requirement'] or 'n/a'} | Prompt-Template: {item['prompt_template'] or 'n/a'} "
            f"| Free Tier: {item['free_tier_details'] or 'n/a'} | URL: {item['url'] or 'n/a'} | Rating: {item['rating'] if item['rating'] is not None else 'n/a'}"
        )
        for item in personalized_context['all_tools']
    ]) or "- Keine Tools verfügbar"

    avoid_tools_text = ', '.join(personalized_context['avoid_tools']) or 'Keine'
    low_rated_tools_text = ', '.join(low_rated_tools) or 'Keine'
    frequently_used_tools_text = ', '.join(frequently_used_tools) or 'Keine'

    templates_text = '\n'.join([
        f"- {tpl['title']}: {tpl.get('example_input') or ''}"
        for tpl in templates_for_subcategory
    ]) or '- Keine Templates verfügbar'

    app.logger.info(
        f"Recommendation request gestartet: task_type={task_type}, area={area}, subcategory={subcategory}, confidence={confidence}"
    )

    system_prompt = f"""Du bist ein persönlicher KI-Workflow-Coach. Du kennst diesen Nutzer sehr gut:

PROFIL:
- Fähigkeiten:
{skills_text}
- Aktuelle Ziele:
{goals_text}
- Bevorzugte Tools (gut bewertet):
{top_tools_text}

VERLAUF (letzte Aufgaben + Bewertungen):
{history_text}

NUTZER-KONTEXT:
- Name: {user_name}
- Schulfächer: {main_subjects}
- KI-Erfahrung: {ki_experience}
- Lernstil: {learning_style}
- Zuletzt schlecht bewertete Tools (nicht empfehlen): {low_rated_tools_text}
- Häufig genutzte Tools (bevorzugen): {frequently_used_tools_text}
- Erkannter Bereich dieser Aufgabe: {area} → {subcategory}

ZUSÄTZLICHER NUTZERKONTEXT (aus /api/user-context):
{user_context_text}

MEIDE DIESE TOOLS (schlecht bewertet im Verlauf): {avoid_tools_text}

VERFÜGBARE TOOL-DATENBANK:
{tools_text}

PASSENDE TASK-TEMPLATES FÜR {subcategory}:
{templates_text}

DEINE AUFGABE:
Analysiere die neue Aufgabe des Nutzers und erstelle einen hyper-personalisierten Workflow.
- Passe die Komplexität an das Skill-Level an
- Empfiehl nur Tools, die zum Skill-Level passen (skill_requirement beachten)
- Lerne aus dem Verlauf: wenn ein Tool schlecht bewertet wurde, meide es
- Nutze die prompt_templates aus der Datenbank als Basis für den optimized_prompt
- Sei konkret, nicht generisch — nenne exakte Schritte, exakte Tool-Einstellungen
- Bereich: {area} | Unterkategorie: {subcategory}
- Spezialanweisung: {specialized_sub_prompt}

Antworte ausschließlich als JSON:
{{
  "workflow": ["Schritt 1", "Schritt 2", "Schritt 3"],
  "recommended_tools": [{{"name": "", "reason": "", "url": "", "specific_tip": ""}}],
  "optimized_prompt": "",
  "tips": [""],
  "estimated_time": "",
  "difficulty": "easy|medium|hard",
  "why_these_tools": "Kurze Begründung warum genau diese Tools für diesen Nutzer",
        "skill_gap": "Was der Nutzer noch lernen sollte um diese Aufgabe besser zu lösen",
        "personalization_note": "Ein Satz der erklärt warum diese Empfehlung auf den Nutzer zugeschnitten ist. Beispiel: Da du Mathe als Hauptfach hast und Wolfram Alpha bereits gut bewertet hast, steht es an erster Stelle.",
        "next_step": "Der allererste konkrete Schritt den der Nutzer JETZT sofort tun soll — ein einziger klarer Satz"
}}
Kein Fließtext, kein Markdown, nur JSON."""

    user_prompt = f"""Neue Nutzeraufgabe: "{task_description}"
Klassifikation: {task_type} (confidence={confidence})
Erkannter Bereich: {area}
Erkannte Unterkategorie: {subcategory}
Spezialmodus: {specialized_sub_prompt}

Bitte liefere eine konkrete, personalisierte Empfehlung gemäß der Systemregeln.
Nutze nur Tools aus der angegebenen Tool-Datenbank.
Nutze bevorzugt gut bewertete Tools und vermeide negativ bewertete Tools aus dem Verlauf.
Falls kein Tool passt, gib trotzdem einen präzisen Workflow mit umsetzbaren Schritten."""

    recommendation = None
    mode = 'demo'
    model_used = None
    personalization_note = None
    next_step = None

    if GROQ_API_KEY and GROQ_API_KEY != 'dein-groq-api-key-hier':
        try:
            app.logger.info('Recommendation step: trying_groq_api')
            candidate_models = [
                'llama-3.3-70b-versatile',
                'llama-3.1-8b-instant',
                'mixtral-8x7b-32768',
            ]

            for model_name in candidate_models:
                response = requests.post(
                    GROQ_API_URL,
                    headers={
                        'Authorization': f'Bearer {GROQ_API_KEY}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': model_name,
                        'messages': [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': user_prompt}
                        ],
                        'temperature': 0.7,
                        'max_tokens': 1500
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    raw_text = result['choices'][0]['message']['content']

                    try:
                        clean = raw_text.strip()
                        if clean.startswith('```'):
                            clean = clean.split('```')[1]
                            if clean.startswith('json'):
                                clean = clean[4:]
                        ai_recommendation = json.loads(clean.strip())
                        recommendation = normalize_recommendation_payload(
                            recommendation=ai_recommendation,
                            task_description=task_description,
                            task_type=task_type,
                            confidence=confidence,
                            tools=tools,
                            skills=skills,
                            tool_scores=tool_scores,
                        )
                        personalization_note = (ai_recommendation.get('personalization_note') or '').strip() if isinstance(ai_recommendation, dict) else ''
                        next_step = (ai_recommendation.get('next_step') or '').strip() if isinstance(ai_recommendation, dict) else ''
                        mode = 'ai'
                        model_used = model_name
                        app.logger.info(f'Recommendation step: groq_success model={model_used}')
                        break
                    except json.JSONDecodeError:
                        app.logger.warning(f'Recommendation step: groq_invalid_json model={model_name} -> local_fallback')
                        break

                if response.status_code in (400, 404):
                    app.logger.warning(f'Recommendation step: groq_http_{response.status_code} model={model_name} -> trying_next_model')
                    continue

                app.logger.warning(f'Recommendation step: groq_http_{response.status_code} model={model_name} -> local_fallback')
                break
        except Exception as e:
            app.logger.exception(f'Recommendation step: groq_exception -> local_fallback ({e})')

    if recommendation is None:
        try:
            app.logger.info('Recommendation step: local_rule_based_fallback')
            recommendation = generate_fallback_recommendation(
                task=task_description,
                tools=tools,
                skills=skills,
                task_type=task_type,
                confidence=confidence,
                tool_scores=tool_scores,
            )
            mode = 'demo'
            model_used = 'fallback_local_rule_based'
        except Exception as fallback_error:
            app.logger.exception(f'Recommendation step: local_fallback_failed -> generic_help ({fallback_error})')
            recommendation = generate_generic_help_recommendation(task_description)
            mode = 'demo'
            model_used = 'fallback_generic_help'

    if mode == 'ai':
        if not personalization_note:
            preferred_tool = frequently_used_tools[0] if frequently_used_tools else (recommendation.get('recommended_tools', [{}])[0].get('name') if recommendation.get('recommended_tools') else 'passende Tools')
            personalization_note = (
                f"Da {main_subjects} zu deinen Schwerpunkten zählen, dein KI-Level auf '{ki_experience}' steht "
                f"und {preferred_tool} häufig gut zu deinem Workflow passt, ist diese Empfehlung darauf zugeschnitten."
            )

        if not next_step:
            workflow_steps = recommendation.get('workflow') if isinstance(recommendation, dict) else None
            if isinstance(workflow_steps, list) and workflow_steps:
                next_step = workflow_steps[0]
            else:
                next_step = 'Formuliere jetzt die Aufgabe präzise in einem Satz und starte mit dem ersten vorgeschlagenen Tool.'
    else:
        personalization_note = ''
        next_step = ''

    recommendation['personalization_note'] = personalization_note
    recommendation['next_step'] = next_step

    history_id = save_workflow_history(task_description, recommendation)

    response_payload = {
        'task': task_description,
        'recommendation': recommendation,
        'mode': mode,
        'model_used': model_used,
        'history_id': history_id,
        'area': area,
        'subcategory': subcategory,
        'personalization_note': personalization_note,
        'next_step': next_step,
        'classification': {
            'type': task_type,
            'confidence': confidence,
        }
    }

    with recommendation_cache_lock:
        recommendation_cache[task_key] = {
            'timestamp': now,
            'payload': response_payload
        }

    return response_payload


@app.route('/api/recommendation', methods=['POST'])
def get_recommendation():
    """
    Zentrale Empfehlungs-Endpunkt:
    1. Nimmt eine Aufgabenbeschreibung entgegen
    2. Liest Nutzerprofil und Tools aus der DB
    3. Ruft Groq-API (Llama 3) auf
    4. Gibt strukturierte Empfehlung zurück
    """
    data = request.get_json(silent=True) or {}
    task_description = (data.get('task_description') or '').strip()

    if not task_description:
        return jsonify({'error': 'Keine Aufgabenbeschreibung angegeben'}), 400

    try:
        response_payload = build_recommendation_response(task_description)
        return jsonify(response_payload)
    except ValueError as value_error:
        return jsonify({'error': str(value_error)}), 400
    except Exception as err:
        app.logger.exception(f'Recommendation endpoint failed: {err}')
        return jsonify({'error': 'Interner Fehler bei der Empfehlungserstellung'}), 500


@app.route('/api/telegram/status', methods=['GET'])
def telegram_status():
    return jsonify({
        'enabled': is_telegram_enabled(),
        'mode': TELEGRAM_MODE,
        'worker_started': telegram_worker_started,
        'receiver_started': telegram_receiver_started,
        'allowed_chat_ids_configured': bool(ALLOWED_CHAT_IDS),
        'queue_size': telegram_update_queue.qsize(),
        'webhook_path': f'{TELEGRAM_WEBHOOK_PATH}/<secret>',
        'webhook_base_url_configured': bool(TELEGRAM_WEBHOOK_BASE_URL),
    })


@app.route('/api/telegram/setup-webhook', methods=['POST'])
def telegram_setup_webhook():
    if not is_telegram_enabled():
        return jsonify({'error': 'Telegram ist nicht konfiguriert (TELEGRAM_BOT_TOKEN / TELEGRAM_WEBHOOK_SECRET fehlen)'}), 400

    if not TELEGRAM_WEBHOOK_BASE_URL:
        return jsonify({'error': 'TELEGRAM_WEBHOOK_BASE_URL fehlt'}), 400

    webhook_url = f"{TELEGRAM_WEBHOOK_BASE_URL}{TELEGRAM_WEBHOOK_PATH}/{TELEGRAM_WEBHOOK_SECRET}"
    payload = {
        'url': webhook_url,
        'secret_token': TELEGRAM_WEBHOOK_SECRET,
        'drop_pending_updates': True,
        'allowed_updates': ['message', 'edited_message'],
    }

    try:
        result = telegram_api_call('setWebhook', payload)
        ensure_telegram_worker_started()
        return jsonify({'success': True, 'webhook_url': webhook_url, 'telegram_response': result})
    except Exception as err:
        app.logger.exception(f'Telegram setWebhook failed: {err}')
        return jsonify({'error': str(err)}), 502


@app.route('/api/telegram/webhook/<secret>', methods=['POST'])
def telegram_webhook(secret):
    if not is_telegram_enabled():
        return jsonify({'error': 'Telegram nicht aktiviert'}), 404

    if secret != TELEGRAM_WEBHOOK_SECRET:
        return jsonify({'error': 'Ungültiger Webhook-Secret'}), 403

    header_secret = (request.headers.get('X-Telegram-Bot-Api-Secret-Token') or '').strip()
    if header_secret and header_secret != TELEGRAM_WEBHOOK_SECRET:
        return jsonify({'error': 'Ungültiger Secret-Header'}), 403

    update = request.get_json(silent=True) or {}
    update_id = update.get('update_id')
    if update_id is None:
        return jsonify({'ok': True, 'ignored': 'no_update_id'})

    try:
        update_id = int(update_id)
    except (TypeError, ValueError):
        return jsonify({'ok': True, 'ignored': 'invalid_update_id'})

    if is_duplicate_update(update_id):
        return jsonify({'ok': True, 'deduplicated': True})

    remember_processed_update(update_id)
    ensure_telegram_worker_started()

    try:
        telegram_update_queue.put_nowait(update)
    except queue.Full:
        app.logger.warning('Telegram webhook queue full, dropping update')
        message = update.get('message') or update.get('edited_message') or {}
        chat_id = ((message.get('chat') or {}).get('id'))
        if chat_id is not None:
            try:
                send_telegram_message(int(chat_id), '⚠️ Der Bot ist gerade ausgelastet. Bitte versuche es in 1-2 Minuten erneut.')
            except Exception:
                pass
        return jsonify({'ok': True, 'queued': False, 'reason': 'queue_full'})

    return jsonify({'ok': True, 'queued': True})


@app.route('/api/health', methods=['GET'])
def health():
    """Health-Check Endpunkt"""
    return jsonify({
        'status': 'ok',
        'groq_configured': bool(GROQ_API_KEY and GROQ_API_KEY != 'dein-groq-api-key-hier'),
        'telegram_configured': is_telegram_enabled(),
    })


@app.route('/api/workflow-history', methods=['GET', 'POST'])
def update_workflow_history():
    """GET: Verlauf abrufen, POST: Nutzer-Feedback (Sternebewertung) speichern."""
    if request.method == 'GET':
        entries = WorkflowHistory.query.order_by(WorkflowHistory.created_at.desc()).limit(20).all()
        return jsonify([entry.to_dict() for entry in entries])

    data = request.get_json() or {}

    workflow_history_id_raw = data.get('id', data.get('workflow_history_id'))
    user_rating_raw = data.get('rating', data.get('user_rating'))
    if workflow_history_id_raw is None or user_rating_raw is None:
        return jsonify({'error': 'id/workflow_history_id und rating/user_rating müssen numerisch sein'}), 400

    try:
        workflow_history_id = int(str(workflow_history_id_raw).strip())
        user_rating = int(str(user_rating_raw).strip())
    except (TypeError, ValueError):
        return jsonify({'error': 'id/workflow_history_id und rating/user_rating müssen numerisch sein'}), 400

    if user_rating < 1 or user_rating > 5:
        return jsonify({'error': 'user_rating muss zwischen 1 und 5 liegen'}), 400

    history_entry = WorkflowHistory.query.get(workflow_history_id)
    if not history_entry:
        return jsonify({'error': 'Workflow-History-Eintrag nicht gefunden'}), 404

    history_entry.user_rating = user_rating
    db.session.commit()
    get_tool_scores.cache_clear()

    return jsonify({
        'success': True,
        'id': workflow_history_id,
        'rating': user_rating,
        'workflow_history_id': workflow_history_id,
        'user_rating': user_rating,
    })


# App starten
if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

    # Schritt: Seeding in Hintergrund-Thread ausführen, damit Start nicht blockiert.
    def run_seed_in_background():
        with app.app_context():
            seed_database()
            seed_extended_data()
            clear_data_caches()

    with app.app_context():
        db.create_all()  # Tabellen erstellen falls nicht vorhanden

    seeding_thread = threading.Thread(target=run_seed_in_background, daemon=True)
    seeding_thread.start()

    ensure_telegram_worker_started()

    port = int(os.environ.get('PORT', '5000'))
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"🚀 Workflow-App Backend läuft auf http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
