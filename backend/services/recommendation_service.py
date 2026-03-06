import json
import logging
import os
import threading
import time
from datetime import datetime
from functools import lru_cache

import requests
from flask import jsonify, request

from extensions import db
from models import (
    Goal,
    Skill,
    Tool,
    UserContext,
    WorkflowHistory,
    make_model,
)
from services.feedback_service import extract_recommended_tool_names, upsert_recommendation_feedback
from utils.cache_utils import ttl_cache


logger = logging.getLogger(__name__)
GROQ_API_KEY = (os.environ.get('GROQ_API_KEY') or '').strip()
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
LEVEL_RANK = {
    'Anfänger': 1,
    'Fortgeschritten': 2,
    'Experte': 3,
}

TASK_TYPE_KEYWORDS = {
    'IMAGE': ['bild', 'foto', 'image', 'grafik', 'illustration', 'poster', 'design', 'logo'],
    'RESEARCH': ['recherche', 'quelle', 'quellen', 'fakten', 'hintergrund', 'zusammenhang', 'belegarbeit', 'facharbeit', 'kryptologie', 'recherchiere'],
    'WRITING': ['aufsatz', 'essay', 'text', 'zusammenfassung', 'analyse', 'schreiben', 'gedicht', 'belegarbeit', 'facharbeit', 'hausarbeit', 'referat'],
    'MATH': ['mathe', 'gleichung', 'rechnung', 'formel', 'integral', 'ableitung', 'physik'],
    'PRESENTATION': ['präsentation', 'praesentation', 'vortrag', 'folien', 'slides', 'referat'],
    'LEARNING': ['lernen', 'klausur', 'prüfung', 'pruefung', 'wiederholen', 'lernplan', 'lernkarten'],
    'CODE': ['code', 'python', 'javascript', 'debug', 'bug', 'api', 'programmieren'],
    'TRANSLATION': ['übersetze', 'uebersetze', 'übersetzung', 'uebersetzung', 'translate', 'deutsch', 'englisch', 'sprache'],
}

DOMAIN_KEYWORDS = {
    'KI & Automatisierung': [
        'ki', 'ai', 'chatgpt', 'claude', 'prompt', 'llm', 'automatisierung',
        'generieren', 'bild erstellen', 'text generieren', 'perplexity',
    ],
    'Schule & Lernen': [
        'schule', 'lernen', 'klausur', 'referat', 'facharbeit', 'belegarbeit',
        'hausaufgabe', 'prüfung', 'abitur', 'recherche', 'lernkarten',
        'zusammenfassen', 'karteikarten', 'kryptologie',
    ],
    'Produktivität & Office': [
        'excel', 'tabelle', 'sheets', 'word', 'dokument', 'präsentation',
        'planung', 'office', 'notion', 'aufgaben', 'kalender', 'todo',
        'pivot', 'formel', 'spreadsheet',
    ],
    'Kreatives Arbeiten': [
        'design', 'video', 'audio', 'bild', 'grafik', 'canva', 'figma',
        'logo', 'poster', 'schnitt', 'musik', 'illustration', 'thumbnail',
    ],
    'Programmierung & Tech': [
        'code', 'python', 'javascript', 'bug', 'debug', 'github', 'api',
        'programmieren', 'git', 'script', 'funktion', 'class', 'algorithmus',
    ],
    'Kommunikation & Team': [
        'email', 'meeting', 'team', 'slack', 'discord', 'kommunikation',
        'zusammenarbeit', 'feedback', 'abstimmung', 'nachricht',
    ],
    'Daten & Analyse': [
        'daten', 'analyse', 'statistik', 'visualisierung', 'dashboard',
        'sql', 'diagramm', 'auswertung', 'kennzahlen',
    ],
    'Finanzen & Business': [
        'finanzen', 'buchhaltung', 'steuer', 'business', 'crm',
        'rechnung', 'budget', 'kosten', 'umsatz',
    ],
}

