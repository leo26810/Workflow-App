import os
import json
import threading
import time
from datetime import timedelta
from datetime import datetime, timezone

from flask import jsonify, request

from models import RecommendationFeedback, WorkflowHistory


def parse_bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    clean = value.strip().lower()
    if clean in {'1', 'true', 'yes', 'on', 'ja'}:
        return True
    if clean in {'0', 'false', 'no', 'off', 'nein'}:
        return False
    return default


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KPI_AUTOREPORT_ENABLED = parse_bool_env('KPI_AUTOREPORT_ENABLED', True)
KPI_AUTOREPORT_INTERVAL_MINUTES = max(5, min(1440, int((os.environ.get('KPI_AUTOREPORT_INTERVAL_MINUTES') or '60').strip() or '60')))
KPI_REPORT_WINDOW_DAYS = max(1, min(365, int((os.environ.get('KPI_REPORT_WINDOW_DAYS') or '30').strip() or '30')))

KPI_TARGETS = {
    'feedback_coverage': {'target': 0.6, 'direction': 'min'},
    'avg_user_rating': {'target': 4.2, 'direction': 'min'},
    'satisfaction_rate': {'target': 0.75, 'direction': 'min'},
    'acceptance_rate': {'target': 0.7, 'direction': 'min'},
    'reuse_rate': {'target': 0.55, 'direction': 'min'},
    'avg_time_saved_minutes': {'target': 20.0, 'direction': 'min'},
    'top3_hit_rate': {'target': 0.7, 'direction': 'min'},
}

kpi_scheduler_started = False
kpi_scheduler_lock = threading.Lock()
kpi_last_report_path = None
kpi_last_report_at = None
kpi_last_report_error = None
_kpi_app = None


def configure_kpi_app(app):
    global _kpi_app
    _kpi_app = app


def evaluate_kpi_against_target(metric_name: str, value):
    target_config = KPI_TARGETS.get(metric_name)
    if not target_config:
        return {'status': 'no-target', 'target': None, 'direction': None, 'gap': None}

    target = target_config['target']
    direction = target_config['direction']

    if value is None:
        return {'status': 'insufficient-data', 'target': target, 'direction': direction, 'gap': None}

    if direction == 'min':
        met = value >= target
        gap = round(value - target, 4)
    else:
        met = value <= target
        gap = round(target - value, 4)

    return {
        'status': 'met' if met else 'below-target',
        'target': target,
        'direction': direction,
        'gap': gap,
    }


def compute_kpi_snapshot(days: int = 30) -> dict:
    bounded_days = max(1, min(365, days))
    since = datetime.utcnow() - timedelta(days=bounded_days)

    feedback_rows = RecommendationFeedback.query.filter(RecommendationFeedback.updated_at >= since).all()
    recommendation_count = WorkflowHistory.query.filter(WorkflowHistory.created_at >= since).count()

    ratings = [row.user_rating for row in feedback_rows if row.user_rating is not None]
    accepted_values = [row.accepted for row in feedback_rows if row.accepted is not None]
    reused_values = [row.reused for row in feedback_rows if row.reused is not None]
    saved_minutes_values = [row.time_saved_minutes for row in feedback_rows if row.time_saved_minutes is not None]

    top3_denominator = 0
    top3_hits = 0
    for row in feedback_rows:
        if row.user_rating is None or row.accepted is None:
            continue
        top3_denominator += 1
        if row.user_rating >= 4 and row.accepted:
            top3_hits += 1

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    satisfaction_rate = round(sum(1 for value in ratings if value >= 4) / len(ratings), 3) if ratings else None
    acceptance_rate = round(sum(1 for value in accepted_values if value) / len(accepted_values), 3) if accepted_values else None
    reuse_rate = round(sum(1 for value in reused_values if value) / len(reused_values), 3) if reused_values else None
    avg_time_saved_minutes = round(sum(saved_minutes_values) / len(saved_minutes_values), 1) if saved_minutes_values else None
    top3_hit_rate = round(top3_hits / top3_denominator, 3) if top3_denominator else None
    feedback_coverage = round(len(feedback_rows) / recommendation_count, 3) if recommendation_count else 0.0

    kpi_values = {
        'feedback_coverage': feedback_coverage,
        'avg_user_rating': avg_rating,
        'satisfaction_rate': satisfaction_rate,
        'acceptance_rate': acceptance_rate,
        'reuse_rate': reuse_rate,
        'avg_time_saved_minutes': avg_time_saved_minutes,
        'top3_hit_rate': top3_hit_rate,
    }

    target_checks = {
        name: evaluate_kpi_against_target(name, value)
        for name, value in kpi_values.items()
    }

    checks_with_targets = [check for check in target_checks.values() if check.get('status') in {'met', 'below-target'}]
    met_count = sum(1 for check in checks_with_targets if check['status'] == 'met')
    health_index = round(met_count / len(checks_with_targets), 3) if checks_with_targets else None

    return {
        'window_days': bounded_days,
        'recommendation_count': recommendation_count,
        'feedback_count': len(feedback_rows),
        'feedback_coverage': feedback_coverage,
        'avg_user_rating': avg_rating,
        'satisfaction_rate': satisfaction_rate,
        'acceptance_rate': acceptance_rate,
        'reuse_rate': reuse_rate,
        'avg_time_saved_minutes': avg_time_saved_minutes,
        'top3_hit_rate': top3_hit_rate,
        'kpi_targets': target_checks,
        'kpi_health_index': health_index,
    }


