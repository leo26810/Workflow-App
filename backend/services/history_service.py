import json

from flask import jsonify, request

from extensions import db
from models import RecommendationFeedback, WorkflowHistory
from services.feedback_service import extract_recommended_tool_names, upsert_recommendation_feedback
from services.groq_service import clear_tool_scores_cache


def save_recommendation_feedback():
    if request.method == 'GET':
        try:
            page = max(1, int(str(request.args.get('page', '1')).strip()))
        except (TypeError, ValueError):
            page = 1

        try:
            limit = max(1, min(200, int(str(request.args.get('limit', '50')).strip())))
        except (TypeError, ValueError):
            limit = 50

        search_term = (request.args.get('search') or '').strip().lower()
        min_rating = request.args.get('min_rating')
        offset = (page - 1) * limit

        query = RecommendationFeedback.query.order_by(RecommendationFeedback.updated_at.desc())
        all_rows = query.all()

        filtered_rows = []
        for row in all_rows:
            if min_rating is not None:
                try:
                    minimum = int(str(min_rating).strip())
                    if row.user_rating is None or row.user_rating < minimum:
                        continue
                except (TypeError, ValueError):
                    pass

            if search_term:
                haystack = ' '.join([
                    str(row.task_description or ''),
                    str(row.area or ''),
                    str(row.subcategory or ''),
                    ' '.join(row.recommended_tools_json or []),
                    str(row.note or ''),
                ]).lower()
                if search_term not in haystack:
                    continue

            filtered_rows.append(row)

        page_rows = filtered_rows[offset:offset + limit]

        payload = []
        for row in page_rows:
            item = row.to_dict()
            history_entry = WorkflowHistory.query.get(row.workflow_history_id)
            if history_entry:
                item['history'] = {
                    'id': history_entry.id,
                    'task_description': history_entry.task_description,
                    'created_at': history_entry.created_at.isoformat() if history_entry.created_at else None,
                    'user_rating': history_entry.user_rating,
                    'recommendation_json': history_entry.recommendation_json,
                }
            payload.append(item)

        return jsonify({
            'items': payload,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(filtered_rows),
                'pages': (len(filtered_rows) + limit - 1) // limit,
            }
        })

    data = request.get_json(silent=True) or {}

    workflow_history_id_raw = data.get('workflow_history_id', data.get('id'))
    if workflow_history_id_raw is None:
        return jsonify({'error': 'workflow_history_id ist erforderlich'}), 400

    try:
        workflow_history_id = int(str(workflow_history_id_raw).strip())
    except (TypeError, ValueError):
        return jsonify({'error': 'workflow_history_id muss numerisch sein'}), 400

    history_entry = WorkflowHistory.query.get(workflow_history_id)
    if not history_entry:
        return jsonify({'error': 'Workflow-History-Eintrag nicht gefunden'}), 404

    user_rating = data.get('user_rating', data.get('rating'))
    accepted = data.get('accepted')
    reused = data.get('reused')
    time_saved_minutes = data.get('time_saved_minutes')
    note = data.get('note')

    if user_rating is not None:
        try:
            user_rating = int(str(user_rating).strip())
        except (TypeError, ValueError):
            return jsonify({'error': 'user_rating muss numerisch sein'}), 400
        if user_rating < 1 or user_rating > 5:
            return jsonify({'error': 'user_rating muss zwischen 1 und 5 liegen'}), 400

    if time_saved_minutes is not None:
        try:
            time_saved_minutes = int(str(time_saved_minutes).strip())
        except (TypeError, ValueError):
            return jsonify({'error': 'time_saved_minutes muss numerisch sein'}), 400
        if time_saved_minutes < 0:
            return jsonify({'error': 'time_saved_minutes muss >= 0 sein'}), 400

    if accepted is not None and not isinstance(accepted, bool):
        return jsonify({'error': 'accepted muss true/false sein'}), 400
    if reused is not None and not isinstance(reused, bool):
        return jsonify({'error': 'reused muss true/false sein'}), 400

    if user_rating is not None:
        history_entry.user_rating = user_rating

    try:
        recommendation_data = json.loads(history_entry.recommendation_json or '{}')
    except json.JSONDecodeError:
        recommendation_data = {}

    feedback_entry = upsert_recommendation_feedback(
        workflow_history_id,
        task_description=history_entry.task_description,
        recommended_tools=extract_recommended_tool_names(recommendation_data),
        user_rating=user_rating,
        accepted=accepted,
        reused=reused,
        time_saved_minutes=time_saved_minutes,
        note=note,
    )

    db.session.commit()
    clear_tool_scores_cache()

    return jsonify({'success': True, 'feedback': feedback_entry.to_dict()})


def update_workflow_history():
    if request.method == 'GET':
        entries = WorkflowHistory.query.order_by(WorkflowHistory.created_at.desc()).limit(20).all()
        return jsonify([entry.to_dict() for entry in entries])

    data = request.get_json() or {}

    workflow_history_id_raw = data.get('id', data.get('workflow_history_id'))
    user_rating_raw = data.get('rating', data.get('user_rating'))
    if workflow_history_id_raw is None or user_rating_raw is None:
        return jsonify({'error': 'id/workflow_history_id und rating/user_rating müssen numerisch sein'}), 400

    try:
        workflow_history_id = int(str(workflow_history_id_raw).strip())
        user_rating = int(str(user_rating_raw).strip())
    except (TypeError, ValueError):
        return jsonify({'error': 'id/workflow_history_id und rating/user_rating müssen numerisch sein'}), 400

    if user_rating < 1 or user_rating > 5:
        return jsonify({'error': 'user_rating muss zwischen 1 und 5 liegen'}), 400

    history_entry = WorkflowHistory.query.get(workflow_history_id)
    if not history_entry:
        return jsonify({'error': 'Workflow-History-Eintrag nicht gefunden'}), 404

    history_entry.user_rating = user_rating
    try:
        recommendation_data = json.loads(history_entry.recommendation_json or '{}')
    except json.JSONDecodeError:
        recommendation_data = {}

    upsert_recommendation_feedback(
        workflow_history_id,
        task_description=history_entry.task_description,
        recommended_tools=extract_recommended_tool_names(recommendation_data),
        user_rating=user_rating,
        accepted=(user_rating >= 4),
        reused=(user_rating >= 4),
        time_saved_minutes=30 if user_rating >= 4 else 10,
        note='Auto-sync from workflow-history rating',
    )

    db.session.commit()
    clear_tool_scores_cache()

    return jsonify({
        'success': True,
        'id': workflow_history_id,
        'rating': user_rating,
        'workflow_history_id': workflow_history_id,
        'user_rating': user_rating,
    })