AREA_KEYWORDS = {
    'ki_bild': ['bild', 'logo', 'foto', 'illustration', 'zeichnung', 'banner', 'thumbnail', 'poster'],
    'ki_code': ['code', 'programmier', 'script', 'python', 'javascript', 'bug', 'funktion', 'app'],
    'ki_prompt': ['prompt', 'anweisung', 'chatgpt', 'claude', 'formulier'],
    'ki_analyse': ['zusammenfassung', 'analysier', 'erkläre', 'erklaere', 'versteh', 'übersetz', 'uebersetz', 'bewert'],
    'recherche_bild': ['bild suchen', 'foto finden', 'stock', 'bildquelle'],
    'recherche_info': ['recherche', 'informationen', 'suche', 'quellen', 'fakten', 'wer ist', 'was ist'],
    'schule_docs': ['mitschreiben', 'notizen', 'dokument', 'aufsatz', 'essay', 'referat', 'facharbeit', 'belegarbeit', 'hausarbeit', 'wissenschaftlich', 'zitier', 'quellenangabe'],
    'schule_projekt': ['schulprojekt', 'präsentation', 'praesentation', 'vortrag', 'hausaufgabe', 'abgabe'],
    'schule_lernen': ['lernen', 'üben', 'ueben', 'vorbereitung', 'klausur', 'prüfung', 'pruefung', 'wiederholen', 'karteikarten'],
    'alltag_planung': ['planung', 'organisieren', 'struktur', 'todo', 'to-do', 'zeitplan', 'wochenplan', 'routine'],
    'alltag_kommunikation': ['email', 'e-mail', 'nachricht', 'kommunikation', 'feedback', 'abstimmung', 'meeting'],
    'alltag_priorisierung': ['priorisierung', 'priorität', 'prioritaet', 'entscheiden', 'entscheidung', 'fokus', 'dringend', 'wichtig'],
    'karriere_bewerbung': ['bewerbung', 'lebenslauf', 'cv', 'anschreiben', 'portfolio', 'praktikum', 'ferienjob'],
    'karriere_skills': ['weiterbildung', 'roadmap', 'skill', 'karriere', 'zertifikat', 'kurs', 'lernpfad'],
    'karriere_business': ['business', 'geschäftsidee', 'geschaeftsidee', 'selbstständig', 'selbststaendig', 'freelance', 'angebot', 'kunde', 'crm'],
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

recommendation_cache = {}
recommendation_cache_lock = threading.Lock()
RECOMMENDATION_DEDUP_TTL = 60

STOPWORDS = {
    'und', 'oder', 'die', 'der', 'das', 'den', 'dem', 'ein', 'eine', 'einer', 'eines', 'einem',
    'fuer', 'für', 'mit', 'aus', 'ist', 'im', 'in', 'am', 'an', 'auf', 'zu', 'von', 'bei',
    'als', 'wie', 'was', 'wer', 'wo', 'wann', 'warum', 'ich', 'du', 'er', 'sie', 'es',
    'wir', 'ihr', 'sie', 'kein', 'keine', 'nicht',
}

TASK_TYPE_CATEGORY_KEYWORDS = {
    'WRITING': ['schreiben', 'text', 'dokument', 'ai', 'research'],
    'RESEARCH': ['recherche', 'suche', 'quellen', 'ai'],
    'CODE': ['code', 'programmierung', 'entwicklung'],
    'IMAGE': ['bild', 'grafik', 'design', 'illustration'],
    'MATH': ['mathe', 'wissenschaft', 'rechnung'],
    'PRESENTATION': ['praesentation', 'folien', 'slides', 'design'],
    'LEARNING': ['lernen', 'schule', 'uebung', 'lernplan'],
    'TRANSLATION': ['uebersetzung', 'sprache', 'text'],
    'GENERAL': ['allgemein', 'workflow', 'planung'],
}

TASK_PROFILE_NEED_KEYWORDS = {
    'research': ['recherche', 'quellen', 'finden', 'suchen', 'informationen', 'ueberblick', 'überblick', 'kryptologie', 'analyse', 'facharbeit', 'belegarbeit', 'wissenschaftlich', 'quellangabe', 'zitier'],
    'writing': ['schreiben', 'verfassen', 'verfasse', 'text', 'aufsatz', 'belegarbeit', 'facharbeit', 'zusammenfassen', 'formulieren', 'ausarbeitung'],
    'structuring': ['gliederung', 'struktur', 'planen', 'outline', 'aufteilen', 'organisieren'],
    'learning': ['lernen', 'lernkarten', 'wiederholen', 'erklaeren', 'erklären'],
    'coding': ['code', 'programmier', 'python', 'software', 'debug', 'algorithmus'],
    'presenting': ['praesentation', 'präsentation', 'referat', 'folien', 'slides', 'vortrag'],
    'translating': ['uebersetzen', 'übersetzen', 'uebersetzung', 'übersetzung', 'translate'],
    'calculating': ['berechnen', 'rechnung', 'gleichung', 'mathe', 'formel', 'integral'],
}

TASK_PROFILE_SUBJECT_KEYWORDS = {
    'informatik': ['code', 'programmier', 'kryptologie', 'algorithmus', 'python', 'software', 'informatik', 'verschluesselung', 'verschlüsselung'],
    'mathematik': ['mathe', 'mathematik', 'gleichung', 'integral', 'ableitung', 'formel', 'rechnung'],
    'deutsch': ['deutsch', 'aufsatz', 'interpretation', 'gedicht', 'grammatik'],
    'biologie': ['biologie', 'zelle', 'genetik', 'oekologie', 'ökologie', 'evolution'],
    'englisch': ['englisch', 'english', 'translation', 'uebersetzung', 'übersetzung', 'essay'],
}

TASK_PROFILE_OUTPUT_KEYWORDS = {
    'facharbeit': ['facharbeit', 'belegarbeit'],
    'referat': ['referat', 'vortrag'],
    'zusammenfassung': ['zusammenfassung', 'zusammenfassen'],
    'lernkarten': ['lernkarten', 'karteikarten'],
    'code': ['code', 'script', 'programm'],
    'praesentation': ['praesentation', 'präsentation', 'folien', 'slides'],
    'bild': ['bild', 'grafik', 'illustration'],
}

TOOL_NEED_MAP = {
    'groq api': ['coding'],
    'chatgpt': ['writing', 'research', 'structuring'],
    'chatgpt free': ['writing', 'research', 'structuring'],
    'claude free': ['writing', 'structuring'],
    'microsoft copilot': ['writing', 'research'],
    'overleaf': ['writing'],
    'quillbot': ['writing'],
    'languagetool': ['writing'],
    'perplexity': ['research'],
    'google scholar': ['research'],
    'semantic scholar': ['research'],
    'connected papers': ['research'],
    'you.com': ['research'],
    'zotero': ['research', 'writing'],
    'mendeley': ['research', 'writing'],
    'notebooklm': ['research', 'structuring'],
    'hemingway': ['writing'],
    'gamma': ['presenting'],
    'canva': ['presenting', 'coding'],
    'anki': ['learning'],
    'remno': ['learning'],
    'quizlet': ['learning'],
    'serlo': ['learning', 'calculating'],
    'wolfram alpha': ['calculating'],
    'symbolab': ['calculating'],
    'github copilot': ['coding'],
    'phind': ['coding'],
    'freecodecamp': ['coding'],
    'deepl': ['translating'],
    'google translate': ['translating'],
    'reverso': ['translating'],
    'claude': ['writing', 'structuring'],
}

TOOL_BLACKLIST = {
    'writing': ['groq api', 'stable diffusion', 'bing image', 'audacity', 'voicepen', 'capcut', 'loom', 'calendly', 'hubspot', 'duolingo', 'busuu', 'memrise'],
    'research': ['groq api', 'stable diffusion', 'bing image', 'audacity', 'capcut', 'duolingo', 'deepl', 'google translate', 'canva video'],
    'coding': ['canva', 'anki', 'quizlet', 'deepl', 'duolingo'],
    'translating': [],
    'calculating': ['canva', 'stable diffusion', 'deepl', 'duolingo'],
    'learning': [],
    'presenting': [],
    'structuring': [],
}

def classify_ai_provider_error(http_status=None, provider_message: str = '', model_name: str = '') -> dict:
    message_lower = (provider_message or '').lower()

    if http_status in {401, 403}:
        code = 'ai_auth_error'
        user_message = 'KI-Provider Auth fehlgeschlagen. Pruefe den API-Key in backend/.env.'
        retryable = False
    elif http_status == 429:
        code = 'ai_rate_limit'
        user_message = 'KI-Provider Rate-Limit erreicht. Bitte kurz warten und erneut versuchen.'
        retryable = True
    elif http_status == 413 or 'token' in message_lower or 'context length' in message_lower or 'too long' in message_lower:
        code = 'ai_token_limit'
        user_message = 'Die Anfrage ist fuer das aktuelle Modell zu lang (Token/Context-Limit). Kuerze die Aufgabe oder den Kontext.'
        retryable = True
    elif http_status == 404:
        code = 'ai_model_not_found'
        user_message = 'Das KI-Modell ist aktuell nicht verfuegbar. Ein alternatives Modell wurde versucht.'
        retryable = True
    elif http_status is not None and http_status >= 500:
        code = 'ai_provider_unavailable'
        user_message = 'Der KI-Provider ist momentan nicht verfuegbar. Bitte spaeter erneut versuchen.'
        retryable = True
    elif 'timeout' in message_lower:
        code = 'ai_timeout'
        user_message = 'Zeitueberschreitung beim KI-Provider. Bitte erneut versuchen.'
        retryable = True
    elif http_status == 400:
        code = 'ai_bad_request'
        user_message = 'Die KI-Anfrage konnte vom Provider nicht verarbeitet werden (HTTP 400).'
        retryable = False
    else:
        code = 'ai_provider_error'
        user_message = 'Unbekannter KI-Provider-Fehler.'
        retryable = True

    return {
        'code': code,
        'user_message': user_message,
        'retryable': retryable,
        'http_status': http_status,
        'provider_message': (provider_message or '').strip()[:500],
        'model': model_name,
        'provider': 'groq',
    }

def classify_task(task_text: str) -> dict:
    lowered = (task_text or '').lower()
    scores = {task_type: 0 for task_type in TASK_TYPE_KEYWORDS}

    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        scores[task_type] = sum(1 for keyword in keywords if keyword in lowered)

    if any(token in lowered for token in ['def ', 'function', 'class ', 'traceback', 'error', 'exception']):
        scores['CODE'] += 2
    if any(token in lowered for token in ['folien', 'slides', 'pitch deck']):
        scores['PRESENTATION'] += 1

    area_scores = {area_key: sum(1 for keyword in keywords if keyword in lowered) for area_key, keywords in AREA_KEYWORDS.items()}
    best_area_key = max(area_scores, key=lambda key: area_scores[key]) if area_scores else None
    best_area_score = area_scores.get(best_area_key, 0) if best_area_key else 0

    best_type = max(scores, key=lambda key: scores[key]) if scores else 'GENERAL'
    best_score = scores.get(best_type, 0)

    if best_score <= 0:
        default_area_key = best_area_key or 'schule_lernen'
        default_area, default_subcategory = AREA_MAPPING.get(default_area_key, ('Schule', 'Lernen & Üben'))
        return {
            'type': 'GENERAL',
            'confidence': 0.3,
            'area_key': default_area_key,
            'area': default_area,
            'subcategory': default_subcategory,
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


def detect_domains(task_description: str) -> list[str]:
    text = task_description.lower()
    domain_scores = {}

    for domain_name, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            domain_scores[domain_name] = score

    if not domain_scores:
        return []

    sorted_domains = sorted(
        domain_scores.items(), key=lambda x: x[1], reverse=True
    )
    # Return top 2 domains with at least 1 hit
    return [name for name, score in sorted_domains[:2]]

def get_user_context_key_map() -> dict:
    key_map = {}
    context_items = UserContext.query.order_by(UserContext.area.asc(), UserContext.key.asc()).all()
    for item in context_items:
        key_map[item.key] = item.value
    return key_map

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

        recommended_names = extract_recommended_tool_names(recommendation_data)
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

def summarize_user_context(skills, goals, user_context_dict) -> str:
    safe_context = user_context_dict if isinstance(user_context_dict, dict) else {}

    level = get_user_level(skills) if skills else 'unbekannt'

    skill_names = []
    for skill in skills or []:
        name = str(getattr(skill, 'name', '') or '').strip()
        if name:
            skill_names.append(name)
        if len(skill_names) >= 3:
            break
    skills_text = ', '.join(skill_names) if skill_names else 'unbekannt'

    goal_names = []
    for goal in goals or []:
        description = str(getattr(goal, 'description', '') or '').strip()
        if description:
            goal_names.append(description)
    goals_text = ', '.join(goal_names) if goal_names else 'unbekannt'

    ki_experience = str(safe_context.get('ki_erfahrung') or '').strip() or 'unbekannt'
    learning_style = str(safe_context.get('lernstil') or '').strip() or 'unbekannt'

    summary = (
        f'Nutzer ist {level} in {skills_text}. '
        f'Ziele: {goals_text}. '
        f'Kontext: {ki_experience}, bevorzugt {learning_style}.'
    )

    if len(summary) > 400:
        summary = summary[:397].rstrip() + '...'

    return summary


def build_micro_prompt(task_description, task_profile, top_tools, user_summary, all_tool_names, detected_domains) -> str:
    safe_profile = task_profile if isinstance(task_profile, dict) else {}
    output_type = str(safe_profile.get('output_type') or 'unbekannt')
    subject_area = str(safe_profile.get('subject_area') or 'unbekannt')
    primary_need = str(safe_profile.get('primary_need') or 'unbekannt')

    tools_lines = []
    for tool in top_tools or []:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get('name') or 'unbekannt')
        try:
            match_score = float(tool.get('match_score') or 0.0)
        except (TypeError, ValueError):
            match_score = 0.0
        best_for = str(tool.get('best_for') or '').strip() or str(tool.get('reason') or '').strip() or 'unbekannt'
        tools_lines.append(f"- {name} ({match_score:.0f}/100): {best_for[:60]}")

    tools_text = '\n'.join(tools_lines) if tools_lines else '- unbekannt (0/100): unbekannt'

    names = [str(name).strip() for name in (all_tool_names or []) if str(name).strip()]
    all_tools_text = ', '.join(names) if names else 'unbekannt'

    schema = '{{"verified_tools":[{{"name":"...","reason":"1 Satz warum dieses Tool hier passt"}}],"workflow":["Schritt 1...","Schritt 2...","Schritt 3...","Schritt 4..."],"optimized_prompt":"Direkt nutzbarer Prompt fuer den Nutzer, 2-3 Saetze.","tips":["Tipp 1","Tipp 2"],"why_these_tools":"1 Satz Gesamtbegruendung."}}'
    rules = (
        '- verified_tools: behalte passende Tools, ersetze unpassende nur durch Namen aus der verfuegbaren Liste\n'
        '- Maximal 5 Tools\n'
        '- workflow: genau 4 konkrete Schritte, nenne jeweils ein Tool beim Namen\n'
        '- optimized_prompt: spezifisch fuer die Aufgabe, nicht generisch\n'
        '- Antworte NUR mit dem JSON, kein Text davor oder danach'
    )
    return (
        f'Aufgabe: "{task_description}"\n'
        f"Erkannte Domänen: {', '.join(detected_domains) if detected_domains else 'allgemein'}\n"
        f'Ausgabetyp: {output_type} | Fachbereich: {subject_area} | Bedarf: {primary_need}\n'
        f'Nutzer: {user_summary}\n\n'
        f'Die Datenbank hat diese Tools vorgeschlagen:\n{tools_text}\n\n'
        f'Verfuegbare Tools gesamt (nur Namen, kommasepariert):\n{all_tools_text}\n\n'
        f'Antworte AUSSCHLIESSLICH als valides JSON ohne Markdown-Backticks:\n{schema}\n\nRegeln:\n{rules}'
    )


def _tokenize_meaningful(text: str) -> set[str]:
    if not text:
        return set()

    normalized = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in text)
    tokens = {token for token in normalized.split() if len(token) > 2 and token not in STOPWORDS}
    return tokens


