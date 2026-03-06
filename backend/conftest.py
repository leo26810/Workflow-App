"""
conftest.py - pytest fixtures for testing the Flask application
Provides test app, database session with auto-rollback, and sample data
"""

import os
import pytest
from datetime import datetime, timedelta

from app_factory import create_app
from extensions import db as _db
from models import User, Skill, Goal, Tool, Domain


@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app instance for testing."""
    # Set test environment variables
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['TESTING'] = 'True'
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    
    # Create all tables
    with app.app_context():
        _db.create_all()
    
    yield app
    
    # Cleanup
    with app.app_context():
        _db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """
    Create a new database session for a test with auto-rollback.
    Changes made in tests are rolled back after each test.
    """
    with app.app_context():
        # Create all tables
        _db.create_all()
        
        yield _db.session
        
        # Rollback and cleanup
        _db.session.rollback()
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app, db_session):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_skills(db_session):
    """Create sample skills for testing."""
    skills = [
        Skill(name="Python", level="Fortgeschritten"),
        Skill(name="JavaScript", level="Anfänger"),
        Skill(name="Data Analysis", level="Experte"),
    ]
    db_session.add_all(skills)
    db_session.commit()
    return skills


@pytest.fixture
def sample_goals(db_session):
    """Create sample goals for testing."""
    goals = [
        Goal(description="Learn machine learning"),
        Goal(description="Build a web application"),
    ]
    db_session.add_all(goals)
    db_session.commit()
    return goals


@pytest.fixture
def sample_tools(db_session):
    """Create sample tools for testing."""
    tools = [
        Tool(
            name="VS Code",
            category="Development",
            domain="Software Development",
            pricing_model="Kostenlos",
            skill_requirement="Anfänger",
            platform="Windows, Mac, Linux",
            use_case="Software Development",
            best_for="General coding tasks",
            url="https://code.visualstudio.com",
            is_free=True,
        ),
        Tool(
            name="Notion",
            category="Productivity",
            domain="Project Management",
            pricing_model="Freemium",
            skill_requirement="Anfänger",
            platform="Web, Windows, Mac, Mobile",
            use_case="Project Management",
            best_for="Personal knowledge management",
            url="https://notion.so",
            is_free=False,
        ),
        Tool(
            name="Pandas",
            category="Data Science",
            domain="Data Science",
            pricing_model="Kostenlos",
            skill_requirement="Fortgeschritten",
            platform="Python",
            use_case="Data Analysis",
            best_for="Tabular data processing",
            url="https://pandas.pydata.org",
            is_free=True,
        ),
    ]
    db_session.add_all(tools)
    db_session.commit()
    return tools


@pytest.fixture
def sample_domains(db_session):
    """Create sample domains for testing."""
    domains = [
        Domain(name="Software Development", description="Programming and software engineering"),
        Domain(name="Data Science", description="Data analysis and machine learning"),
    ]
    db_session.add_all(domains)
    db_session.commit()
    return domains
