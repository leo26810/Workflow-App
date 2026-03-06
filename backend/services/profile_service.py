from flask import jsonify, request

from extensions import db
from models import Goal, Skill, Tool, User, UserContext, make_model
from services.data_cache_service import clear_data_caches, get_profile_payload_cached


def get_profile():
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    try:
        limit = max(1, min(100, int(request.args.get('limit', 20))))
    except ValueError:
        limit = 20

    return jsonify(get_profile_payload_cached(page, limit))


def update_profile():
    data = request.get_json() or {}
    action = data.get('action')

    if action == 'add_skill':
        skill = make_model(Skill, name=data['name'], level=data.get('level', 'Anfänger'))
        db.session.add(skill)
        db.session.commit()
        clear_data_caches()
        return jsonify({'success': True, 'skill': skill.to_dict()})

    if action == 'delete_skill':
        skill = Skill.query.get(data['id'])
        if skill:
            db.session.delete(skill)
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})

    if action == 'add_goal':
        goal = make_model(Goal, description=data['description'])
        db.session.add(goal)
        db.session.commit()
        clear_data_caches()
        return jsonify({'success': True, 'goal': goal.to_dict()})

    if action == 'delete_goal':
        goal = Goal.query.get(data['id'])
        if goal:
            db.session.delete(goal)
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})

    if action == 'update_name':
        user = User.query.first()
        if user:
            user.name = data['name']
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})

    if action == 'add_tool':
        tool = make_model(
            Tool,
            name=data['name'],
            category=data.get('category', 'Allgemein'),
            url=data.get('url', ''),
            notes=data.get('notes', '')
        )
        db.session.add(tool)
        db.session.commit()
        clear_data_caches()
        return jsonify({'success': True, 'tool': tool.to_dict()})

    if action == 'delete_tool':
        tool = Tool.query.get(data['id'])
        if tool:
            db.session.delete(tool)
            db.session.commit()
            clear_data_caches()
        return jsonify({'success': True})

    return jsonify({'error': 'Unbekannte Aktion'}), 400


def get_user_context():
    context_items = UserContext.query.order_by(UserContext.area.asc(), UserContext.key.asc()).all()
    return jsonify([item.to_dict() for item in context_items])


def set_user_context():
    data = request.get_json() or {}
    area = (data.get('area') or '').strip()
    key = (data.get('key') or '').strip()
    value = data.get('value')

    if not area or not key:
        return jsonify({'error': 'area und key sind erforderlich'}), 400

    context_item = UserContext.query.filter_by(area=area, key=key).first()
    if not context_item:
        context_item = make_model(UserContext, area=area, key=key, value='' if value is None else str(value))
        db.session.add(context_item)
    else:
        context_item.value = '' if value is None else str(value)

    db.session.commit()
    return jsonify({'success': True, 'item': context_item.to_dict()})
