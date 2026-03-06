from flask import jsonify, request

from extensions import db
from models import ResearchSession, make_model


def create_research_session():
    data = request.get_json() or {}

    query = (data.get('query') or '').strip()
    sources = data.get('sources')
    summary = (data.get('summary') or '').strip()
    tags = (data.get('tags') or '').strip()

    if not query:
        return jsonify({'error': 'query ist erforderlich'}), 400
    if not isinstance(sources, list):
        return jsonify({'error': 'sources muss ein JSON-Array sein'}), 400

    session = make_model(
        ResearchSession,
        query=query,
        sources=sources,
        summary=summary,
        tags=tags,
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({'success': True, 'session': session.to_dict()})


def get_research_sessions():
    sessions = db.session.query(ResearchSession).order_by(ResearchSession.created_at.desc()).all()
    return jsonify([session.to_dict() for session in sessions])