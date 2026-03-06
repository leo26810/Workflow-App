import html
import json
import logging
import os
import queue
import threading
import time

import requests
from flask import jsonify, request

from models import WorkflowHistory
from services.groq_service import build_recommendation_response
from services.kpi_service import ensure_kpi_scheduler_started


logger = logging.getLogger(__name__)
TELEGRAM_BOT_TOKEN = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
TELEGRAM_WEBHOOK_SECRET = (os.environ.get('TELEGRAM_WEBHOOK_SECRET') or '').strip()
TELEGRAM_ALLOWED_CHAT_IDS = (os.environ.get('TELEGRAM_ALLOWED_CHAT_IDS') or '').strip()
TELEGRAM_WEBHOOK_PATH = '/api/telegram/webhook'
TELEGRAM_API_BASE = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}' if TELEGRAM_BOT_TOKEN else ''
TELEGRAM_WEBHOOK_BASE_URL = (os.environ.get('TELEGRAM_WEBHOOK_BASE_URL') or '').strip().rstrip('/')
TELEGRAM_MODE = (os.environ.get('TELEGRAM_MODE') or 'webhook').strip().lower()
if TELEGRAM_MODE not in {'webhook', 'polling'}:
    TELEGRAM_MODE = 'webhook'

telegram_update_queue = queue.Queue(maxsize=500)
telegram_worker_started = False
telegram_receiver_started = False
telegram_worker_lock = threading.Lock()
telegram_receiver_lock = threading.Lock()
telegram_processed_updates = {}
telegram_processed_lock = threading.Lock()
TELEGRAM_UPDATE_TTL_SECONDS = 600
_worker_app = None


def _parse_allowed_chat_ids(raw_value: str) -> set[int]:
    ids = set()
    if not raw_value:
        return ids

    for token in raw_value.split(','):
        token = token.strip()
        if not token:
            continue
        try:
            ids.add(int(token))
        except ValueError:
            logger.warning(f'Telegram config: invalid chat id ignored: {token}')
    return ids


ALLOWED_CHAT_IDS = _parse_allowed_chat_ids(TELEGRAM_ALLOWED_CHAT_IDS)


def configure_telegram_app(app):
    global _worker_app
    _worker_app = app


def is_telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET)


def is_chat_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS


def telegram_api_call(method: str, payload: dict, timeout_seconds: int = 20) -> dict:
    if not TELEGRAM_API_BASE:
        raise RuntimeError('Telegram API nicht konfiguriert')

    response = requests.post(
        f'{TELEGRAM_API_BASE}/{method}',
        headers={'Content-Type': 'application/json'},
        json=payload,
        timeout=timeout_seconds,
    )

    if response.status_code != 200:
        raise RuntimeError(f'Telegram API Fehler: HTTP {response.status_code}')

    result = response.json()
    if not result.get('ok'):
        raise RuntimeError(f"Telegram API Fehler: {result.get('description', 'Unbekannt')}")
    return result


