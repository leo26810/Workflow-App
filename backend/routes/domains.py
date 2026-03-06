from flask import Blueprint, jsonify
from models import Domain, WorkflowCategory


domains_bp = Blueprint('domains', __name__)


@domains_bp.route('/api/domains', methods=['GET'])
def get_domains():
    domains = Domain.query.order_by(Domain.sort_order.asc()).all()
    result = []
    for domain in domains:
        d = domain.to_dict()
        d['categories'] = [
            c.to_dict() for c in
            WorkflowCategory.query.filter_by(domain_id=domain.id)
            .order_by(WorkflowCategory.name.asc()).all()
        ]
        result.append(d)
    return jsonify({'domains': result, 'total': len(result)})
