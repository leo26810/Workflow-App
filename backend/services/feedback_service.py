from extensions import db
from models import RecommendationFeedback, make_model


def get_feedback_for_history(workflow_history_id: int):
    return RecommendationFeedback.query.filter_by(workflow_history_id=workflow_history_id).first()


def extract_recommended_tool_names(recommendation_data: dict) -> list[str]:
    if not isinstance(recommendation_data, dict):
        return []

    recommended_tools = recommendation_data.get('recommended_tools', [])
    names = []
    for recommended_tool in recommended_tools:
        if isinstance(recommended_tool, dict):
            name = (recommended_tool.get('name') or '').strip()
        elif isinstance(recommended_tool, str):
            name = recommended_tool.strip()
        else:
            name = ''
        if name:
            names.append(name)

    return names


def upsert_recommendation_feedback(
    workflow_history_id: int,
    *,
    task_description: str | None = None,
    area: str | None = None,
    subcategory: str | None = None,
    recommended_tools: list[str] | None = None,
    user_rating: int | None = None,
    accepted: bool | None = None,
    reused: bool | None = None,
    time_saved_minutes: int | None = None,
    note: str | None = None,
):
    feedback = get_feedback_for_history(workflow_history_id)
    if not feedback:
        feedback = make_model(
            RecommendationFeedback,
            workflow_history_id=workflow_history_id,
            recommended_tools_json=[],
        )
        db.session.add(feedback)

    if task_description is not None:
        feedback.task_description = task_description.strip()[:1000]
    if area is not None:
        feedback.area = area.strip()[:100]
    if subcategory is not None:
        feedback.subcategory = subcategory.strip()[:150]
    if recommended_tools is not None:
        feedback.recommended_tools_json = [name.strip() for name in recommended_tools if isinstance(name, str) and name.strip()][:20]
    if user_rating is not None:
        feedback.user_rating = user_rating
    if accepted is not None:
        feedback.accepted = accepted
    if reused is not None:
        feedback.reused = reused
    if time_saved_minutes is not None:
        feedback.time_saved_minutes = max(0, min(24 * 60, int(time_saved_minutes)))
    if note is not None:
        feedback.note = note.strip()[:1000]

    return feedback