def get_task_profile(task_description: str) -> dict:
    text = (task_description or '').lower()

    need_scores: dict[str, int] = {}
    for need_name, keywords in TASK_PROFILE_NEED_KEYWORDS.items():
        need_scores[need_name] = sum(1 for keyword in keywords if keyword in text)

    primary_need = max(need_scores, key=lambda name: need_scores[name]) if need_scores else 'writing'
    if need_scores.get(primary_need, 0) <= 0:
        primary_need = 'writing'

    secondary_candidates = [
        need_name
        for need_name, score in sorted(need_scores.items(), key=lambda item: item[1], reverse=True)
        if need_name != primary_need and score > 0
    ]
    secondary_needs = secondary_candidates[:2]

    subject_area = 'allgemein'
    subject_best_score = 0
    for subject_name, keywords in TASK_PROFILE_SUBJECT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > subject_best_score:
            subject_best_score = score
            subject_area = subject_name

    output_type = 'allgemein'
    output_best_score = 0
    for output_name, keywords in TASK_PROFILE_OUTPUT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > output_best_score:
            output_best_score = score
            output_type = output_name

    return {
        'primary_need': primary_need,
        'secondary_needs': secondary_needs,
        'subject_area': subject_area,
        'output_type': output_type,
    }


def score_tool_relevance(tool_dict, task_description, task_type, user_skill_level, task_profile):
    best_for_text = str(tool_dict.get('best_for') or '')
    notes_text = str(tool_dict.get('notes') or '')
    category_text = str(tool_dict.get('category') or '').lower()

    task_tokens = _tokenize_meaningful(task_description)
    tool_tokens = _tokenize_meaningful(f'{best_for_text} {notes_text}')

    overlap = task_tokens.intersection(tool_tokens)
    best_for_match_points = min(35, len(overlap) * 5)

    tool_name_lower = str(tool_dict.get('name') or '').lower()
    mapped_needs = []
    for tool_key, needs in TOOL_NEED_MAP.items():
        if tool_key in tool_name_lower:
            mapped_needs = needs
            break

    if mapped_needs:
        task_needs = {task_profile.get('primary_need')} | set(task_profile.get('secondary_needs') or [])
        if task_needs.intersection(mapped_needs):
            need_match_points = 40
        else:
            need_match_points = -20
    else:
        need_match_points = 0

    primary_need = str(task_profile.get('primary_need') or 'writing')
    blacklisted_fragments = TOOL_BLACKLIST.get(primary_need, [])
    if any(fragment in tool_name_lower for fragment in blacklisted_fragments):
        return {
            'total': 0.0,
            'best_for_match': int(best_for_match_points),
            'need_match': int(need_match_points),
            'skill_fit': 0,
            'category_match': 0,
            'rating_bonus': 0.0,
            'primary_need': primary_need,
        }

    tool_skill_level = (tool_dict.get('skill_requirement') or 'Anfänger').strip()
    tool_rank = LEVEL_RANK.get(tool_skill_level, 1)
    user_rank = LEVEL_RANK.get(user_skill_level, 1)
    rank_distance = abs(tool_rank - user_rank)
    if rank_distance == 0:
        skill_fit_points = 25
    elif rank_distance == 1:
        skill_fit_points = 15
    else:
        skill_fit_points = 5

    category_keywords = TASK_TYPE_CATEGORY_KEYWORDS.get(task_type, TASK_TYPE_CATEGORY_KEYWORDS['GENERAL'])
    category_match_points = 25 if any(keyword in category_text for keyword in category_keywords) else 0

    rating_value = tool_dict.get('rating')
    if isinstance(rating_value, (int, float)):
        clamped_rating = max(0.0, min(5.0, float(rating_value)))
        rating_bonus_points = round((clamped_rating / 5.0) * 15.0, 2)
    else:
        rating_bonus_points = 0.0

    total_score = round(best_for_match_points + need_match_points + skill_fit_points + category_match_points + rating_bonus_points, 2)
    total_score = max(0.0, min(100.0, total_score))

    return {
        'total': total_score,
        'best_for_match': int(best_for_match_points),
        'need_match': int(need_match_points),
        'skill_fit': int(skill_fit_points),
        'category_match': int(category_match_points),
        'rating_bonus': float(rating_bonus_points),
        'primary_need': primary_need,
    }


