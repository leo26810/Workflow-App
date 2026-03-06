from flask import jsonify, request

from models import SubCategory, TaskTemplate, WorkflowCategory
from services.data_cache_service import get_tools_page_cached


def get_categories():
    categories = WorkflowCategory.query.order_by(WorkflowCategory.id.asc()).all()
    payload = []

    for category in categories:
        category_payload = category.to_dict()
        category_payload['subcategories'] = []

        subcategories = SubCategory.query.filter_by(category_id=category.id).order_by(SubCategory.id.asc()).all()
        for subcategory in subcategories:
            sub_payload = subcategory.to_dict()
            templates = TaskTemplate.query.filter_by(subcategory_id=subcategory.id).order_by(TaskTemplate.id.asc()).all()
            sub_payload['task_templates'] = [template.to_dict() for template in templates]
            category_payload['subcategories'].append(sub_payload)

        payload.append(category_payload)

    return jsonify(payload)


def get_task_templates():
    subcategory_name = (request.args.get('subcategory') or '').strip()
    if not subcategory_name:
        return jsonify({'error': 'Parameter subcategory fehlt'}), 400

    subcategory = SubCategory.query.filter_by(name=subcategory_name).first()
    if not subcategory:
        return jsonify({'error': 'Unterkategorie nicht gefunden'}), 404

    templates = TaskTemplate.query.filter_by(subcategory_id=subcategory.id).order_by(TaskTemplate.id.asc()).all()
    return jsonify({
        'subcategory': subcategory.name,
        'templates': [template.to_dict() for template in templates]
    })


def get_tools_list():
    try:
        page = max(1, int(str(request.args.get('page', '1')).strip()))
    except (TypeError, ValueError):
        page = 1

    try:
        limit = max(1, min(500, int(str(request.args.get('limit', '20')).strip())))
    except (TypeError, ValueError):
        limit = 20

    return jsonify(get_tools_page_cached(page, limit))
