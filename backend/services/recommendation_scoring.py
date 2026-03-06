import json
from functools import lru_cache

from extensions import db
from models import Tool, WorkflowHistory
from services.feedback_service import extract_recommended_tool_names
from services.recommendation_classification import (
    LEVEL_RANK,
    TASK_TYPE_CATEGORY_KEYWORDS,
    _tokenize_meaningful,
    detect_domains,
    get_task_profile,
)
from utils.cache_utils import ttl_cache


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
        from models import Tool as ToolModel

        db_filtered = ToolModel.query.filter(
            db.or_(
                ToolModel.domain.in_(detected_domains),
                ToolModel.domain.is_(None),
                ToolModel.domain == '',
            )
        ).all()
        working_tools = db_filtered if len(db_filtered) >= 15 else tools
    else:
        working_tools = tools

    task_tokens = _tokenize_meaningful(task_description)

    if len(working_tools) > 50:
        tag_filtered = []
        for tool in working_tools:
            tool_tags = set((tool.tags or '').lower().replace('-', ' ').split(','))
            tool_tags = {t.strip() for t in tool_tags if t.strip()}
            if tool_tags.intersection(task_tokens) or not tool.tags:
                tag_filtered.append(tool)
            elif (tool.domain or '') in detected_domains:
                tag_filtered.append(tool)
        working_tools = tag_filtered if len(tag_filtered) >= 15 else working_tools

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