def build_tool_recommendations(
    tools: list,
    task_description: str,
    task_type: str,
    user_level: str,
    tool_scores: dict,
    preferred_names=None,
    max_count=5,
):
    preferred_names = preferred_names or []
    preferred_lower = {name.strip().lower() for name in preferred_names if name}

    detected_domains = detect_domains(task_description)

    if detected_domains and len(tools) > 100:
        # Stage 1: SQL-level domain filter
        from models import Tool as ToolModel
        db_filtered = ToolModel.query.filter(
            db.or_(
                ToolModel.domain.in_(detected_domains),
                ToolModel.domain.is_(None),
                ToolModel.domain == '',
            )
        ).all()
        # Safety fallback: if less than 15 tools found, use all
        working_tools = db_filtered if len(db_filtered) >= 15 else tools
    else:
        working_tools = tools

    task_tokens = _tokenize_meaningful(task_description)

    if len(working_tools) > 50:
        # Stage 2: tag overlap filter
        tag_filtered = []
        for tool in working_tools:
            tool_tags = set((tool.tags or '').lower().replace('-', ' ').split(','))
            tool_tags = {t.strip() for t in tool_tags if t.strip()}
            if tool_tags.intersection(task_tokens) or not tool.tags:
                tag_filtered.append(tool)
            elif (tool.domain or '') in detected_domains:
                tag_filtered.append(tool)
        # Safety: if less than 15 tools pass, skip this filter
        working_tools = tag_filtered if len(tag_filtered) >= 15 else working_tools

    # Stage 3: score_tool_relevance() runs on working_tools
    task_profile = get_task_profile(task_description)

    scored_tools = []
    for tool in working_tools:
        tool_dict = tool.to_dict()
        score_parts = score_tool_relevance(
            tool_dict=tool_dict,
            task_description=task_description,
            task_type=task_type,
            user_skill_level=user_level,
            task_profile=task_profile,
        )
        relevance_score = float(score_parts['total'])

        if tool.name.lower() in preferred_lower:
            relevance_score = min(100.0, relevance_score + 6.0)

        historical_factor = float(tool_scores.get(tool.name, 1.0))
        normalized_historical_bonus = (historical_factor - 1.0) * 10.0
        final_score = round(max(0.0, min(100.0, relevance_score + normalized_historical_bonus)), 2)

        primary_need = str(score_parts.get('primary_need') or task_profile.get('primary_need') or 'writing')
        if score_parts.get('need_match', 0) > 0:
            reason_text = f"Ideal für {primary_need}-Aufgaben"
        else:
            reason_text = f"Passend für {task_type.lower()}-Aufgaben"

        reason_suffixes = []
        if score_parts.get('category_match', 0) > 0:
            reason_suffixes.append('passende Kategorie')

        if score_parts.get('best_for_match', 0) > 0:
            reason_suffixes.append('inhaltlicher Match')

        if score_parts.get('skill_fit', 0) >= 25:
            reason_suffixes.append('passt zu deinem Level')

        if reason_suffixes:
            reason_text = f"{reason_text}, {', '.join(reason_suffixes)}"

        match_reason = reason_text + '.'

        scored_tools.append({
            'name': tool.name,
            'reason': match_reason,
            'url': tool.url or '',
            'match_score': final_score,
            'match_reason': match_reason,
        })

    scored_tools.sort(key=lambda item: item['match_score'], reverse=True)
    top_tools = scored_tools[:max_count]

    WRITING_TOOL_NAMES = ['chatgpt', 'claude', 'microsoft copilot', 'you.com']
    writing_keywords = [
        'schreiben',
        'verfassen',
        'belegarbeit',
        'facharbeit',
        'aufsatz',
        'zusammenfassen',
        'text',
        'hausarbeit',
    ]

    task_text = (task_description or '').lower()
    requires_writing = any(keyword in task_text for keyword in writing_keywords)
    has_writing_tool = any(
        any(fragment in str(item.get('name') or '').lower() for fragment in WRITING_TOOL_NAMES)
        for item in top_tools
    )

    if requires_writing and not has_writing_tool:
        selected_names = {str(item.get('name') or '').strip().lower() for item in top_tools}
        writing_candidates = []

        for tool in working_tools:
            tool_name = (tool.name or '').strip().lower()
            if not tool_name or tool_name in selected_names:
                continue
            if not any(fragment in tool_name for fragment in WRITING_TOOL_NAMES):
                continue

            score_parts = score_tool_relevance(
                tool_dict=tool.to_dict(),
                task_description=task_description,
                task_type=task_type,
                user_skill_level=user_level,
                task_profile=task_profile,
            )
            writing_candidates.append((float(score_parts.get('total', 0.0)), tool))

        writing_candidates.sort(key=lambda item: item[0], reverse=True)

        if writing_candidates and len(top_tools) > 4:
            _, writing_tool = writing_candidates[0]
            guaranteed_entry = {
                'name': writing_tool.name,
                'reason': 'Ideal zum Verfassen und Strukturieren des Textes.',
                'url': writing_tool.url or '',
                'match_score': 55.0,
                'match_reason': 'Ideal zum Verfassen und Strukturieren des Textes.',
            }
            top_tools[4] = guaranteed_entry

    return top_tools


