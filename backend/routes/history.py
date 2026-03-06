from flask import Blueprint, jsonify

from models import WorkflowHistory
from services.history_service import update_workflow_history


history_bp = Blueprint('history', __name__)


@history_bp.route('/api/workflow-history', methods=['GET', 'POST'])
def workflow_history_route():
    return update_workflow_history()


@history_bp.route('/api/workflow-history/<int:history_id>', methods=['GET'])
def workflow_history_item_route(history_id: int):
    entry = WorkflowHistory.query.get(history_id)
    if not entry:
        return jsonify({'error': 'Workflow-History-Eintrag nicht gefunden'}), 404
    return jsonify(entry.to_dict())
