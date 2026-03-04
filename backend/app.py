"""
app.py - Flask Backend für die Workflow-Optimierungs-App
REST-API mit Endpunkten für Profil und KI-Empfehlungen
"""

import os
import json
import time
import threading
import requests
from functools import lru_cache, wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_compress import Compress
from dotenv import load_dotenv
from models import db, User, Skill, Goal, Tool, WorkflowHistory, seed_extended_data

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
    database_url = 'sqlite:///instance/workflow.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Groq API Konfiguration (kostenlose LLM-API)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Datenbank mit App verbinden
db.init_app(app)


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

        wrapper.cache_clear = cache_clear
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


def seed_database():
    """Befüllt die Datenbank mit Beispieldaten beim ersten Start"""
    # Nur seeden wenn die Tabellen leer sind
    if User.query.first():
        return
    
    # Standard-Nutzer anlegen
    user = User(name="Mein Profil")
    db.session.add(user)
    
    # Beispiel-Fähigkeiten
    skills = [
        Skill(name="Python-Grundlagen", level="Fortgeschritten"),
        Skill(name="Web-Recherche", level="Experte"),
        Skill(name="Bildbearbeitung", level="Anfänger"),
        Skill(name="Textschreiben", level="Fortgeschritten"),
        Skill(name="KI-Prompt-Engineering", level="Anfänger"),
    ]
    for skill in skills:
        db.session.add(skill)
    
    # Beispiel-Ziele
    goals = [
        Goal(description="Note in Mathe verbessern"),
        Goal(description="KI-Tools effektiver nutzen lernen"),
        Goal(description="Schulprojekte schneller abschließen"),
    ]
    for goal in goals:
        db.session.add(goal)
    
    # Nützliche kostenlose Tools
    tools = [
        Tool(
            name="Groq API (Llama 3)",
            category="KI-Textgenerierung",
            url="https://console.groq.com",
            notes="Sehr schnelle kostenlose Text-KI, ideal für Analysen und Schreiben"
        ),
        Tool(
            name="Stable Diffusion (DreamStudio)",
            category="Bilderstellung",
            url="https://dreamstudio.ai",
            notes="Kostenlose Credits für realistische KI-Bilder"
        ),
        Tool(
            name="Perplexity AI",
            category="Internet-Recherche",
            url="https://perplexity.ai",
            notes="KI-gestützte Suchmaschine mit Quellenangaben, kostenlos nutzbar"
        ),
        Tool(
            name="Zotero",
            category="Literaturverwaltung",
            url="https://zotero.org",
            notes="Kostenlose Literaturverwaltung für wissenschaftliche Arbeiten"
        ),
        Tool(
            name="Canva (Free)",
            category="Design & Präsentation",
            url="https://canva.com",
            notes="Kostenlose Designplattform für Präsentationen, Poster, Social Media"
        ),
        Tool(
            name="Anki",
            category="Lernen & Schule",
            url="https://apps.ankiweb.net",
            notes="Kostenlose Lernkarten-App mit intelligentem Wiederholungssystem"
        ),
        Tool(
            name="Wolfram Alpha",
            category="Mathe & Wissenschaft",
            url="https://wolframalpha.com",
            notes="Mächtiges Rechenwerkzeug für Mathematik, Physik, Chemie"
        ),
        Tool(
            name="DeepL",
            category="Übersetzung",
            url="https://deepl.com",
            notes="Hochqualitative kostenlose Übersetzungen"
        ),
        Tool(
            name="Bing Image Creator",
            category="Bilderstellung",
            url="https://www.bing.com/images/create",
            notes="Kostenlose KI-Bildgenerierung via DALL-E, kein Account nötig"
        ),
        Tool(
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
        skill = Skill(name=data['name'], level=data.get('level', 'Anfänger'))
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
        goal = Goal(description=data['description'])
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
        tool = Tool(
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

    best_type = max(scores, key=lambda key: scores[key]) if scores else 'GENERAL'
    best_score = scores.get(best_type, 0)

    if best_score <= 0:
        return {'type': 'GENERAL', 'confidence': 0.25}

    confidence = min(1.0, 0.35 + 0.13 * best_score)
    return {'type': best_type, 'confidence': round(confidence, 2)}


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

    return {
        'workflow': workflow,
        'recommended_tools': recommended_tools,
        'optimized_prompt': optimized_prompt,
        'tips': tips,
        'estimated_time': estimated_time,
        'difficulty': difficulty,
        'alternative_approach': alternative_approach,
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
    }


def save_workflow_history(task_description: str, recommendation: dict):
    history_entry = WorkflowHistory(
        task_description=task_description,
        recommendation_json=json.dumps(recommendation, ensure_ascii=False),
        user_rating=None,
    )
    db.session.add(history_entry)
    db.session.commit()
    get_tool_scores.cache_clear()


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


@app.route('/api/recommendation', methods=['POST'])
def get_recommendation():
    """
    Zentrale Empfehlungs-Endpunkt:
    1. Nimmt eine Aufgabenbeschreibung entgegen
    2. Liest Nutzerprofil und Tools aus der DB
    3. Ruft Groq-API (Llama 3) auf
    4. Gibt strukturierte Empfehlung zurück
    """
    data = request.get_json()
    task_description = data.get('task_description', '').strip()
    
    if not task_description:
        return jsonify({'error': 'Keine Aufgabenbeschreibung angegeben'}), 400

    task_key = task_description.strip().lower()
    now = time.time()

    # Schritt: Identische Requests innerhalb von 60 Sekunden deduplizieren.
    with recommendation_cache_lock:
        existing = recommendation_cache.get(task_key)
        if existing and now - existing['timestamp'] <= RECOMMENDATION_DEDUP_TTL:
            return jsonify(existing['payload'])

        expired_keys = [
            key for key, value in recommendation_cache.items()
            if now - value['timestamp'] > RECOMMENDATION_DEDUP_TTL
        ]
        for key in expired_keys:
            recommendation_cache.pop(key, None)

    classification = classify_task(task_description)
    task_type = classification['type']
    confidence = classification['confidence']

    skills = Skill.query.all()
    tools = Tool.query.all()
    goals = Goal.query.all()
    tool_scores = get_tool_scores()

    skills_text = ', '.join([f"{s.name} ({s.level})" for s in skills]) or "Keine Fähigkeiten angegeben"
    goals_text = ', '.join([g.description for g in goals]) or "Keine Ziele angegeben"
    tools_text = '\n'.join([
        f"- {t.name} ({t.category}) | Skill: {t.skill_requirement or 'n/a'} | Score: {tool_scores.get(t.name, 1.0)} | URL: {t.url}"
        for t in tools
    ]) or "Keine Tools verfügbar"

    app.logger.info(f"Recommendation request gestartet: task_type={task_type}, confidence={confidence}")

    system_prompt = """Du bist ein persönlicher Workflow-Optimierungs-Assistent.
Antworte ausschließlich als valides JSON-Objekt mit exakt diesen Feldern:
{
    "workflow": ["Schritt 1", "Schritt 2", "Schritt 3"],
    "recommended_tools": [
        {"name": "Tool Name", "reason": "Warum dieses Tool", "url": "https://..."}
    ],
    "optimized_prompt": "String",
    "tips": ["Tipp 1", "Tipp 2"],
    "estimated_time": "String",
    "difficulty": "easy|medium|hard",
    "alternative_approach": "String"
}
Kein Fließtext, kein Markdown, nur JSON."""

    user_prompt = f"""Aufgabe: "{task_description}"
Klassifikation: {task_type} (confidence={confidence})

Fähigkeiten des Nutzers: {skills_text}
Aktuelle Ziele: {goals_text}

Verfügbare kostenlose Tools:
{tools_text}

Erstelle einen optimierten Workflow für diese Aufgabe. 
Empfiehl nur Tools aus der obigen Liste wenn sie relevant sind.
Berücksichtige Skill-Matching: Empfiehl kein Experten-Tool für Anfänger, außer als optionale Challenge.
Berücksichtige, dass Tools mit niedrigem Score depriorisiert werden sollen.
Generiere auch einen verbesserten, detaillierten Prompt."""

    recommendation = None
    mode = 'demo'

    if GROQ_API_KEY and GROQ_API_KEY != 'dein-groq-api-key-hier':
        try:
            app.logger.info('Recommendation step: trying_groq_api')
            response = requests.post(
                GROQ_API_URL,
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'llama3-8b-8192',  # Kostenloses Llama 3 Modell via Groq
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
                    mode = 'ai'
                    app.logger.info('Recommendation step: groq_success')
                except json.JSONDecodeError:
                    app.logger.warning('Recommendation step: groq_invalid_json -> local_fallback')
            else:
                app.logger.warning(f'Recommendation step: groq_http_{response.status_code} -> local_fallback')
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
        except Exception as fallback_error:
            app.logger.exception(f'Recommendation step: local_fallback_failed -> generic_help ({fallback_error})')
            recommendation = generate_generic_help_recommendation(task_description)
            mode = 'demo'

    response_payload = {
        'task': task_description,
        'recommendation': recommendation,
        'mode': mode,
        'classification': {
            'type': task_type,
            'confidence': confidence,
        }
    }

    save_workflow_history(task_description, recommendation)

    with recommendation_cache_lock:
        recommendation_cache[task_key] = {
            'timestamp': now,
            'payload': response_payload
        }

    return jsonify(response_payload)


@app.route('/api/health', methods=['GET'])
def health():
    """Health-Check Endpunkt"""
    return jsonify({'status': 'ok', 'groq_configured': bool(GROQ_API_KEY and GROQ_API_KEY != 'dein-groq-api-key-hier')})


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

    port = int(os.environ.get('PORT', '5000'))
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"🚀 Workflow-App Backend läuft auf http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