def normalize_recommendation_payload(
    recommendation: dict,
    task_description: str,
    task_type: str,
    confidence: float,
    tools: list,
    skills: list,
    tool_scores: dict,
) -> dict:
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
        task_description=task_description,
        task_type=task_type,
        user_level=user_level,
        tool_scores=tool_scores,
        preferred_names=preferred_names,
    )

    workflow = recommendation.get('workflow') if isinstance(recommendation, dict) else None
    if not isinstance(workflow, list) or not workflow:
        workflow = [
            'Aufgabe praezisieren und Ziel definieren',
            'Passende Tools auswaehlen und strukturiert anwenden',
            'Ergebnis pruefen und verbessern',
        ]

    tips = recommendation.get('tips') if isinstance(recommendation, dict) else None
    if not isinstance(tips, list) or not tips:
        tips = [
            'Arbeite in kleinen, ueberpruefbaren Schritten.',
            'Nutze Quellenpruefung und kurze Zwischen-Reviews.',
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
        alternative_approach = 'Nutze eine manuelle Schritt-fuer-Schritt-Recherche und validiere Zwischenergebnisse mit einer zweiten Quelle.'

    optimized_prompt = recommendation.get('optimized_prompt') if isinstance(recommendation, dict) else None
    if not optimized_prompt:
        optimized_prompt = f'Hilf mir bei dieser Aufgabe: {task_description}. Gib mir einen klaren Workflow mit ueberpruefbaren Zwischenschritten.'

    estimated_time = recommendation.get('estimated_time') if isinstance(recommendation, dict) else None
    if not estimated_time:
        estimated_time = '30-60 Minuten'

    why_these_tools = recommendation.get('why_these_tools') if isinstance(recommendation, dict) else None
    if not why_these_tools:
        why_these_tools = 'Die Tools passen zu Aufgabe, Skill-Level und bisherigen positiven Bewertungen.'

    skill_gap = recommendation.get('skill_gap') if isinstance(recommendation, dict) else None
    if not skill_gap:
        skill_gap = 'Vertiefe die Nutzung fortgeschrittener Prompt-Strategien und Qualitaetskontrolle der Ergebnisse.'

    for tool_entry in recommended_tools:
        if not tool_entry.get('specific_tip'):
            tool_entry['specific_tip'] = 'Starte mit einem kleinen Test-Output und verfeinere anschliessend iterativ.'

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
            'Fuer jedes Teilproblem eine kurze Loesung skizzieren',
            'Ergebnisse zusammenfuehren und final pruefen',
        ],
        'recommended_tools': [],
        'optimized_prompt': f'Bitte unterstuetze mich Schritt fuer Schritt bei: {task_description}',
        'tips': ['Halte den Fokus auf den naechsten konkreten Schritt.'],
        'estimated_time': '20-45 Minuten',
        'difficulty': 'easy',
        'alternative_approach': 'Arbeite ohne KI mit einem klaren 3-Schritte-Plan und einer Checkliste.',
        'why_these_tools': 'Kein spezifisches Tool-Match verfuegbar, daher neutraler Vorgehensplan.',
        'skill_gap': 'Baue systematische Aufgabenanalyse und Prompt-Praezision aus.',
    }


