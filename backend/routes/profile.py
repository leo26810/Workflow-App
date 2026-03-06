from flask import Blueprint, jsonify

from models import Goal, Skill
from services.profile_service import get_profile, get_user_context, set_user_context, update_profile


profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/api/profile', methods=['GET'])
def profile_get_route():
    return get_profile()


@profile_bp.route('/api/profile', methods=['POST'])
def profile_post_route():
    return update_profile()


@profile_bp.route('/api/user-context', methods=['GET'])
def user_context_get_route():
    return get_user_context()


@profile_bp.route('/api/user-context', methods=['POST'])
def user_context_post_route():
    return set_user_context()


@profile_bp.route('/api/skills', methods=['GET'])
def skills_get_route():
    skills = Skill.query.order_by(Skill.id.asc()).all()
    return jsonify([item.to_dict() for item in skills])


@profile_bp.route('/api/goals', methods=['GET'])
def goals_get_route():
    goals = Goal.query.order_by(Goal.id.asc()).all()
    return jsonify([item.to_dict() for item in goals])
