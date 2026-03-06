from flask import Blueprint

from services.history_service import save_recommendation_feedback
from services.recommendation_service import get_recommendation


recommendations_bp = Blueprint('recommendations', __name__)


@recommendations_bp.route('/api/recommendation', methods=['POST'])
def recommendation_route():
    return get_recommendation()


@recommendations_bp.route('/api/recommendation-feedback', methods=['GET', 'POST'])
def recommendation_feedback_route():
    return save_recommendation_feedback()