def generate_fallback_recommendation(
    task: str,
    tools: list,
    skills: list,
    task_type: str,
    confidence: float,
    tool_scores: dict,
) -> dict:
    workflow_templates = {
        'IMAGE': ['Motiv und Stil klar definieren', 'Bild mit passendem KI-Tool erzeugen', 'Auswahl treffen und visuell nachbearbeiten'],
        'RESEARCH': ['Kernfrage formulieren', 'Quellen sammeln und vergleichen', 'Erkenntnisse strukturieren und zusammenfassen'],
        'WRITING': ['Gliederung erstellen', 'Entwurf schreiben', 'Stil und Inhalt ueberarbeiten'],
        'MATH': ['Problemtyp identifizieren', 'Loesungsweg Schritt fuer Schritt ausfuehren', 'Ergebnis mit Gegenprobe validieren'],
        'PRESENTATION': ['Kernaussage und Storyline definieren', 'Folienstruktur und Visuals erstellen', 'Probevortrag und Feinschliff'],
        'LEARNING': ['Lernziele und Themen priorisieren', 'Lernbloecke mit Wiederholungen planen', 'Wissensstand mit Mini-Tests pruefen'],
        'CODE': ['Fehler oder Zielzustand praezise beschreiben', 'Loesung schrittweise implementieren', 'Tests/Checks durchfuehren und refaktorisieren'],
        'TRANSLATION': ['Quelltext analysieren', 'Zielsprachliche Übersetzung erstellen', 'Ton, Terminologie und Konsistenz prüfen'],
        'GENERAL': ['Aufgabe in Teilziele aufteilen', 'Teilziele nacheinander umsetzen', 'Qualitaet pruefen und Ergebnis finalisieren'],
    }

    recommendation = {
        'workflow': workflow_templates.get(task_type, workflow_templates['GENERAL']),
        'recommended_tools': [],
        'optimized_prompt': f'Hilf mir bei folgender Aufgabe: {task}. Gib mir einen umsetzbaren Schritt-fuer-Schritt-Plan.',
        'tips': ['Ergebnisse nach jedem Schritt kurz validieren.', 'Bei Unsicherheit mit kleinerem Teilproblem starten.'],
        'estimated_time': '30-60 Minuten',
        'difficulty': 'medium' if confidence >= 0.5 else 'easy',
        'alternative_approach': 'Loese die Aufgabe ohne KI mit einer klaren Checkliste und Peer-Review.',
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


def save_workflow_history(task_description: str, recommendation: dict, area: str = '', subcategory: str = ''):
    history_entry = make_model(
        WorkflowHistory,
        task_description=task_description,
        recommendation_json=json.dumps(recommendation, ensure_ascii=False),
        created_at=datetime.utcnow(),
        user_rating=None,
    )
    db.session.add(history_entry)
    db.session.flush()

    upsert_recommendation_feedback(
        history_entry.id,
        task_description=task_description,
        area=area,
        subcategory=subcategory,
        recommended_tools=extract_recommended_tool_names(recommendation),
    )

    db.session.commit()
    clear_tool_scores_cache()
    return history_entry.id


def call_groq_with_micro_prompt(micro_prompt):
    required_keys = {'verified_tools', 'workflow', 'optimized_prompt', 'tips', 'why_these_tools'}

    models = globals().get('MODELS')
    if not isinstance(models, (list, tuple)) or not models:
        models = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768']

    def _set_error(model_name: str, message: str, http_status=None, code_override: str | None = None, missing_keys=None):
        classified = classify_ai_provider_error(http_status=http_status, provider_message=message, model_name=model_name)
        if code_override:
            classified['code'] = code_override
        if missing_keys:
            classified['missing_keys'] = missing_keys
        logger.info('Micro-prompt attempt fehlgeschlagen: model=%s code=%s', model_name, classified.get('code'))
        return classified

    last_error = classify_ai_provider_error(provider_message='No model attempt executed', model_name='n/a')

    for model_name in models:
        logger.info('Micro-prompt attempt gestartet: model=%s', model_name)
        try:
            response = requests.post(
                GROQ_API_URL,
                headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
                json={
                    'model': model_name,
                    'messages': [
                        {'role': 'user', 'content': micro_prompt},
                    ],
                    'temperature': 0.3,
                    'max_tokens': 600,
                },
                timeout=30,
            )

            if response.status_code != 200:
                try:
                    error_payload = response.json()
                    provider_message = str((error_payload.get('error') or {}).get('message') or error_payload)
                except Exception:
                    provider_message = response.text
                last_error = _set_error(model_name, provider_message, http_status=response.status_code)
                continue

            payload = response.json()
            raw_text = str(((payload.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

            cleaned = raw_text
            if cleaned.startswith('```'):
                cleaned = cleaned.strip('`').strip()
                if cleaned.lower().startswith('json'):
                    cleaned = cleaned[4:].strip()

            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                last_error = _set_error(model_name, 'Micro-prompt response is not valid JSON', http_status=200, code_override='ai_invalid_json')
                continue

            if not isinstance(parsed, dict):
                last_error = _set_error(model_name, 'Micro-prompt response JSON is not an object', http_status=200, code_override='ai_invalid_json_shape')
                continue

            missing_keys = sorted(required_keys.difference(parsed.keys()))
            if missing_keys:
                last_error = _set_error(
                    model_name,
                    f"Micro-prompt JSON missing keys: {', '.join(missing_keys)}",
                    http_status=200,
                    code_override='ai_missing_required_keys',
                    missing_keys=missing_keys,
                )
                continue

            logger.info('Micro-prompt attempt erfolgreich: model=%s', model_name)
            return parsed, model_name, None

        except requests.Timeout:
            last_error = _set_error(model_name, 'timeout')
        except requests.RequestException as request_error:
            last_error = _set_error(model_name, str(request_error))
        except Exception as error:
            last_error = _set_error(model_name, str(error))

    return None, None, last_error


def build_recommendation_response(task_description: str) -> dict:
    task_description = (task_description or '').strip()
    if not task_description:
        raise ValueError('Keine Aufgabenbeschreibung angegeben')

    task_key = task_description.lower()
    now = time.time()

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
            key for key, value in recommendation_cache.items() if now - value['timestamp'] > RECOMMENDATION_DEDUP_TTL
        ]
        for key in expired_keys:
            recommendation_cache.pop(key, None)

    classification = classify_task(task_description)
    task_type = classification['type']
    confidence = classification['confidence']
    area = classification.get('area', 'Schule')
    subcategory = classification.get('subcategory', 'Lernen & Üben')

    skills = Skill.query.order_by(Skill.id.asc()).all()
    goals = Goal.query.order_by(Goal.id.asc()).all()
    tools = Tool.query.order_by(Tool.id.asc()).all()
    tool_scores = get_tool_scores()
    user_context = get_user_context_key_map()
    main_subjects = user_context.get('hauptfaecher') or user_context.get('schule_faecher') or 'nicht angegeben'
    ki_experience = user_context.get('ki_erfahrung') or 'nicht angegeben'

    user_summary = summarize_user_context(skills, goals, user_context)

    all_tool_names = [t.name for t in tools]

    top_tools = build_tool_recommendations(
        tools=tools,
        task_description=task_description,
        task_type=task_type,
        user_level=get_user_level(skills),
        tool_scores=tool_scores,
    )

    task_profile = get_task_profile(task_description)
    detected_domains = detect_domains(task_description)

    micro_prompt = build_micro_prompt(
        task_description=task_description,
        task_profile=task_profile,
        top_tools=top_tools,
        user_summary=user_summary,
        all_tool_names=all_tool_names,
        detected_domains=detected_domains,
    )

    logger.info(
        'Recommendation request gestartet: task_type=%s, area=%s, subcategory=%s, confidence=%s',
        task_type,
        area,
        subcategory,
        confidence,
    )

    recommendation = None
    mode = 'demo'
    model_used = None
    personalization_note = None
    next_step = None
    ai_diagnostics = None
    ai_attempts = []
    fallback_variant = None

    if GROQ_API_KEY and GROQ_API_KEY != 'dein-groq-api-key-hier':
        try:
            ai_result, model_used, ai_error = call_groq_with_micro_prompt(micro_prompt)

            if ai_result is not None:
                mode = 'ai'
                db_tool_map = {t['name']: t for t in top_tools}

                merged_tools = []
                for ai_tool in ai_result.get('verified_tools', []):
                    if not isinstance(ai_tool, dict):
                        continue
                    name = ai_tool.get('name', '')
                    db_data = db_tool_map.get(name, {})
                    merged_tools.append({
                        'name': name,
                        'reason': ai_tool.get('reason', db_data.get('reason', '')),
                        'url': db_data.get('url', ''),
                        'match_score': db_data.get('match_score', 0),
                        'match_reason': ai_tool.get('reason', ''),
                    })

                recommendation = {
                    'recommended_tools': merged_tools,
                    'workflow': ai_result.get('workflow', []),
                    'optimized_prompt': ai_result.get('optimized_prompt', ''),
                    'tips': ai_result.get('tips', []),
                    'why_these_tools': ai_result.get('why_these_tools', ''),
                    'difficulty': 'medium',
                }
                fallback_variant = None
                ai_diagnostics = {
                    'code': 'ai_ok',
                    'user_message': 'KI-Antwort erfolgreich erstellt.',
                    'retryable': False,
                    'provider': 'groq',
                    'model': model_used,
                    'http_status': 200,
                }
            else:
                ai_diagnostics = ai_error
                if isinstance(ai_error, dict):
                    ai_attempts.append(ai_error)

        except requests.Timeout:
            timeout_error = classify_ai_provider_error(provider_message='timeout', model_name='n/a')
            ai_attempts.append(timeout_error)
            ai_diagnostics = timeout_error
            logger.exception('Recommendation step: groq_timeout -> local_fallback')
        except requests.RequestException as request_error:
            network_error = classify_ai_provider_error(provider_message=str(request_error), model_name='n/a')
            ai_attempts.append(network_error)
            ai_diagnostics = network_error
            logger.exception('Recommendation step: groq_request_exception -> local_fallback')
        except Exception as error:
            unknown_error = classify_ai_provider_error(provider_message=str(error), model_name='n/a')
            ai_attempts.append(unknown_error)
            ai_diagnostics = unknown_error
            logger.exception('Recommendation step: groq_exception -> local_fallback')
    else:
        ai_diagnostics = {
            'code': 'ai_api_key_missing',
            'user_message': 'Kein aktiver Groq API-Key gefunden. Es wird der Demo-Fallback genutzt.',
            'retryable': False,
            'provider': 'groq',
            'model': None,
            'http_status': None,
            'provider_message': 'GROQ_API_KEY fehlt oder Platzhalterwert gesetzt',
        }

    if recommendation is None:
        try:
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
            fallback_variant = 'local_rule_based'
        except Exception:
            recommendation = generate_generic_help_recommendation(task_description)
            mode = 'demo'
            model_used = 'fallback_generic_help'
            fallback_variant = 'generic_help'

    if mode == 'ai':
        if not personalization_note:
            fallback_preferred_tool = (
                recommendation.get('recommended_tools', [{}])[0].get('name')
                if recommendation.get('recommended_tools')
                else 'passende Tools'
            )
            preferred_tool = fallback_preferred_tool if isinstance(fallback_preferred_tool, str) and fallback_preferred_tool.strip() else 'passende Tools'
            personalization_note = (
                f"Da {main_subjects} zu deinen Schwerpunkten zaehlen, dein KI-Level auf '{ki_experience}' steht "
                f'und {preferred_tool} haeufig gut zu deinem Workflow passt, ist diese Empfehlung darauf zugeschnitten.'
            )

        if not next_step:
            workflow_steps = recommendation.get('workflow') if isinstance(recommendation, dict) else None
            next_step = workflow_steps[0] if isinstance(workflow_steps, list) and workflow_steps else 'Formuliere jetzt die Aufgabe praezise in einem Satz.'
    else:
        personalization_note = ''
        next_step = ''

    recommendation['personalization_note'] = personalization_note
    recommendation['next_step'] = next_step

    history_id = save_workflow_history(task_description, recommendation, area=area, subcategory=subcategory)

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
        'classification': {'type': task_type, 'confidence': confidence},
        'ai_diagnostics': ai_diagnostics,
        'ai_attempts': ai_attempts[:3],
        'fallback_variant': fallback_variant,
        'fallback_reason': ai_diagnostics.get('code') if mode != 'ai' and isinstance(ai_diagnostics, dict) else None,
    }

    with recommendation_cache_lock:
        recommendation_cache[task_key] = {'timestamp': now, 'payload': response_payload}

    return response_payload


def clear_tool_scores_cache() -> None:
    get_tool_scores.cache_clear()


def get_recommendation():
    data = request.get_json(silent=True) or {}
    task_description = (data.get('task_description') or '').strip()

    if not task_description:
        return jsonify({
            'error': 'Keine Aufgabenbeschreibung angegeben',
            'error_code': 'invalid_task_description',
            'details': {
                'hint': 'Sende task_description als nicht-leeren String.',
            },
        }), 400

    try:
        response_payload = build_recommendation_response(task_description)
        return jsonify(response_payload)
    except ValueError as value_error:
        return jsonify({'error': str(value_error), 'error_code': 'invalid_request'}), 400
    except Exception as err:
        logger.exception(f'Recommendation endpoint failed: {err}')
        return jsonify({
            'error': 'Interner Fehler bei der Empfehlungserstellung',
            'error_code': 'recommendation_internal_error',
            'details': {
                'exception_type': err.__class__.__name__,
                'hint': 'Backend-Logs pruefen und Anfrage erneut versuchen.',
            },
        }), 500
