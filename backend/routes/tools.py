from flask import Blueprint

from services.tools_service import get_categories, get_task_templates, get_tools_list


tools_bp = Blueprint('tools', __name__)


@tools_bp.route('/api/categories', methods=['GET'])
def categories_get_route():
    return get_categories()


@tools_bp.route('/api/task-templates', methods=['GET'])
def task_templates_get_route():
    return get_task_templates()


@tools_bp.route('/api/tools', methods=['GET'])
def tools_get_route():
    return get_tools_list()
