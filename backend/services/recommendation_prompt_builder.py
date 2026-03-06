from models import UserContext
from services.recommendation_classification import get_task_profile
from services.recommendation_scoring import build_tool_recommendations, get_user_level


def get_user_context_key_map() -> dict:
    key_map = {}
    context_items = UserContext.query.order_by(UserContext.area.asc(), UserContext.key.asc()).all()
    for item in context_items:
        key_map[item.key] = item.value
    return key_map


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
