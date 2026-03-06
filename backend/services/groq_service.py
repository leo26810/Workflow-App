def build_recommendation_response(task_description: str):
    from services.recommendation_service import build_recommendation_response as build_recommendation

    return build_recommendation(task_description)


def get_recommendation_handler():
    from services.recommendation_service import get_recommendation

    return get_recommendation()


def recommendation_feedback_handler():
    from services.history_service import save_recommendation_feedback

    return save_recommendation_feedback()


def clear_tool_scores_cache():
    from services.recommendation_service import clear_tool_scores_cache as clear_cache

    clear_cache()
