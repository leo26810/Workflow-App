import os

from dotenv import load_dotenv
from flask import Flask

from extensions import compress, cors, db
from routes.domains import domains_bp
from routes.history import history_bp
from routes.kpis import kpis_bp
from routes.profile import profile_bp
from routes.research import research_bp
from routes.recommendations import recommendations_bp
from routes.system import system_bp
from routes.telegram import telegram_bp
from routes.tools import tools_bp


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(base_dir, '.env'))

    app = Flask(__name__)

    compress.init_app(app)

    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000')
    cors.init_app(app, origins=[origin.strip() for origin in cors_origins.split(',') if origin.strip()])

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        default_sqlite_path = os.path.join(base_dir, 'instance', 'workflow.db')
        normalized_sqlite_path = default_sqlite_path.replace('\\', '/')
        database_url = f"sqlite:///{normalized_sqlite_path}"

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    app.register_blueprint(system_bp)
    app.register_blueprint(domains_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(research_bp)
    app.register_blueprint(kpis_bp)
    app.register_blueprint(telegram_bp)

    return app
