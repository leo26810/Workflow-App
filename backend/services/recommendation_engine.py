import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

import requests
from flask import jsonify, request

from extensions import db
from models import Goal, Skill, Tool, WorkflowHistory, make_model
from services.feedback_service import extract_recommended_tool_names, upsert_recommendation_feedback
from services.recommendation_classification import (
    classify_ai_provider_error,
    classify_task,
    detect_domains,
    get_task_profile,
)
from services.recommendation_prompt_builder import (
    build_micro_prompt,
    generate_fallback_recommendation,
    generate_generic_help_recommendation,
    get_user_context_key_map,
    summarize_user_context,
)
from services.recommendation_scoring import build_tool_recommendations, get_tool_scores, get_user_level


logger = logging.getLogger(__name__)
GROQ_API_KEY = (os.environ.get('GROQ_API_KEY') or '').strip()
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

recommendation_cache = {}
recommendation_cache_lock = threading.Lock()
RECOMMENDATION_DEDUP_TTL = 60


def save_workflow_history(task_description: str, recommendation: dict, area: str = '', subcategory: str = ''):
    history_entry = make_model(
        WorkflowHistory,
        task_description=task_description,
        recommendation_json=json.dumps(recommendation, ensure_ascii=False),
        created_at=datetime.now(timezone.utc),
        user_rating=None,
    )
    db.session.add(history_entry)
    db.session.flush()

    upsert_recommendation_feedback(
        history_entry.id,
        task_description=task_description,
        area=area,
        subcategory=subcategory,
        recommended_tools=extract_recommended_tool_names(recommendation),
    )

    db.session.commit()
    clear_tool_scores_cache()
    return history_entry.id


