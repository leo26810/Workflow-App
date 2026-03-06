import logging


logger = logging.getLogger(__name__)


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

    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    return [name for name, _score in sorted_domains[:2]]


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