def write_kpi_report_file(days: int | None = None) -> str:
    global kpi_last_report_path, kpi_last_report_at, kpi_last_report_error

    report_days = days if isinstance(days, int) else KPI_REPORT_WINDOW_DAYS
    snapshot = compute_kpi_snapshot(days=report_days)

    log_dir = os.path.join(os.path.dirname(BASE_DIR), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_name = f'kpi_report_{timestamp}.json'
    file_path = os.path.join(log_dir, file_name)

    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'window_days': report_days,
        'snapshot': snapshot,
    }

    with open(file_path, 'w', encoding='utf-8') as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    kpi_last_report_path = file_path
    kpi_last_report_at = payload['generated_at']
    kpi_last_report_error = None

    return file_path


def kpi_scheduler_loop():
    global kpi_last_report_error
    interval_seconds = KPI_AUTOREPORT_INTERVAL_MINUTES * 60

    while True:
        try:
            if _kpi_app is not None:
                with _kpi_app.app_context():
                    write_kpi_report_file()
            else:
                write_kpi_report_file()
        except Exception as err:
            kpi_last_report_error = str(err)

        time.sleep(interval_seconds)


def ensure_kpi_scheduler_started():
    global kpi_scheduler_started
    if not KPI_AUTOREPORT_ENABLED:
        return

    with kpi_scheduler_lock:
        if kpi_scheduler_started:
            return

        scheduler = threading.Thread(target=kpi_scheduler_loop, daemon=True, name='kpi-autoreport-scheduler')
        scheduler.start()
        kpi_scheduler_started = True


def get_kpi_health_state() -> dict:
    return {
        'kpi_scheduler_enabled': KPI_AUTOREPORT_ENABLED,
        'kpi_scheduler_started': kpi_scheduler_started,
        'kpi_last_report_at': kpi_last_report_at,
        'kpi_last_report_error': kpi_last_report_error,
    }


def get_kpis():
    try:
        days = int(str(request.args.get('days', '30')).strip())
    except (TypeError, ValueError):
        return jsonify({'error': 'days muss numerisch sein'}), 400

    snapshot = compute_kpi_snapshot(days=days)
    return jsonify(snapshot)


def get_kpi_targets():
    return jsonify(KPI_TARGETS)


def get_kpi_report():
    try:
        days = int(str(request.args.get('days', '30')).strip())
    except (TypeError, ValueError):
        return jsonify({'error': 'days muss numerisch sein'}), 400

    snapshot = compute_kpi_snapshot(days=days)
    return jsonify({
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'summary': {
            'kpi_health_index': snapshot.get('kpi_health_index'),
            'feedback_coverage': snapshot.get('feedback_coverage'),
            'avg_user_rating': snapshot.get('avg_user_rating'),
            'top3_hit_rate': snapshot.get('top3_hit_rate'),
        },
        'snapshot': snapshot,
    })


def get_kpi_scheduler_status():
    report_path = kpi_last_report_path or ''
    report_name = os.path.basename(report_path) if report_path else None
    return jsonify({
        'enabled': KPI_AUTOREPORT_ENABLED,
        'started': kpi_scheduler_started,
        'interval_minutes': KPI_AUTOREPORT_INTERVAL_MINUTES,
        'window_days': KPI_REPORT_WINDOW_DAYS,
        'last_report_at': kpi_last_report_at,
        'last_report_file': report_name,
        'last_error': kpi_last_report_error,
    })