def call_groq_with_micro_prompt(micro_prompt):
    required_keys = {'verified_tools', 'workflow', 'optimized_prompt', 'tips', 'why_these_tools'}

    models = globals().get('MODELS')
    if not isinstance(models, (list, tuple)) or not models:
        models = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768']

    def _set_error(model_name: str, message: str, http_status=None, code_override: str | None = None, missing_keys=None):
        classified = classify_ai_provider_error(http_status=http_status, provider_message=message, model_name=model_name)
        if code_override:
            classified['code'] = code_override
        if missing_keys:
            classified['missing_keys'] = missing_keys
        logger.info('Micro-prompt attempt fehlgeschlagen: model=%s code=%s', model_name, classified.get('code'))
        return classified

    last_error = classify_ai_provider_error(provider_message='No model attempt executed', model_name='n/a')

    for model_name in models:
        logger.info('Micro-prompt attempt gestartet: model=%s', model_name)
        try:
            response = requests.post(
                GROQ_API_URL,
                headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
                json={
                    'model': model_name,
                    'messages': [
                        {'role': 'user', 'content': micro_prompt},
                    ],
                    'temperature': 0.3,
                    'max_tokens': 600,
                },
                timeout=30,
            )

            if response.status_code != 200:
                try:
                    error_payload = response.json()
                    provider_message = str((error_payload.get('error') or {}).get('message') or error_payload)
                except Exception:
                    provider_message = response.text
                last_error = _set_error(model_name, provider_message, http_status=response.status_code)
                continue

            payload = response.json()
            raw_text = str(((payload.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

            cleaned = raw_text
            if cleaned.startswith('```'):
                cleaned = cleaned.strip('`').strip()
                if cleaned.lower().startswith('json'):
                    cleaned = cleaned[4:].strip()

            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                last_error = _set_error(model_name, 'Micro-prompt response is not valid JSON', http_status=200, code_override='ai_invalid_json')
                continue

            if not isinstance(parsed, dict):
                last_error = _set_error(model_name, 'Micro-prompt response JSON is not an object', http_status=200, code_override='ai_invalid_json_shape')
                continue

            missing_keys = sorted(required_keys.difference(parsed.keys()))
            if missing_keys:
                last_error = _set_error(
                    model_name,
                    f"Micro-prompt JSON missing keys: {', '.join(missing_keys)}",
                    http_status=200,
                    code_override='ai_missing_required_keys',
                    missing_keys=missing_keys,
                )
                continue

            logger.info('Micro-prompt attempt erfolgreich: model=%s', model_name)
            return parsed, model_name, None

        except requests.Timeout:
            last_error = _set_error(model_name, 'timeout')
        except requests.RequestException as request_error:
            last_error = _set_error(model_name, str(request_error))
        except Exception as error:
            last_error = _set_error(model_name, str(error))

    return None, None, last_error


def build_recommendation_response(task_description: str) -> dict:
    task_description = (task_description or '').strip()
    if not task_description:
        raise ValueError('Keine Aufgabenbeschreibung angegeben')

    task_key = task_description.lower()
    now = time.time()

    with recommendation_cache_lock:
        existing = recommendation_cache.get(task_key)
        if (
            existing
            and now - existing['timestamp'] <= RECOMMENDATION_DEDUP_TTL
            and isinstance(existing.get('payload'), dict)
            and 'area' in existing['payload']
            and 'subcategory' in existing['payload']
            and 'personalization_note' in existing['payload']
            and 'next_step' in existing['payload']
        ):
            return existing['payload']

        expired_keys = [
            key for key, value in recommendation_cache.items() if now - value['timestamp'] > RECOMMENDATION_DEDUP_TTL
        ]
        for key in expired_keys:
            recommendation_cache.pop(key, None)

    classification = classify_task(task_description)
    task_type = classification['type']
    confidence = classification['confidence']
    area = classification.get('area', 'Schule')
    subcategory = classification.get('subcategory', 'Lernen & Üben')

    skills = Skill.query.order_by(Skill.id.asc()).all()
    goals = Goal.query.order_by(Goal.id.asc()).all()
    tools = Tool.query.order_by(Tool.id.asc()).all()
    tool_scores = get_tool_scores()
    user_context = get_user_context_key_map()
    main_subjects = user_context.get('hauptfaecher') or user_context.get('schule_faecher') or 'nicht angegeben'
    ki_experience = user_context.get('ki_erfahrung') or 'nicht angegeben'

    user_summary = summarize_user_context(skills, goals, user_context)

    all_tool_names = [t.name for t in tools]

    top_tools = build_tool_recommendations(
        tools=tools,
        task_description=task_description,
        task_type=task_type,
        user_level=get_user_level(skills),
        tool_scores=tool_scores,
    )

    task_profile = get_task_profile(task_description)
    detected_domains = detect_domains(task_description)

    micro_prompt = build_micro_prompt(
        task_description=task_description,
        task_profile=task_profile,
        top_tools=top_tools,
        user_summary=user_summary,
        all_tool_names=all_tool_names,
        detected_domains=detected_domains,
    )

    logger.info(
        'Recommendation request gestartet: task_type=%s, area=%s, subcategory=%s, confidence=%s',
        task_type,
        area,
        subcategory,
        confidence,
    )

    recommendation = None
    mode = 'demo'
    model_used = None
    personalization_note = None
    next_step = None
    ai_diagnostics = None
    ai_attempts = []
    fallback_variant = None

    if GROQ_API_KEY and GROQ_API_KEY != 'dein-groq-api-key-hier':
        try:
            ai_result, model_used, ai_error = call_groq_with_micro_prompt(micro_prompt)

            if ai_result is not None:
                mode = 'ai'
                db_tool_map = {t['name']: t for t in top_tools}

                merged_tools = []
                for ai_tool in ai_result.get('verified_tools', []):
                    if not isinstance(ai_tool, dict):
                        continue
                    name = ai_tool.get('name', '')
                    db_data = db_tool_map.get(name, {})
                    merged_tools.append({
                        'name': name,
                        'reason': ai_tool.get('reason', db_data.get('reason', '')),
                        'url': db_data.get('url', ''),
                        'match_score': db_data.get('match_score', 0),
                        'match_reason': ai_tool.get('reason', ''),
                    })

                recommendation = {
                    'recommended_tools': merged_tools,
                    'workflow': ai_result.get('workflow', []),
                    'optimized_prompt': ai_result.get('optimized_prompt', ''),
                    'tips': ai_result.get('tips', []),
                    'why_these_tools': ai_result.get('why_these_tools', ''),
                    'difficulty': 'medium',
                }
                fallback_variant = None
                ai_diagnostics = {
                    'code': 'ai_ok',
                    'user_message': 'KI-Antwort erfolgreich erstellt.',
                    'retryable': False,
                    'provider': 'groq',
                    'model': model_used,
                    'http_status': 200,
                }
            else:
                ai_diagnostics = ai_error
                if isinstance(ai_error, dict):
                    ai_attempts.append(ai_error)

        except requests.Timeout:
            timeout_error = classify_ai_provider_error(provider_message='timeout', model_name='n/a')
            ai_attempts.append(timeout_error)
            ai_diagnostics = timeout_error
            logger.exception('Recommendation step: groq_timeout -> local_fallback')
        except requests.RequestException as request_error:
            network_error = classify_ai_provider_error(provider_message=str(request_error), model_name='n/a')
            ai_attempts.append(network_error)
            ai_diagnostics = network_error
            logger.exception('Recommendation step: groq_request_exception -> local_fallback')
        except Exception as error:
            unknown_error = classify_ai_provider_error(provider_message=str(error), model_name='n/a')
            ai_attempts.append(unknown_error)
            ai_diagnostics = unknown_error
            logger.exception('Recommendation step: groq_exception -> local_fallback')
    else:
        ai_diagnostics = {
            'code': 'ai_api_key_missing',
            'user_message': 'Kein aktiver Groq API-Key gefunden. Es wird der Demo-Fallback genutzt.',
            'retryable': False,
            'provider': 'groq',
            'model': None,
            'http_status': None,
            'provider_message': 'GROQ_API_KEY fehlt oder Platzhalterwert gesetzt',
        }

    if recommendation is None:
        try:
            recommendation = generate_fallback_recommendation(
                task=task_description,
                tools=tools,
                skills=skills,
                task_type=task_type,
                confidence=confidence,
                tool_scores=tool_scores,
            )
            mode = 'demo'
            model_used = 'fallback_local_rule_based'
            fallback_variant = 'local_rule_based'
        except Exception:
            recommendation = generate_generic_help_recommendation(task_description)
            mode = 'demo'
            model_used = 'fallback_generic_help'
            fallback_variant = 'generic_help'

    if mode == 'ai':
        if not personalization_note:
            fallback_preferred_tool = (
                recommendation.get('recommended_tools', [{}])[0].get('name')
                if recommendation.get('recommended_tools')
                else 'passende Tools'
            )
            preferred_tool = fallback_preferred_tool if isinstance(fallback_preferred_tool, str) and fallback_preferred_tool.strip() else 'passende Tools'
            personalization_note = (
                f"Da {main_subjects} zu deinen Schwerpunkten zaehlen, dein KI-Level auf '{ki_experience}' steht "
                f'und {preferred_tool} haeufig gut zu deinem Workflow passt, ist diese Empfehlung darauf zugeschnitten.'
            )

        if not next_step:
            workflow_steps = recommendation.get('workflow') if isinstance(recommendation, dict) else None
            next_step = workflow_steps[0] if isinstance(workflow_steps, list) and workflow_steps else 'Formuliere jetzt die Aufgabe praezise in einem Satz.'
    else:
        personalization_note = ''
        next_step = ''

    recommendation['personalization_note'] = personalization_note
    recommendation['next_step'] = next_step

    history_id = save_workflow_history(task_description, recommendation, area=area, subcategory=subcategory)

    response_payload = {
        'task': task_description,
        'recommendation': recommendation,
        'mode': mode,
        'model_used': model_used,
        'history_id': history_id,
        'area': area,
        'subcategory': subcategory,
        'personalization_note': personalization_note,
        'next_step': next_step,
        'classification': {'type': task_type, 'confidence': confidence},
        'ai_diagnostics': ai_diagnostics,
        'ai_attempts': ai_attempts[:3],
        'fallback_variant': fallback_variant,
        'fallback_reason': ai_diagnostics.get('code') if mode != 'ai' and isinstance(ai_diagnostics, dict) else None,
    }

    with recommendation_cache_lock:
        recommendation_cache[task_key] = {'timestamp': now, 'payload': response_payload}

    return response_payload


def clear_tool_scores_cache() -> None:
    get_tool_scores.cache_clear()


def get_recommendation():
    data = request.get_json(silent=True) or {}
    task_description = (data.get('task_description') or '').strip()

    if not task_description:
        return jsonify({
            'error': 'Keine Aufgabenbeschreibung angegeben',
            'error_code': 'invalid_task_description',
            'details': {
                'hint': 'Sende task_description als nicht-leeren String.',
            },
        }), 400

    try:
        response_payload = build_recommendation_response(task_description)
        return jsonify(response_payload)
    except ValueError as value_error:
        return jsonify({'error': str(value_error), 'error_code': 'invalid_request'}), 400
    except Exception as err:
        logger.exception(f'Recommendation endpoint failed: {err}')
        return jsonify({
            'error': 'Interner Fehler bei der Empfehlungserstellung',
            'error_code': 'recommendation_internal_error',
            'details': {
                'exception_type': err.__class__.__name__,
                'hint': 'Backend-Logs pruefen und Anfrage erneut versuchen.',
            },
        }), 500
