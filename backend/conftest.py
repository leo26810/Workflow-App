"""
conftest.py - pytest fixtures for testing the Flask application
Provides test app, database session with auto-rollback, and sample data
"""

import os
import pytest
from datetime import datetime, timedelta

from app_factory import create_app
from extensions import db as _db
from models import User, Skill, Goal, Tool, Domain, KnowledgeBase, ToolFeedback


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
        connection = _db.engine.connect()
        transaction = connection.begin()
        
        # Bind session to connection
        session = _db.create_scoped_session(
            options={'bind': connection, 'binds': {}}
        )
        _db.session = session
        
        yield session
        
        # Rollback transaction and close connection
        transaction.rollback()
        connection.close()
        session.remove()


@pytest.fixture
def client(app, db_session):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(id=1, name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_skills(db_session):
    """Create sample skills for testing."""
    skills = [
        Skill(id=1, name="Python", level="Fortgeschritten"),
        Skill(id=2, name="JavaScript", level="Anfänger"),
        Skill(id=3, name="Data Analysis", level="Experte"),
    ]
    db_session.add_all(skills)
    db_session.commit()
    return skills


@pytest.fixture
def sample_goals(db_session):
    """Create sample goals for testing."""
    goals = [
        Goal(id=1, description="Learn machine learning"),
        Goal(id=2, description="Build a web application"),
    ]
    db_session.add_all(goals)
    db_session.commit()
    return goals


@pytest.fixture
def sample_tools(db_session):
    """Create sample tools for testing."""
    tools = [
        Tool(
            id=1,
            name="VS Code",
            category="Development",
            description="Code editor",
            pricing_model="Kostenlos",
            skill_requirement="Anfänger",
            platform="Windows, Mac, Linux",
            use_case="Software Development",
            best_for="General coding tasks",
            strengths="Lightweight, extensible, fast",
            weaknesses="Heavy extension usage slows it down",
            alternatives="Sublime Text, Atom",
            website="https://code.visualstudio.com",
        ),
        Tool(
            id=2,
            name="Notion",
            category="Productivity",
            description="Note-taking and project management",
            pricing_model="Freemium",
            skill_requirement="Anfänger",
            platform="Web, Windows, Mac, Mobile",
            use_case="Project Management",
            best_for="Personal knowledge management",
            strengths="Flexible, beautiful UI, databases",
            weaknesses="Can be slow, learning curve",
            alternatives="Obsidian, Roam Research",
            website="https://notion.so",
        ),
        Tool(
            id=3,
            name="Pandas",
            category="Data Science",
            description="Data manipulation library",
            pricing_model="Kostenlos",
            skill_requirement="Fortgeschritten",
            platform="Python",
            use_case="Data Analysis",
            best_for="Tabular data processing",
            strengths="Powerful, flexible, well-documented",
            weaknesses="Memory intensive, steep learning curve",
            alternatives="Polars, Dask",
            website="https://pandas.pydata.org",
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


@pytest.fixture
def sample_feedback(db_session, sample_tools):
    """Create sample tool feedback for testing."""
    feedback = [
        ToolFeedback(
            tool_names="VS Code, GitHub Copilot",
            feedback_text="Great combination for coding",
            rating=5,
        ),
        ToolFeedback(
            tool_names="Notion",
            feedback_text="Too slow for large databases",
            rating=3,
        ),
    ]
    db_session.add_all(feedback)
    db_session.commit()
    return feedback
