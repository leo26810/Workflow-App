from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from extensions import db


system_bp = Blueprint('system', __name__)


@system_bp.route('/api/health', methods=['GET'])
def health():
    provider = current_app.config.get('HEALTH_STATE_PROVIDER')
    if callable(provider):
        return jsonify(provider())

    return jsonify({'status': 'ok'})


@system_bp.route('/api/system/stats', methods=['GET'])
def system_stats():
    provider = current_app.config.get('HEALTH_STATE_PROVIDER')
    health_payload = provider() if callable(provider) else {'status': 'ok'}

    table_map = {
        'domains': 'domain',
        'workflow_categories': 'workflow_categories',
        'sub_categories': 'sub_categories',
        'task_templates': 'task_templates',
        'tools': 'tools',
        'workflow_history': 'workflow_history',
        'recommendation_feedback': 'recommendation_feedback',
        'research_sessions': 'research_sessions',
        'user_context': 'user_context',
        'skills': 'skills',
        'goals': 'goals',
    }

    tables = {}
    coverage = {}
    quality = {}
    distributions = {
        'tools_by_domain': [],
        'tools_by_pricing': [],
        'tools_by_skill': [],
        'categories_by_domain': [],
    }

    with current_app.app_context():
        conn = db.engine.connect()
        try:
            for label, table_name in table_map.items():
                try:
                    value = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
                except Exception:
                    value = 0
                tables[label] = int(value or 0)

            tools_total = tables.get('tools', 0)
            categories_total = tables.get('workflow_categories', 0)

            def count_non_empty(table_name: str, column_name: str) -> int:
                stmt = text(
                    f'SELECT COUNT(*) FROM "{table_name}" '
                    f'WHERE {column_name} IS NOT NULL AND LENGTH(TRIM({column_name})) > 0'
                )
                return int(conn.execute(stmt).scalar_one() or 0)

            if tools_total > 0:
                tags_count = count_non_empty('tools', 'tags')
                domain_count = count_non_empty('tools', 'domain')
                use_case_count = count_non_empty('tools', 'use_case')
                platform_count = count_non_empty('tools', 'platform')
                pricing_count = count_non_empty('tools', 'pricing_model')
                skill_count = count_non_empty('tools', 'skill_requirement')

                coverage = {
                    'tools_tag_coverage': round(tags_count / tools_total * 100.0, 1),
                    'tools_domain_coverage': round(domain_count / tools_total * 100.0, 1),
                    'tools_use_case_coverage': round(use_case_count / tools_total * 100.0, 1),
                    'tools_platform_coverage': round(platform_count / tools_total * 100.0, 1),
                    'tools_pricing_coverage': round(pricing_count / tools_total * 100.0, 1),
                    'tools_skill_coverage': round(skill_count / tools_total * 100.0, 1),
                }
            else:
                coverage = {
                    'tools_tag_coverage': 0.0,
                    'tools_domain_coverage': 0.0,
                    'tools_use_case_coverage': 0.0,
                    'tools_platform_coverage': 0.0,
                    'tools_pricing_coverage': 0.0,
                    'tools_skill_coverage': 0.0,
                }

            if categories_total > 0:
                cat_linked = int(
                    conn.execute(
                        text('SELECT COUNT(*) FROM "workflow_categories" WHERE domain_id IS NOT NULL')
                    ).scalar_one()
                    or 0
                )
                coverage['category_domain_link_coverage'] = round(cat_linked / categories_total * 100.0, 1)
            else:
                coverage['category_domain_link_coverage'] = 0.0

            quality['invalid_pricing_values'] = int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM tools
                        WHERE pricing_model IS NOT NULL
                          AND TRIM(pricing_model) <> ''
                          AND LOWER(TRIM(pricing_model)) NOT IN ('kostenlos', 'freemium', 'kostenpflichtig')
                        """
                    )
                ).scalar_one()
                or 0
            )

            quality['invalid_skill_values'] = int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM tools
                        WHERE skill_requirement IS NOT NULL
                          AND TRIM(skill_requirement) <> ''
                          AND LOWER(REPLACE(TRIM(skill_requirement), 'ä', 'a')) NOT IN ('anfaenger', 'anfanger', 'einsteiger', 'fortgeschritten', 'experte')
                        """
                    )
                ).scalar_one()
                or 0
            )

            quality['duplicate_tool_names'] = int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM (
                            SELECT LOWER(TRIM(name)) AS n
                            FROM tools
                            GROUP BY LOWER(TRIM(name))
                            HAVING COUNT(*) > 1
                        ) d
                        """
                    )
                ).scalar_one()
                or 0
            )

            quality['bad_tool_urls'] = int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM tools
                        WHERE url IS NOT NULL
                          AND TRIM(url) <> ''
                          AND LOWER(url) NOT LIKE 'http%'
                        """
                    )
                ).scalar_one()
                or 0
            )

            for key, sql in {
                'tools_by_domain': "SELECT COALESCE(NULLIF(TRIM(domain), ''), 'Unbekannt') AS k, COUNT(*) AS c FROM tools GROUP BY k ORDER BY c DESC, k ASC LIMIT 12",
                'tools_by_pricing': "SELECT COALESCE(NULLIF(TRIM(pricing_model), ''), 'Unbekannt') AS k, COUNT(*) AS c FROM tools GROUP BY k ORDER BY c DESC, k ASC",
                'tools_by_skill': "SELECT COALESCE(NULLIF(TRIM(skill_requirement), ''), 'Unbekannt') AS k, COUNT(*) AS c FROM tools GROUP BY k ORDER BY c DESC, k ASC",
                'categories_by_domain': "SELECT COALESCE(d.name, 'Unbekannt') AS k, COUNT(*) AS c FROM workflow_categories wc LEFT JOIN domain d ON d.id = wc.domain_id GROUP BY k ORDER BY c DESC, k ASC",
            }.items():
                rows = conn.execute(text(sql)).fetchall()
                distributions[key] = [{'key': str(r[0]), 'count': int(r[1])} for r in rows]
        finally:
            conn.close()

    return jsonify({
        'status': 'ok',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'health': health_payload,
        'tables': tables,
        'coverage': coverage,
        'quality': quality,
        'distributions': distributions,
    })
