from flask import Blueprint

from services.kpi_service import get_kpi_report, get_kpi_scheduler_status, get_kpi_targets, get_kpis


kpis_bp = Blueprint('kpis', __name__)


@kpis_bp.route('/api/kpis', methods=['GET'])
def kpis_route():
    return get_kpis()


@kpis_bp.route('/api/kpis/targets', methods=['GET'])
def kpi_targets_route():
    return get_kpi_targets()


@kpis_bp.route('/api/kpis/report', methods=['GET'])
def kpi_report_route():
    return get_kpi_report()


@kpis_bp.route('/api/kpis/scheduler-status', methods=['GET'])
def kpi_scheduler_status_route():
    return get_kpi_scheduler_status()