def send_telegram_message(chat_id: int, text: str, reply_to_message_id=None):
    payload = {
        'chat_id': chat_id,
        'text': (text or '').strip()[:4096],
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    if reply_to_message_id:
        payload['reply_to_message_id'] = reply_to_message_id

    return telegram_api_call('sendMessage', payload)


def format_telegram_recommendation(task_description: str, payload: dict) -> str:
    recommendation = payload.get('recommendation', {}) if isinstance(payload, dict) else {}
    workflow = recommendation.get('workflow') if isinstance(recommendation, dict) else []
    tools = recommendation.get('recommended_tools') if isinstance(recommendation, dict) else []
    area = (payload.get('area') or '').strip()
    subcategory = (payload.get('subcategory') or '').strip()
    optimized_prompt = (recommendation.get('optimized_prompt') or '').strip()
    model_used = (payload.get('model_used') or 'unbekannt').strip()

    first_step = ''
    if isinstance(workflow, list) and workflow:
        first_step = str(workflow[0]).strip()

    safe_task = html.escape((task_description or '').strip()[:60])
    safe_area = html.escape((area or 'n/a')[:80])
    safe_subcategory = html.escape((subcategory or 'n/a')[:80])

    lines = []
    lines.append(f'<b>🎯 {safe_task}</b>')
    lines.append(f'<i>Bereich: {safe_area} · {safe_subcategory}</i>')
    lines.append('')

    lines.append('<b>⚡ Jetzt sofort:</b>')
    lines.append(html.escape(first_step[:260]) if first_step else 'Kein Schritt verfuegbar.')
    lines.append('')

    lines.append('<b>📋 Workflow:</b>')
    if isinstance(workflow, list) and workflow:
        for index, step in enumerate(workflow, 1):
            step_text = str(step).strip()
            if not step_text:
                continue
            lines.append(f'{index}. {html.escape(step_text[:260])}')
    else:
        lines.append('1. Kein Workflow verfuegbar.')
    lines.append('')

    lines.append('<b>🛠 Empfohlene Tools:</b>')
    if isinstance(tools, list) and tools:
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            name = (tool.get('name') or '').strip()
            reason = (tool.get('reason') or tool.get('match_reason') or tool.get('best_for') or '').strip()
            url = (tool.get('url') or '').strip()

            if not name:
                continue

            line = f'• <b>{html.escape(name[:80])}</b> – {html.escape(reason[:180]) if reason else "ohne Begruendung"}'
            if url.lower().startswith('http'):
                line += f' (<a href="{html.escape(url, quote=True)}">Öffnen</a>)'
            lines.append(line)
    else:
        lines.append('• Keine Tools verfuegbar.')
    lines.append('')

    lines.append('<b>💡 Optimierter Prompt:</b>')
    if optimized_prompt:
        compact_prompt = ' '.join(optimized_prompt.split())[:900]
        lines.append(f'<code>{html.escape(compact_prompt)}</code>')
    else:
        lines.append('<code>Kein Prompt verfuegbar.</code>')
    lines.append('')

    lines.append(f'<i>via {html.escape(model_used[:80])} · FlowAI</i>')

    return '\n'.join(lines)[:4096]


def _get_last_history_payload() -> tuple[str | None, dict | None]:
    last_entry = WorkflowHistory.query.order_by(WorkflowHistory.created_at.desc()).first()
    if not last_entry:
        return None, None

    try:
        recommendation = json.loads(last_entry.recommendation_json or '{}')
    except json.JSONDecodeError:
        recommendation = {}

    payload = {
        'recommendation': recommendation if isinstance(recommendation, dict) else {},
        'area': 'n/a',
        'subcategory': 'n/a',
        'model_used': 'history',
    }
    return last_entry.task_description, payload


def _build_demo_prefix_message(task_description: str, payload: dict) -> str:
    formatted = format_telegram_recommendation(task_description, payload)
    return f'⚠️ KI nicht verfügbar – ich nutze den Regel-Fallback.\n\n{formatted}'


def _build_generic_error_fallback_payload(task_description: str) -> dict:
    return {
        'recommendation': {
            'workflow': [
                'Aufgabe in Teilziele aufteilen',
                'Recherche und Quellenpruefung durchfuehren',
                'Entwurf erstellen und ueberarbeiten',
            ],
            'recommended_tools': [],
            'optimized_prompt': f'Hilf mir bei dieser Aufgabe: {task_description}. Gib mir konkrete Schritte.',
            'tips': [],
            'why_these_tools': '',
        },
        'area': 'n/a',
        'subcategory': 'n/a',
        'model_used': 'fallback_local_rule_based',
    }


def _handle_known_command(chat_id: int, text: str, message_id: int | None) -> bool:
    normalized = text.lower().strip()

    if normalized == '/start':
        start_text = (
            "👋 Hallo! Ich bin FlowAI.\n"
            "Schreib mir einfach deine Aufgabe und ich empfehle dir den besten Workflow mit passenden Tools.\n\n"
            "Beispiel: 'Belegarbeit Kryptologie schreiben'"
        )
        send_telegram_message(chat_id, start_text, reply_to_message_id=message_id)
        return True

    if normalized in {'/hilfe', '/help'}:
        help_text = (
            "📖 <b>FlowAI Bot Hilfe</b>\n\n"
            "Schreib eine Aufgabe als freien Text.\n"
            "Ich analysiere sie und gebe dir:\n"
            "• Workflow-Schritte\n"
            "• Passende Tools mit Begründung\n"
            "• Einen optimierten Prompt\n\n"
            "<b>Befehle:</b>\n"
            "/start – Begrüßung\n"
            "/hilfe – Diese Hilfe\n"
            "/letzter – Letzte Empfehlung anzeigen"
        )
        send_telegram_message(chat_id, help_text, reply_to_message_id=message_id)
        return True

    if normalized == '/letzter':
        task_description, payload = _get_last_history_payload()
        if not task_description or not payload:
            send_telegram_message(chat_id, 'Noch keine Empfehlungen vorhanden.', reply_to_message_id=message_id)
            return True

        response_text = format_telegram_recommendation(task_description, payload)
        send_telegram_message(chat_id, response_text, reply_to_message_id=message_id)
        return True

    return False


def remember_processed_update(update_id: int):
    now = time.time()
    with telegram_processed_lock:
        telegram_processed_updates[update_id] = now
        expired = [
            key for key, timestamp in telegram_processed_updates.items()
            if now - timestamp > TELEGRAM_UPDATE_TTL_SECONDS
        ]
        for key in expired:
            telegram_processed_updates.pop(key, None)


def is_duplicate_update(update_id: int) -> bool:
    with telegram_processed_lock:
        return update_id in telegram_processed_updates


def handle_telegram_update(update: dict):
    message = update.get('message') or update.get('edited_message') or {}
    if not message:
        return

    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    text = (message.get('text') or '').strip()
    message_id = message.get('message_id')

    if chat_id is None or not text:
        return

    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        return

    if not is_chat_allowed(chat_id):
        send_telegram_message(chat_id, 'Dieser Chat ist nicht freigeschaltet.', reply_to_message_id=message_id)
        return

    if _handle_known_command(chat_id, text, message_id):
        return

    if text.startswith('/'):
        send_telegram_message(chat_id, 'Unbekannter Befehl. Nutze /hilfe für Hinweise.', reply_to_message_id=message_id)
        return

    try:
        payload = build_recommendation_response(text)
        if str(payload.get('mode') or '').strip().lower() == 'demo':
            response_text = _build_demo_prefix_message(text, payload)
        else:
            response_text = format_telegram_recommendation(text, payload)
        send_telegram_message(chat_id, response_text, reply_to_message_id=message_id)
    except Exception as err:
        logger.exception(f'Telegram processing failed: {err}')
        fallback_payload = _build_generic_error_fallback_payload(text)
        response_text = _build_demo_prefix_message(text, fallback_payload)
        send_telegram_message(chat_id, response_text, reply_to_message_id=message_id)


def telegram_worker_loop():
    logger.info('Telegram worker: started')
    while True:
        update = telegram_update_queue.get()
        try:
            if _worker_app is not None:
                with _worker_app.app_context():
                    handle_telegram_update(update)
            else:
                handle_telegram_update(update)
        except Exception as err:
            logger.exception(f'Telegram worker unexpected error: {err}')
        finally:
            telegram_update_queue.task_done()


def telegram_polling_loop():
    logger.info('Telegram polling receiver: started')
    offset = 0
    backoff_seconds = 1

    while True:
        try:
            response = requests.post(
                f'{TELEGRAM_API_BASE}/getUpdates',
                headers={'Content-Type': 'application/json'},
                json={
                    'offset': offset,
                    'timeout': 25,
                    'allowed_updates': ['message', 'edited_message'],
                },
                timeout=35,
            )

            if response.status_code != 200:
                raise RuntimeError(f'getUpdates HTTP {response.status_code}')

            payload = response.json()
            if not payload.get('ok'):
                raise RuntimeError(payload.get('description', 'getUpdates failed'))

            updates = payload.get('result') or []
            for update in updates:
                update_id = update.get('update_id')
                try:
                    update_id = int(update_id)
                except (TypeError, ValueError):
                    continue

                offset = max(offset, update_id + 1)

                if is_duplicate_update(update_id):
                    continue
                remember_processed_update(update_id)

                try:
                    telegram_update_queue.put(update, timeout=2)
                except queue.Full:
                    logger.warning('Telegram polling: queue full, dropping update')

            backoff_seconds = 1
        except Exception as err:
            logger.warning(f'Telegram polling receiver error: {err}')
            time.sleep(backoff_seconds)
            backoff_seconds = min(30, backoff_seconds * 2)


def ensure_telegram_receiver_started():
    global telegram_receiver_started
    if not is_telegram_enabled():
        return
    if TELEGRAM_MODE != 'polling':
        return

    with telegram_receiver_lock:
        if telegram_receiver_started:
            return

        try:
            telegram_api_call('deleteWebhook', {'drop_pending_updates': False})
        except Exception as err:
            logger.warning(f'Telegram polling: deleteWebhook failed: {err}')

        receiver = threading.Thread(target=telegram_polling_loop, daemon=True, name='telegram-polling-receiver')
        receiver.start()
        telegram_receiver_started = True
        logger.info('Telegram polling receiver: initialized')


def ensure_worker_started():
    global telegram_worker_started
    if not is_telegram_enabled():
        return

    with telegram_worker_lock:
        if telegram_worker_started:
            return

        worker = threading.Thread(target=telegram_worker_loop, daemon=True, name='telegram-worker')
        worker.start()
        telegram_worker_started = True
        logger.info('Telegram worker: initialized')

    ensure_telegram_receiver_started()


def ensure_scheduler_started():
    return ensure_kpi_scheduler_started()


def telegram_status_handler():
    return jsonify({
        'enabled': is_telegram_enabled(),
        'mode': TELEGRAM_MODE,
        'worker_started': telegram_worker_started,
        'receiver_started': telegram_receiver_started,
        'allowed_chat_ids_configured': bool(ALLOWED_CHAT_IDS),
        'queue_size': telegram_update_queue.qsize(),
        'webhook_path': f'{TELEGRAM_WEBHOOK_PATH}/<secret>',
        'webhook_base_url_configured': bool(TELEGRAM_WEBHOOK_BASE_URL),
    })


def telegram_setup_webhook_handler():
    if not is_telegram_enabled():
        return jsonify({'error': 'Telegram ist nicht konfiguriert (TELEGRAM_BOT_TOKEN / TELEGRAM_WEBHOOK_SECRET fehlen)'}), 400

    if not TELEGRAM_WEBHOOK_BASE_URL:
        return jsonify({'error': 'TELEGRAM_WEBHOOK_BASE_URL fehlt'}), 400

    webhook_url = f"{TELEGRAM_WEBHOOK_BASE_URL}{TELEGRAM_WEBHOOK_PATH}/{TELEGRAM_WEBHOOK_SECRET}"
    payload = {
        'url': webhook_url,
        'secret_token': TELEGRAM_WEBHOOK_SECRET,
        'drop_pending_updates': True,
        'allowed_updates': ['message', 'edited_message'],
    }

    try:
        result = telegram_api_call('setWebhook', payload)
        ensure_worker_started()
        return jsonify({'success': True, 'webhook_url': webhook_url, 'telegram_response': result})
    except Exception as err:
        logger.exception(f'Telegram setWebhook failed: {err}')
        return jsonify({'error': str(err)}), 502


def telegram_webhook_handler(secret: str):
    if not is_telegram_enabled():
        return jsonify({'error': 'Telegram nicht aktiviert'}), 404

    if secret != TELEGRAM_WEBHOOK_SECRET:
        return jsonify({'error': 'Ungültiger Webhook-Secret'}), 403

    header_secret = (request.headers.get('X-Telegram-Bot-Api-Secret-Token') or '').strip()
    if header_secret and header_secret != TELEGRAM_WEBHOOK_SECRET:
        return jsonify({'error': 'Ungültiger Secret-Header'}), 403

    update = request.get_json(silent=True) or {}
    update_id = update.get('update_id')
    if update_id is None:
        return jsonify({'ok': True, 'ignored': 'no_update_id'})

    try:
        update_id = int(update_id)
    except (TypeError, ValueError):
        return jsonify({'ok': True, 'ignored': 'invalid_update_id'})

    if is_duplicate_update(update_id):
        return jsonify({'ok': True, 'deduplicated': True})

    remember_processed_update(update_id)
    ensure_worker_started()

    try:
        telegram_update_queue.put_nowait(update)
    except queue.Full:
        logger.warning('Telegram webhook queue full, dropping update')
        message = update.get('message') or update.get('edited_message') or {}
        chat_id = ((message.get('chat') or {}).get('id'))
        if chat_id is not None:
            try:
                send_telegram_message(int(chat_id), '⚠️ Der Bot ist gerade ausgelastet. Bitte versuche es in 1-2 Minuten erneut.')
            except Exception:
                pass
        return jsonify({'ok': True, 'queued': False, 'reason': 'queue_full'})

    return jsonify({'ok': True, 'queued': True})


def get_telegram_health_state() -> dict:
    return {
        'telegram_configured': is_telegram_enabled(),
    }
