"""
models.py - Datenbankmodelle für die Workflow-Optimierungs-App
Verwendet SQLAlchemy ORM mit SQLite als Datenbank
"""

from datetime import date, datetime, timedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """Speichert grundlegende Benutzerinformationen (vorerst nur ein Nutzer)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="Mein Profil")
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name}


class Skill(db.Model):
    """Speichert die Fähigkeiten des Nutzers"""
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(50), nullable=False, default="Anfänger")  # Anfänger / Fortgeschritten / Experte
    progress_entries = db.relationship('SkillProgress', backref='skill', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'level': self.level}


class Goal(db.Model):
    """Speichert die aktuellen Ziele des Nutzers"""
    __tablename__ = 'goals'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    
    def to_dict(self):
        return {'id': self.id, 'description': self.description}


class Tool(db.Model):
    """Wissensdatenbank über nützliche (vor allem kostenlose) Tools"""
    __tablename__ = 'tools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # z.B. Bilderstellung, Recherche, Schule
    url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.String(1000), nullable=True)
    is_free = db.Column(db.Boolean, nullable=False, default=True)
    free_tier_details = db.Column(db.String(1000), nullable=True)
    skill_requirement = db.Column(db.String(50), nullable=True)
    best_for = db.Column(db.String(500), nullable=True)
    prompt_template = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    usage_logs = db.relationship('ToolUsageLog', backref='tool', lazy=True, cascade='all, delete-orphan')
    prompt_templates = db.relationship('PromptTemplate', backref='tool', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'url': self.url,
            'notes': self.notes,
            'is_free': self.is_free,
            'free_tier_details': self.free_tier_details,
            'skill_requirement': self.skill_requirement,
            'best_for': self.best_for,
            'prompt_template': self.prompt_template,
            'rating': self.rating
        }


class ToolUsageLog(db.Model):
    """Protokolliert die Nutzung eines Tools durch den Nutzer"""
    __tablename__ = 'tool_usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable=False)
    task_description = db.Column(db.String(1000), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    was_helpful = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tool_id': self.tool_id,
            'task_description': self.task_description,
            'rating': self.rating,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'was_helpful': self.was_helpful
        }


class PromptTemplate(db.Model):
    """Gespeicherte Prompt-Vorlagen, die gut funktioniert haben"""
    __tablename__ = 'prompt_templates'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False, default='Allgemein')
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable=True)
    use_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'prompt_text': self.prompt_text,
            'category': self.category,
            'tool_id': self.tool_id,
            'use_count': self.use_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WorkflowHistory(db.Model):
    """Speichert generierte Workflow-Empfehlungen"""
    __tablename__ = 'workflow_history'

    id = db.Column(db.Integer, primary_key=True)
    task_description = db.Column(db.String(1000), nullable=False)
    recommendation_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_rating = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'task_description': self.task_description,
            'recommendation_json': self.recommendation_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_rating': self.user_rating
        }


class UserPreference(db.Model):
    """Key-Value Speicher für Nutzereinstellungen"""
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.String(1000), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value
        }


class SkillProgress(db.Model):
    """Speichert Skill-Fortschritt über die Zeit"""
    __tablename__ = 'skill_progress'

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    level = db.Column(db.String(50), nullable=False)
    note = db.Column(db.String(1000), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'skill_id': self.skill_id,
            'date': self.date.isoformat() if self.date else None,
            'level': self.level,
            'note': self.note
        }


def seed_extended_data():
    """Befüllt neue Tabellen/Felder mit Beispieldaten, falls noch leer."""
    first_tool = Tool.query.first()
    first_skill = Skill.query.first()

    if first_tool and first_tool.free_tier_details is None:
        first_tool.is_free = True
        first_tool.free_tier_details = 'Kostenlos nutzbare Basisversion verfügbar.'
        first_tool.skill_requirement = 'Anfänger'
        first_tool.best_for = 'Schnelle Aufgaben und Schulprojekte'
        first_tool.prompt_template = 'Hilf mir bei der Aufgabe: {{task}}. Gib eine klare Schritt-für-Schritt-Anleitung.'

    if first_tool and ToolUsageLog.query.first() is None:
        db.session.add_all([
            ToolUsageLog(
                tool_id=first_tool.id,
                task_description='Titelbild für eine Biologie-Präsentation erstellen',
                rating=4,
                timestamp=datetime.utcnow() - timedelta(days=2),
                was_helpful=True,
            ),
            ToolUsageLog(
                tool_id=first_tool.id,
                task_description='Recherche-Workflow für Facharbeit planen',
                rating=5,
                timestamp=datetime.utcnow() - timedelta(days=1),
                was_helpful=True,
            ),
        ])

    if PromptTemplate.query.first() is None:
        db.session.add_all([
            PromptTemplate(
                title='Recherche Zusammenfassung',
                prompt_text='Fasse die wichtigsten Fakten zu {{thema}} in 8 Stichpunkten mit Quellenangaben zusammen.',
                category='Recherche',
                tool_id=first_tool.id if first_tool else None,
                use_count=3,
            ),
            PromptTemplate(
                title='Lernkarten Generator',
                prompt_text='Erstelle aus folgendem Stoff 15 Frage-Antwort-Lernkarten: {{stoff}}',
                category='Lernen',
                tool_id=first_tool.id if first_tool else None,
                use_count=2,
            ),
        ])

    if WorkflowHistory.query.first() is None:
        db.session.add_all([
            WorkflowHistory(
                task_description='Vorbereitung Mathe-Klausur',
                recommendation_json='{"workflow": ["Themen sortieren", "Übungen lösen", "Fehleranalyse"]}',
                user_rating=4,
            ),
            WorkflowHistory(
                task_description='Infografik für Geographie',
                recommendation_json='{"workflow": ["Inhalte recherchieren", "Layout in Canva", "Finale Prüfung"]}',
                user_rating=5,
            ),
        ])

    if UserPreference.query.first() is None:
        db.session.add_all([
            UserPreference(key='preferred_language', value='de'),
            UserPreference(key='difficulty_level', value='mittel'),
            UserPreference(key='focus_areas', value='Mathe, Recherche, Präsentation'),
        ])

    if first_skill and SkillProgress.query.first() is None:
        db.session.add_all([
            SkillProgress(
                skill_id=first_skill.id,
                date=date.today() - timedelta(days=14),
                level='Anfänger',
                note='Grundlagen wiederholt',
            ),
            SkillProgress(
                skill_id=first_skill.id,
                date=date.today() - timedelta(days=7),
                level='Fortgeschritten',
                note='Übungsaufgaben sicher gelöst',
            ),
            SkillProgress(
                skill_id=first_skill.id,
                date=date.today(),
                level='Fortgeschritten',
                note='Stabiler Lernfortschritt',
            ),
        ])

    avg_ratings = (
        db.session.query(ToolUsageLog.tool_id, db.func.avg(ToolUsageLog.rating))
        .group_by(ToolUsageLog.tool_id)
        .all()
    )
    for tool_id, avg_value in avg_ratings:
        tool = Tool.query.get(tool_id)
        if tool:
            tool.rating = round(float(avg_value), 2)

    db.session.commit()
