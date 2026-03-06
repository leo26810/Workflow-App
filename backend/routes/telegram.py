from flask import Blueprint

from services.telegram_service import (
    telegram_status_handler,
    telegram_setup_webhook_handler,
    telegram_webhook_handler,
)


telegram_bp = Blueprint('telegram', __name__)


@telegram_bp.route('/api/telegram/status', methods=['GET'])
def telegram_status_route():
    return telegram_status_handler()


@telegram_bp.route('/api/telegram/setup-webhook', methods=['POST'])
def telegram_setup_webhook_route():
    return telegram_setup_webhook_handler()


@telegram_bp.route('/api/telegram/webhook/<secret>', methods=['POST'])
def telegram_webhook_route(secret: str):
    return telegram_webhook_handler(secret)
