import os
import threading

from app_factory import create_app
from extensions import db
from models import RecommendationFeedback, seed_extended_data
from services.data_cache_service import clear_data_caches
from services.kpi_service import configure_kpi_app, get_kpi_health_state
from services.seed_service import seed_database, seed_domains
from services.telegram_service import (
    configure_telegram_app,
    ensure_scheduler_started,
    ensure_worker_started,
    get_telegram_health_state,
)


app = create_app()
configure_telegram_app(app)
configure_kpi_app(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def build_health_payload() -> dict:
    telegram_state = get_telegram_health_state()
    kpi_state = get_kpi_health_state()
    return {
        'status': 'ok',
        'groq_configured': bool((os.environ.get('GROQ_API_KEY') or '').strip() and (os.environ.get('GROQ_API_KEY') or '').strip() != 'dein-groq-api-key-hier'),
        'telegram_configured': bool(telegram_state.get('telegram_configured')),
        'feedback_records': RecommendationFeedback.query.count(),
        'kpi_scheduler_enabled': kpi_state.get('kpi_scheduler_enabled'),
        'kpi_scheduler_started': kpi_state.get('kpi_scheduler_started'),
        'kpi_last_report_at': kpi_state.get('kpi_last_report_at'),
        'kpi_last_report_error': kpi_state.get('kpi_last_report_error'),
    }


app.config['HEALTH_STATE_PROVIDER'] = build_health_payload


def run_server() -> None:
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

    def run_seed_in_background() -> None:
        with app.app_context():
            seed_domains()
            seed_database()
            seed_extended_data()
            clear_data_caches()

    with app.app_context():
        db.create_all()

    seeding_thread = threading.Thread(target=run_seed_in_background, daemon=True)
    seeding_thread.start()

    ensure_worker_started()
    ensure_scheduler_started()

    port = int(os.environ.get('PORT', '5000'))
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"Backend running on http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run_server()
