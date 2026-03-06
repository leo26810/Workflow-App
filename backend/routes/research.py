from flask import Blueprint

from services.research_service import create_research_session, get_research_sessions


research_bp = Blueprint('research', __name__)


@research_bp.route('/api/research-session', methods=['POST'])
def research_session_create_route():
    return create_research_session()


@research_bp.route('/api/research-sessions', methods=['GET'])
def research_sessions_get_route():
    return get_research_sessions()