"""
models.py - Datenbankmodelle für die Workflow-Optimierungs-App
Verwendet SQLAlchemy ORM mit SQLite als Datenbank
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, TypeVar

from extensions import db
ModelT = TypeVar('ModelT')


def make_model(model_cls: type[ModelT], **values: Any) -> ModelT:
    instance = model_cls()
    for key, value in values.items():
        setattr(instance, key, value)
    return instance


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    domain = db.Column(db.String(100), nullable=True, index=True)
    tags = db.Column(db.String(500), nullable=True)
    use_case = db.Column(db.String(1000), nullable=True)
    platform = db.Column(db.String(200), nullable=True)
    pricing_model = db.Column(db.String(100), nullable=True)
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
            'domain': self.domain,
            'tags': self.tags,
            'use_case': self.use_case,
            'platform': self.platform,
            'pricing_model': self.pricing_model,
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
    timestamp = db.Column(db.DateTime, nullable=False, default=utc_now)
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
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

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
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    user_rating = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'task_description': self.task_description,
            'recommendation_json': self.recommendation_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_rating': self.user_rating
        }


class RecommendationFeedback(db.Model):
    """Nutzer-Feedback pro Empfehlung für dynamisches Ranking und KPI-Berechnung."""
    __tablename__ = 'recommendation_feedback'

    id = db.Column(db.Integer, primary_key=True)
    workflow_history_id = db.Column(db.Integer, db.ForeignKey('workflow_history.id'), nullable=False, unique=True)
    task_description = db.Column(db.String(1000), nullable=True)
    area = db.Column(db.String(100), nullable=True)
    subcategory = db.Column(db.String(150), nullable=True)
    recommended_tools_json = db.Column(db.JSON, nullable=False, default=list)
    user_rating = db.Column(db.Integer, nullable=True)
    accepted = db.Column(db.Boolean, nullable=True)
    reused = db.Column(db.Boolean, nullable=True)
    time_saved_minutes = db.Column(db.Integer, nullable=True)
    note = db.Column(db.String(1000), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_history_id': self.workflow_history_id,
            'task_description': self.task_description,
            'area': self.area,
            'subcategory': self.subcategory,
            'recommended_tools': self.recommended_tools_json or [],
            'user_rating': self.user_rating,
            'accepted': self.accepted,
            'reused': self.reused,
            'time_saved_minutes': self.time_saved_minutes,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
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


class Domain(db.Model):
    __tablename__ = 'domain'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(20), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    categories = db.relationship('WorkflowCategory', backref='domain', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'tags': self.tags,
            'sort_order': self.sort_order,
            'category_count': len(self.categories),
        }


class WorkflowCategory(db.Model):
    """Die drei Hauptbereiche der App."""
    __tablename__ = 'workflow_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    icon = db.Column(db.String(10), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    description = db.Column(db.String(500), nullable=True)
    subcategories = db.relationship('SubCategory', backref='category', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'domain_id': self.domain_id,
            'tags': self.tags,
            'description': self.description,
        }


class SubCategory(db.Model):
    """Unterkategorien pro Hauptbereich."""
    __tablename__ = 'sub_categories'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('workflow_categories.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    task_templates = db.relationship('TaskTemplate', backref='subcategory', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
        }


class TaskTemplate(db.Model):
    """Vorgefertigte Aufgaben-Templates pro Unterkategorie."""
    __tablename__ = 'task_templates'

    id = db.Column(db.Integer, primary_key=True)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('sub_categories.id'), nullable=False)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    example_input = db.Column(db.String(1000), nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'subcategory_id': self.subcategory_id,
            'title': self.title,
            'description': self.description,
            'example_input': self.example_input,
            'tags': self.tags,
        }


class UserContext(db.Model):
    """Detaillierter Nutzerkontext über alle Bereiche."""
    __tablename__ = 'user_context'

    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(50), nullable=False)  # ki / recherche / schule
    key = db.Column(db.String(120), nullable=False)
    value = db.Column(db.String(2000), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'area': self.area,
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ResearchSession(db.Model):
    """Gespeicherte Recherche-Sessions."""
    __tablename__ = 'research_sessions'

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(500), nullable=False)
    sources = db.Column(db.JSON, nullable=False, default=list)  # [{"url": "...", "title": "..."}]
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    tags = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'sources': self.sources or [],
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tags': self.tags,
        }


db.Index('ix_tool_domain', Tool.domain)
db.Index('ix_tool_tags', Tool.tags)


def seed_categories():
    """Seedet Hauptbereiche, Unterkategorien und Task-Templates (idempotent)."""
    category_definitions = [
        {
            'name': 'KI-Verwendung',
            'icon': '🤖',
            'description': 'Aufgaben rund um KI-gestützte Erstellung, Analyse und Automatisierung.',
            'subcategories': [
                {
                    'name': 'Bilderstellung',
                    'description': 'Bilder, Illustrationen und visuelle Assets mit KI erzeugen.',
                    'templates': [
                        {
                            'title': 'Logo für AG erstellen',
                            'description': 'Erstelle ein einfaches, gut lesbares Logo für eine Schul-AG.',
                            'example_input': 'Ich brauche ein modernes Logo für unsere Robotik-AG in Blau und Weiß.',
                            'tags': 'logo,design,schule'
                        },
                        {
                            'title': 'Titelbild für Referat',
                            'description': 'Generiere ein passendes Cover-Bild für eine Präsentation.',
                            'example_input': 'Erzeuge ein Titelbild für mein Referat über erneuerbare Energien.',
                            'tags': 'titelbild,präsentation,energie'
                        },
                        {
                            'title': 'Infografik-Visual erzeugen',
                            'description': 'Erstelle ein didaktisches Visual zur Erklärung eines Themas.',
                            'example_input': 'Erstelle ein Visual, das den Wasserkreislauf für 8. Klasse zeigt.',
                            'tags': 'infografik,biologie,unterricht'
                        },
                    ],
                },
                {
                    'name': 'Programmierung',
                    'description': 'Unterstützung beim Coden, Debuggen und Strukturieren von Software.',
                    'templates': [
                        {
                            'title': 'Python-Hausaufgabe debuggen',
                            'description': 'Finde und behebe Fehler in einer Schulaufgabe.',
                            'example_input': 'Mein Python-Skript für Notendurchschnitt zeigt falsche Werte, hilf beim Debuggen.',
                            'tags': 'python,debug,hausaufgabe'
                        },
                        {
                            'title': 'Mini-Tool für Lernplan',
                            'description': 'Baue ein kleines Script zur Lernorganisation.',
                            'example_input': 'Schreibe ein Python-Programm, das einen Wochen-Lernplan aus Fächern erstellt.',
                            'tags': 'python,lernplan,automation'
                        },
                        {
                            'title': 'Code erklären lassen',
                            'description': 'Lass dir schwierigen Code in einfachen Schritten erklären.',
                            'example_input': 'Erkläre mir diese Schleife und Liste in meinem JavaScript-Projekt einfach.',
                            'tags': 'codeverständnis,javascript,lernen'
                        },
                    ],
                },
                {
                    'name': 'Promptgeneration',
                    'description': 'Bessere Eingaben erstellen, um präzisere KI-Ergebnisse zu erhalten.',
                    'templates': [
                        {
                            'title': 'Prompt für Zusammenfassung',
                            'description': 'Formuliere einen präzisen Prompt für Text-Zusammenfassungen.',
                            'example_input': 'Gib mir einen Prompt, um einen langen Geschichtstext in 10 Stichpunkten zusammenzufassen.',
                            'tags': 'prompt,text,zusammenfassung'
                        },
                        {
                            'title': 'Prompt für Lernkarten',
                            'description': 'Erzeuge Lernkarten aus Unterrichtsinhalten per KI.',
                            'example_input': 'Ich brauche einen Prompt, der aus Biologie-Notizen Lernkarten erstellt.',
                            'tags': 'prompt,lernkarten,biologie'
                        },
                        {
                            'title': 'Prompt für Mathe-Erklärung',
                            'description': 'Fordere schrittweise und altersgerechte Erklärungen an.',
                            'example_input': 'Erstelle einen Prompt, damit KI mir quadratische Gleichungen Schritt für Schritt erklärt.',
                            'tags': 'prompt,mathe,erklärung'
                        },
                    ],
                },
                {
                    'name': 'Analysen & Zusammenfassung',
                    'description': 'Inhalte strukturieren, vergleichen und verständlich aufbereiten.',
                    'templates': [
                        {
                            'title': 'Kapitelanalyse Deutsch',
                            'description': 'Analysiere ein Kapitel nach Figuren, Motiven und Sprache.',
                            'example_input': 'Analysiere Kapitel 3 aus meinem Romantext für den Deutschunterricht.',
                            'tags': 'analyse,deutsch,roman'
                        },
                        {
                            'title': 'Quellenvergleich Geschichte',
                            'description': 'Vergleiche zwei Quellen nach Perspektive und Aussage.',
                            'example_input': 'Vergleiche diese zwei Texte zum Ersten Weltkrieg nach Kernaussagen.',
                            'tags': 'geschichte,quellenvergleich,analyse'
                        },
                        {
                            'title': 'Lernzettel aus Mitschrift',
                            'description': 'Erstelle einen kompakten Lernzettel aus ungeordneten Notizen.',
                            'example_input': 'Fasse meine Notizen zum Thema Zellbiologie als Lernzettel zusammen.',
                            'tags': 'lernzettel,biologie,zusammenfassung'
                        },
                    ],
                },
            ],
        },
        {
            'name': 'Internet-Recherche',
            'icon': '🔍',
            'description': 'Gezielte Suche, Quellenprüfung und strukturierte Informationssammlung.',
            'subcategories': [
                {
                    'name': 'Bildersuche',
                    'description': 'Geeignete, lizenzkonforme Bilder für Schulzwecke finden.',
                    'templates': [
                        {
                            'title': 'Quellenbild für Referat',
                            'description': 'Finde ein passendes Bild mit sauberer Quellenangabe.',
                            'example_input': 'Suche ein lizenzfreies Bild zum Thema Vulkane für meine Folie.',
                            'tags': 'bilder,quelle,präsentation'
                        },
                        {
                            'title': 'Vergleichsbilder sammeln',
                            'description': 'Sammle mehrere Bilder für Vorher-Nachher-Vergleiche.',
                            'example_input': 'Finde 3 Vergleichsbilder zur Stadtentwicklung in den letzten 100 Jahren.',
                            'tags': 'vergleich,bildersuche,geschichte'
                        },
                        {
                            'title': 'Kartenmaterial finden',
                            'description': 'Suche Karten und Grafiken für Geographie- oder Geschichtsprojekte.',
                            'example_input': 'Ich brauche eine Karte der Handelsrouten im Mittelalter mit Quelle.',
                            'tags': 'karten,geographie,geschichte'
                        },
                    ],
                },
                {
                    'name': 'Informationsrecherche',
                    'description': 'Faktenbasierte Recherche mit Quellenbewertung und Strukturierung.',
                    'templates': [
                        {
                            'title': 'Facharbeit Grundlagen sammeln',
                            'description': 'Sammle Einstiegsliteratur und zuverlässige Online-Quellen.',
                            'example_input': 'Recherchiere Ursachen und Folgen der Industrialisierung mit seriösen Quellen.',
                            'tags': 'facharbeit,recherche,quellen'
                        },
                        {
                            'title': 'Pro-Contra Recherche',
                            'description': 'Strukturiere Argumente für Diskussionen oder Debatten.',
                            'example_input': 'Finde Pro- und Contra-Argumente zur Nutzung von KI im Unterricht.',
                            'tags': 'debatte,argumente,ki'
                        },
                        {
                            'title': 'Schnellbriefing für Referat',
                            'description': 'Erstelle ein kurzes, belastbares Themenbriefing in Stichpunkten.',
                            'example_input': 'Gib mir ein 10-Punkte-Briefing über den Treibhauseffekt mit Quellen.',
                            'tags': 'referat,briefing,naturwissenschaften'
                        },
                    ],
                },
            ],
        },
        {
            'name': 'Schule',
            'icon': '📚',
            'description': 'Lernorganisation, Projekte und Prüfungsvorbereitung für den Schulalltag.',
            'subcategories': [
                {
                    'name': 'Mitschreiben & Dokumente',
                    'description': 'Mitschriften strukturieren und in brauchbare Dokumente überführen.',
                    'templates': [
                        {
                            'title': 'Mitschrift ordnen',
                            'description': 'Unstrukturierte Notizen in klare Themenblöcke sortieren.',
                            'example_input': 'Ordne meine chaotischen Geschichtsnotizen in ein sauberes Dokument.',
                            'tags': 'mitschrift,dokument,ordnung'
                        },
                        {
                            'title': 'Lernblatt erstellen',
                            'description': 'Erzeuge ein kompaktes Lernblatt aus Unterrichtsstoff.',
                            'example_input': 'Erstelle ein Lernblatt zu Photosynthese aus meinen Stichpunkten.',
                            'tags': 'lernblatt,biologie,zusammenfassung'
                        },
                        {
                            'title': 'Protokoll für Gruppenarbeit',
                            'description': 'Formuliere ein klares Protokoll für Team-Meetings.',
                            'example_input': 'Erstelle ein Protokoll unserer Gruppenarbeit für das Chemieprojekt.',
                            'tags': 'protokoll,gruppenarbeit,chemie'
                        },
                    ],
                },
                {
                    'name': 'Schulprojekte',
                    'description': 'Planung, Aufgabenverteilung und Umsetzung größerer Schulprojekte.',
                    'templates': [
                        {
                            'title': 'Projektplan mit Deadlines',
                            'description': 'Erstelle einen realistischen Zeitplan bis zur Abgabe.',
                            'example_input': 'Plane mein Geographie-Projekt bis zur Abgabe in 3 Wochen.',
                            'tags': 'projektplanung,deadlines,geographie'
                        },
                        {
                            'title': 'Rollen im Team verteilen',
                            'description': 'Definiere Rollen und Aufgabenpakete für Gruppenmitglieder.',
                            'example_input': 'Verteile Aufgaben für unser Geschichtsprojekt mit 4 Personen.',
                            'tags': 'team,rollen,projekt'
                        },
                        {
                            'title': 'Abschlusspräsentation vorbereiten',
                            'description': 'Strukturiere die finale Präsentation für ein Projekt.',
                            'example_input': 'Erstelle den Aufbau für unsere Abschlusspräsentation zum Klimawandel-Projekt.',
                            'tags': 'präsentation,abschluss,projekt'
                        },
                    ],
                },
                {
                    'name': 'Lernen & Üben',
                    'description': 'Lernpläne, Wiederholung und Prüfungsvorbereitung.',
                    'templates': [
                        {
                            'title': 'Wochenlernplan erstellen',
                            'description': 'Plane ein realistisches Lernpensum für mehrere Fächer.',
                            'example_input': 'Erstelle mir einen Wochenlernplan für Mathe, Englisch und Biologie.',
                            'tags': 'lernplan,wochenplan,prüfung'
                        },
                        {
                            'title': 'Prüfungsvorbereitung strukturieren',
                            'description': 'Priorisiere Themen nach Schwierigkeitsgrad und Zeit.',
                            'example_input': 'Hilf mir bei der Vorbereitung auf die Mathe-Klausur zu quadratischen Funktionen.',
                            'tags': 'klausur,mathe,vorbereitung'
                        },
                        {
                            'title': 'Wiederholung mit Quizfragen',
                            'description': 'Erstelle Übungsfragen zum Selbsttest.',
                            'example_input': 'Generiere 20 Quizfragen zur Französischen Revolution mit Lösungen.',
                            'tags': 'quiz,geschichte,selbsttest'
                        },
                    ],
                },
            ],
        },
        {
            'name': 'Alltag & Produktivität',
            'icon': '🧭',
            'description': 'Struktur für Tagesplanung, Kommunikation und Priorisierung im Alltag.',
            'subcategories': [
                {
                    'name': 'Planung & Organisation',
                    'description': 'Aufgaben strukturieren, Zeitblöcke planen und To-dos systematisch bearbeiten.',
                    'templates': [
                        {
                            'title': 'Tagesplan mit Fokusblöcken',
                            'description': 'Erstelle einen realistischen Tagesplan mit Deep-Work- und Pausenblöcken.',
                            'example_input': 'Plane meinen Tag zwischen Schule, Sport und Hausaufgaben in 90-Minuten-Blöcken.',
                            'tags': 'planung,zeitmanagement,produktivität'
                        },
                        {
                            'title': 'Wochenziele priorisieren',
                            'description': 'Priorisiere Aufgaben nach Wichtigkeit und Aufwand.',
                            'example_input': 'Hilf mir, meine Wochenziele mit Must/Should/Could zu sortieren.',
                            'tags': 'wochenziele,priorisierung,organisation'
                        },
                        {
                            'title': 'Routine für wiederkehrende Aufgaben',
                            'description': 'Baue eine wiederholbare Routine für tägliche Aufgaben.',
                            'example_input': 'Erstelle mir eine Morgenroutine für Schule und Lernvorbereitung.',
                            'tags': 'routine,alltag,struktur'
                        },
                    ],
                },
                {
                    'name': 'Kommunikation',
                    'description': 'Nachrichten, E-Mails und Abstimmungen klar und zielgerichtet formulieren.',
                    'templates': [
                        {
                            'title': 'E-Mail an Lehrkraft formulieren',
                            'description': 'Schreibe eine höfliche und präzise E-Mail mit klarem Anliegen.',
                            'example_input': 'Formuliere eine E-Mail an meine Lehrerin wegen einer Fristverlängerung.',
                            'tags': 'email,schule,kommunikation'
                        },
                        {
                            'title': 'Gruppenchat strukturieren',
                            'description': 'Formuliere klare Aufgabenverteilung und nächste Schritte für Teams.',
                            'example_input': 'Schreibe eine Nachricht für unsere Projektgruppe mit klaren To-dos.',
                            'tags': 'team,chat,abstimmung'
                        },
                        {
                            'title': 'Feedback professionell geben',
                            'description': 'Formuliere konstruktives Feedback konkret und respektvoll.',
                            'example_input': 'Hilf mir, Feedback zu einem Referat freundlich und konkret zu schreiben.',
                            'tags': 'feedback,kommunikation,zusammenarbeit'
                        },
                    ],
                },
                {
                    'name': 'Entscheidungen & Priorisierung',
                    'description': 'Optionen vergleichen, Kriterien definieren und fokussierte Entscheidungen treffen.',
                    'templates': [
                        {
                            'title': 'Optionen mit Kriterienmatrix vergleichen',
                            'description': 'Bewerte mehrere Optionen nach gewichteten Kriterien.',
                            'example_input': 'Vergleiche drei Themen für mein Referat anhand Aufwand, Interesse und Quellenlage.',
                            'tags': 'entscheidung,kriterien,vergleich'
                        },
                        {
                            'title': 'Nächsten besten Schritt bestimmen',
                            'description': 'Wähle den direkt wirksamsten nächsten Schritt bei vielen offenen Aufgaben.',
                            'example_input': 'Ich habe 10 offene Tasks. Bestimme den nächsten besten Schritt für heute.',
                            'tags': 'next-step,fokus,priorisierung'
                        },
                        {
                            'title': 'Aufgaben reduzieren und delegieren',
                            'description': 'Entscheide, was gestrichen, verschoben oder delegiert werden kann.',
                            'example_input': 'Hilf mir, meine Aufgabenliste zu kürzen und wichtige Dinge zu priorisieren.',
                            'tags': 'task-management,delegation,priorität'
                        },
                    ],
                },
            ],
        },
        {
            'name': 'Karriere & Zukunft',
            'icon': '🚀',
            'description': 'Bewerbung, Skill-Aufbau und erste Schritte in berufliche Projekte.',
            'subcategories': [
                {
                    'name': 'Bewerbung & Portfolio',
                    'description': 'Lebenslauf, Anschreiben und Projektportfolio für Schule, Praktikum und Nebenjob.',
                    'templates': [
                        {
                            'title': 'Anschreiben für Praktikum',
                            'description': 'Erstelle ein zielgerichtetes Anschreiben für einen Praktikumsplatz.',
                            'example_input': 'Schreibe ein Anschreiben für ein IT-Praktikum in einem mittelständischen Unternehmen.',
                            'tags': 'bewerbung,praktikum,anschreiben'
                        },
                        {
                            'title': 'Lebenslauf strukturieren',
                            'description': 'Bau einen klaren, kompakten Lebenslauf mit relevanten Stationen.',
                            'example_input': 'Hilf mir, meinen Lebenslauf für einen Ferienjob zu optimieren.',
                            'tags': 'cv,lebenslauf,job'
                        },
                        {
                            'title': 'Portfolio-Projekt beschreiben',
                            'description': 'Beschreibe ein Projekt so, dass Kompetenz und Wirkung sichtbar werden.',
                            'example_input': 'Formuliere mein Schulprojekt als Portfolio-Eintrag mit Ergebnis und Learnings.',
                            'tags': 'portfolio,projekt,karriere'
                        },
                    ],
                },
                {
                    'name': 'Skills & Weiterbildung',
                    'description': 'Lernpfade für berufsrelevante Fähigkeiten aufbauen und tracken.',
                    'templates': [
                        {
                            'title': 'Skill-Roadmap 90 Tage',
                            'description': 'Definiere Lernziele und Meilensteine für die nächsten 3 Monate.',
                            'example_input': 'Erstelle eine 90-Tage-Roadmap, um Python für Data Analysis zu lernen.',
                            'tags': 'roadmap,skill,weiterbildung'
                        },
                        {
                            'title': 'Lernressourcen kuratieren',
                            'description': 'Wähle passende Ressourcen nach Level und Zeitbudget.',
                            'example_input': 'Finde die besten kostenlosen Ressourcen für UI/UX-Grundlagen.',
                            'tags': 'ressourcen,lernen,kuratierung'
                        },
                        {
                            'title': 'Praxisprojekt für Skill-Aufbau',
                            'description': 'Plane ein kleines Umsetzungsprojekt für praktisches Lernen.',
                            'example_input': 'Gib mir ein Mini-Projekt, um JavaScript und APIs praktisch zu üben.',
                            'tags': 'projektbasiert,skillaufbau,praxis'
                        },
                    ],
                },
                {
                    'name': 'Business & Selbstständigkeit',
                    'description': 'Ideen validieren, einfache Angebote formulieren und Prozesse strukturieren.',
                    'templates': [
                        {
                            'title': 'Geschäftsidee validieren',
                            'description': 'Prüfe eine Idee auf Zielgruppe, Nutzen und Realisierbarkeit.',
                            'example_input': 'Validiere meine Idee für einen lokalen Nachhilfe-Service mit KI-Unterstützung.',
                            'tags': 'business,validierung,idee'
                        },
                        {
                            'title': 'Angebotstext erstellen',
                            'description': 'Erstelle einen klaren Angebotstext mit Leistungsumfang und Preislogik.',
                            'example_input': 'Formuliere ein Angebot für Social-Media-Design als Nebenjob.',
                            'tags': 'angebot,freelance,text'
                        },
                        {
                            'title': 'Kundenprozess skizzieren',
                            'description': 'Skizziere den Ablauf vom Erstkontakt bis zur Lieferung.',
                            'example_input': 'Plane einen einfachen Kundenprozess für meinen kleinen Design-Service.',
                            'tags': 'prozess,kundenreise,selbstständig'
                        },
                    ],
                },
            ],
        },
    ]

    for category_data in category_definitions:
        category = WorkflowCategory.query.filter_by(name=category_data['name']).first()
        if not category:
            category = make_model(
                WorkflowCategory,
                name=category_data['name'],
                icon=category_data['icon'],
                description=category_data['description'],
            )
            db.session.add(category)
            db.session.flush()
        else:
            category.icon = category_data['icon']
            category.description = category_data['description']

        for subcategory_data in category_data['subcategories']:
            subcategory = SubCategory.query.filter_by(
                category_id=category.id,
                name=subcategory_data['name']
            ).first()

            if not subcategory:
                subcategory = make_model(
                    SubCategory,
                    category_id=category.id,
                    name=subcategory_data['name'],
                    description=subcategory_data['description'],
                )
                db.session.add(subcategory)
                db.session.flush()
            else:
                subcategory.description = subcategory_data['description']

            for template_data in subcategory_data['templates']:
                existing_template = TaskTemplate.query.filter_by(
                    subcategory_id=subcategory.id,
                    title=template_data['title']
                ).first()

                if not existing_template:
                    db.session.add(
                        make_model(
                            TaskTemplate,
                            subcategory_id=subcategory.id,
                            title=template_data['title'],
                            description=template_data['description'],
                            example_input=template_data['example_input'],
                            tags=template_data['tags'],
                        )
                    )
                else:
                    existing_template.description = template_data['description']
                    existing_template.example_input = template_data['example_input']
                    existing_template.tags = template_data['tags']

    db.session.commit()


def seed_extended_data():
    """Befüllt neue Tabellen/Felder mit Beispieldaten, falls noch leer."""
    first_tool = Tool.query.first()
    first_skill = Skill.query.first()

    supplemental_tools = [
        {
            'name': 'Notion',
            'category': 'Planung & Organisation',
            'url': 'https://www.notion.so',
            'notes': 'All-in-One Workspace für Notizen, Projekte und Wissensmanagement.',
            'is_free': True,
            'free_tier_details': 'Free Plan mit Kernfunktionen für Einzelpersonen.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Aufgabenplanung, Wissensdatenbank, Team-Boards',
            'prompt_template': 'Erstelle eine klare Struktur für dieses Projekt in Notion: {{task}}',
        },
        {
            'name': 'Trello',
            'category': 'Planung & Organisation',
            'url': 'https://trello.com',
            'notes': 'Kanban-Boards für Aufgabenverwaltung und Teamarbeit.',
            'is_free': True,
            'free_tier_details': 'Kostenloser Einstieg mit Boards und Basis-Automation.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Kanban-Workflows und Priorisierung',
            'prompt_template': 'Brich folgende Aufgabe in Trello-Karten auf: {{task}}',
        },
        {
            'name': 'Google Scholar',
            'category': 'Internet-Recherche',
            'url': 'https://scholar.google.com',
            'notes': 'Wissenschaftliche Suche mit Zitaten und verwandten Arbeiten.',
            'is_free': True,
            'free_tier_details': 'Kostenlose Suche, Volltexte abhängig von Quelle.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Facharbeiten, wissenschaftliche Quellen',
            'prompt_template': 'Gib mir Suchphrasen für Google Scholar zu: {{task}}',
        },
        {
            'name': 'Semantic Scholar',
            'category': 'Internet-Recherche',
            'url': 'https://www.semanticscholar.org',
            'notes': 'KI-gestützte Paper-Suche und Themenüberblick.',
            'is_free': True,
            'free_tier_details': 'Kostenlos nutzbar.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Schneller Einstieg in Forschungsthemen',
            'prompt_template': 'Formuliere eine Suchstrategie für Semantic Scholar: {{task}}',
        },
        {
            'name': 'Connected Papers',
            'category': 'Internet-Recherche',
            'url': 'https://www.connectedpapers.com',
            'notes': 'Visualisiert Forschungszusammenhänge zwischen Publikationen.',
            'is_free': True,
            'free_tier_details': 'Kostenloser Basiszugang.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Themenkartierung und Literaturüberblick',
            'prompt_template': 'Erstelle eine Literatur-Karte mit Fokus auf: {{task}}',
        },
        {
            'name': 'Obsidian',
            'category': 'Mitschreiben & Dokumente',
            'url': 'https://obsidian.md',
            'notes': 'Lokales Wissensmanagement mit verlinkten Notizen.',
            'is_free': True,
            'free_tier_details': 'Private Nutzung kostenlos.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Lernnotizen, vernetztes Denken',
            'prompt_template': 'Strukturiere meine Notizen als Obsidian-Outline: {{task}}',
        },
        {
            'name': 'Miro',
            'category': 'Schulprojekte',
            'url': 'https://miro.com',
            'notes': 'Virtuelles Whiteboard für Brainstorming und Teamplanung.',
            'is_free': True,
            'free_tier_details': 'Kostenlose Basisversion verfügbar.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Teamideen, Projektmapping',
            'prompt_template': 'Erstelle ein Miro-Board-Konzept für: {{task}}',
        },
        {
            'name': 'Excalidraw',
            'category': 'Design & Präsentation',
            'url': 'https://excalidraw.com',
            'notes': 'Schnelle Skizzen und Diagramme im Handdrawn-Stil.',
            'is_free': True,
            'free_tier_details': 'Kostenlos im Browser.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Ablaufdiagramme, Ideenskizzen',
            'prompt_template': 'Plane ein Excalidraw-Diagramm für diesen Prozess: {{task}}',
        },
        {
            'name': 'Mermaid Live Editor',
            'category': 'Programmierung',
            'url': 'https://mermaid.live',
            'notes': 'Textbasiertes Erstellen von Fluss- und Architekturdiagrammen.',
            'is_free': True,
            'free_tier_details': 'Kostenlos nutzbar.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Systemdesign und Prozessvisualisierung',
            'prompt_template': 'Erzeuge ein Mermaid-Diagramm-Skript für: {{task}}',
        },
        {
            'name': 'Khan Academy',
            'category': 'Lernen & Schule',
            'url': 'https://www.khanacademy.org',
            'notes': 'Kostenlose Lernplattform mit Mathe- und Naturwissenschaftskursen.',
            'is_free': True,
            'free_tier_details': 'Komplett kostenlos für Lernende.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Grundlagen lernen und üben',
            'prompt_template': 'Baue einen Lernplan mit Khan Academy für: {{task}}',
        },
        {
            'name': 'GeoGebra',
            'category': 'Mathe & Wissenschaft',
            'url': 'https://www.geogebra.org',
            'notes': 'Interaktive Mathematik-Visualisierung für Schule und Studium.',
            'is_free': True,
            'free_tier_details': 'Kostenlos nutzbar.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Funktionen, Geometrie, Visualisierungen',
            'prompt_template': 'Erstelle einen GeoGebra-Plan für dieses Mathethema: {{task}}',
        },
        {
            'name': 'Overleaf',
            'category': 'Mitschreiben & Dokumente',
            'url': 'https://www.overleaf.com',
            'notes': 'Online-LaTeX-Editor für wissenschaftliche Dokumente.',
            'is_free': True,
            'free_tier_details': 'Free Plan mit Basisfunktionen.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Facharbeiten und wissenschaftliches Schreiben',
            'prompt_template': 'Erzeuge eine LaTeX-Dokumentstruktur für: {{task}}',
        },
        {
            'name': 'Gamma',
            'category': 'Design & Präsentation',
            'url': 'https://gamma.app',
            'notes': 'KI-unterstützte Erstellung moderner Präsentationen.',
            'is_free': True,
            'free_tier_details': 'Kostenloser Einstieg verfügbar.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Schnelle Präsentationsentwürfe',
            'prompt_template': 'Erstelle eine Präsentationsstruktur in Gamma für: {{task}}',
        },
        {
            'name': 'Figma',
            'category': 'Design & Präsentation',
            'url': 'https://www.figma.com',
            'notes': 'UI/UX-Design und kollaboratives Prototyping.',
            'is_free': True,
            'free_tier_details': 'Kostenlose Starter-Version.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Prototypen, Interface-Layouts',
            'prompt_template': 'Skizziere ein UI-Konzept in Figma für: {{task}}',
        },
        {
            'name': 'GitHub',
            'category': 'Programmierung',
            'url': 'https://github.com',
            'notes': 'Versionskontrolle und kollaborative Softwareentwicklung.',
            'is_free': True,
            'free_tier_details': 'Kostenlos mit privaten Repositories.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Codeverwaltung und Teamarbeit',
            'prompt_template': 'Plane Commits und Branches für dieses Projekt: {{task}}',
        },
        {
            'name': 'GitHub Projects',
            'category': 'Planung & Organisation',
            'url': 'https://github.com/features/issues',
            'notes': 'Task-Tracking direkt im Entwicklerworkflow.',
            'is_free': True,
            'free_tier_details': 'In GitHub-Plan enthalten.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Backlog, Sprintplanung, Aufgabenstatus',
            'prompt_template': 'Erstelle ein Issue-Board für folgende Roadmap: {{task}}',
        },
        {
            'name': 'Loom',
            'category': 'Kommunikation',
            'url': 'https://www.loom.com',
            'notes': 'Kurze Erklärvideos für asynchrone Kommunikation.',
            'is_free': True,
            'free_tier_details': 'Kostenloser Plan mit Basisgrenzen.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Erklärungen, Projekt-Updates',
            'prompt_template': 'Schreibe ein 90-Sekunden-Skript für ein Loom-Update zu: {{task}}',
        },
        {
            'name': 'Calendly',
            'category': 'Kommunikation',
            'url': 'https://calendly.com',
            'notes': 'Terminabstimmung ohne E-Mail-Pingpong.',
            'is_free': True,
            'free_tier_details': 'Kostenloser Basisplan.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Meetingplanung und Verfügbarkeiten',
            'prompt_template': 'Formuliere eine klare Terminanfrage für: {{task}}',
        },
        {
            'name': 'Airtable',
            'category': 'Planung & Organisation',
            'url': 'https://airtable.com',
            'notes': 'Flexible Tabellen-Datenbank für Projekte und Prozesse.',
            'is_free': True,
            'free_tier_details': 'Free Plan mit Basislimits.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Datenübersichten und Projekttracking',
            'prompt_template': 'Entwirf ein Airtable-Schema für: {{task}}',
        },
        {
            'name': 'HubSpot CRM',
            'category': 'Business & Selbstständigkeit',
            'url': 'https://www.hubspot.com/products/crm',
            'notes': 'CRM für Kontaktverwaltung und Vertriebsprozesse.',
            'is_free': True,
            'free_tier_details': 'Kostenloses CRM verfügbar.',
            'skill_requirement': 'Fortgeschritten',
            'best_for': 'Lead-Tracking und Kundenkommunikation',
            'prompt_template': 'Definiere einen einfachen CRM-Prozess für: {{task}}',
        },
        {
            'name': 'Canva Resume Builder',
            'category': 'Bewerbung & Portfolio',
            'url': 'https://www.canva.com/resumes/',
            'notes': 'Schneller Lebenslauf-Builder mit modernen Vorlagen.',
            'is_free': True,
            'free_tier_details': 'Viele Vorlagen im Free-Plan.',
            'skill_requirement': 'Anfänger',
            'best_for': 'Lebenslauf und Portfolio-Layout',
            'prompt_template': 'Erstelle eine klare CV-Struktur für dieses Profil: {{task}}',
        },
    ]

    for tool_data in supplemental_tools:
        existing_tool = Tool.query.filter_by(name=tool_data['name']).first()
        if not existing_tool:
            existing_tool = Tool()
            db.session.add(existing_tool)

        existing_tool.name = tool_data['name']
        existing_tool.category = tool_data['category']
        existing_tool.url = tool_data['url']
        existing_tool.notes = tool_data['notes']
        existing_tool.is_free = bool(tool_data['is_free'])
        existing_tool.free_tier_details = tool_data['free_tier_details']
        existing_tool.skill_requirement = tool_data['skill_requirement']
        existing_tool.best_for = tool_data['best_for']
        existing_tool.prompt_template = tool_data['prompt_template']

    if first_tool and first_tool.free_tier_details is None:
        first_tool.is_free = True
        first_tool.free_tier_details = 'Kostenlos nutzbare Basisversion verfügbar.'
        first_tool.skill_requirement = 'Anfänger'
        first_tool.best_for = 'Schnelle Aufgaben und Schulprojekte'
        first_tool.prompt_template = 'Hilf mir bei der Aufgabe: {{task}}. Gib eine klare Schritt-für-Schritt-Anleitung.'

    if first_tool and ToolUsageLog.query.first() is None:
        db.session.add_all([
            make_model(
                ToolUsageLog,
                tool_id=first_tool.id,
                task_description='Titelbild für eine Biologie-Präsentation erstellen',
                rating=4,
                timestamp=datetime.now(timezone.utc) - timedelta(days=2),
                was_helpful=True,
            ),
            make_model(
                ToolUsageLog,
                tool_id=first_tool.id,
                task_description='Recherche-Workflow für Facharbeit planen',
                rating=5,
                timestamp=datetime.now(timezone.utc) - timedelta(days=1),
                was_helpful=True,
            ),
        ])

    if PromptTemplate.query.first() is None:
        db.session.add_all([
            make_model(
                PromptTemplate,
                title='Recherche Zusammenfassung',
                prompt_text='Fasse die wichtigsten Fakten zu {{thema}} in 8 Stichpunkten mit Quellenangaben zusammen.',
                category='Recherche',
                tool_id=first_tool.id if first_tool else None,
                use_count=3,
            ),
            make_model(
                PromptTemplate,
                title='Lernkarten Generator',
                prompt_text='Erstelle aus folgendem Stoff 15 Frage-Antwort-Lernkarten: {{stoff}}',
                category='Lernen',
                tool_id=first_tool.id if first_tool else None,
                use_count=2,
            ),
        ])

    if WorkflowHistory.query.first() is None:
        db.session.add_all([
            make_model(
                WorkflowHistory,
                task_description='Vorbereitung Mathe-Klausur',
                recommendation_json='{"workflow": ["Themen sortieren", "Übungen lösen", "Fehleranalyse"]}',
                user_rating=4,
            ),
            make_model(
                WorkflowHistory,
                task_description='Infografik für Geographie',
                recommendation_json='{"workflow": ["Inhalte recherchieren", "Layout in Canva", "Finale Prüfung"]}',
                user_rating=5,
            ),
        ])

    history_entries = WorkflowHistory.query.order_by(WorkflowHistory.created_at.asc()).limit(5).all()
    if history_entries and RecommendationFeedback.query.first() is None:
        for history_entry in history_entries:
            try:
                recommendation_data = json.loads(history_entry.recommendation_json or '{}')
            except Exception:
                recommendation_data = {}

            recommended_tools = []
            for item in recommendation_data.get('recommended_tools', []):
                if isinstance(item, dict):
                    name = (item.get('name') or '').strip()
                elif isinstance(item, str):
                    name = item.strip()
                else:
                    name = ''
                if name:
                    recommended_tools.append(name)

            feedback = make_model(
                RecommendationFeedback,
                workflow_history_id=history_entry.id,
                task_description=history_entry.task_description,
                recommended_tools_json=recommended_tools,
                user_rating=history_entry.user_rating,
                accepted=True if history_entry.user_rating and history_entry.user_rating >= 4 else None,
                reused=True if history_entry.user_rating and history_entry.user_rating >= 4 else None,
                time_saved_minutes=30 if history_entry.user_rating and history_entry.user_rating >= 4 else None,
                note='Seeded baseline feedback',
            )
            db.session.add(feedback)

    if UserPreference.query.first() is None:
        db.session.add_all([
            make_model(UserPreference, key='preferred_language', value='de'),
            make_model(UserPreference, key='difficulty_level', value='mittel'),
            make_model(UserPreference, key='focus_areas', value='Mathe, Recherche, Präsentation'),
        ])

    if first_skill and SkillProgress.query.first() is None:
        db.session.add_all([
            make_model(
                SkillProgress,
                skill_id=first_skill.id,
                date=date.today() - timedelta(days=14),
                level='Anfänger',
                note='Grundlagen wiederholt',
            ),
            make_model(
                SkillProgress,
                skill_id=first_skill.id,
                date=date.today() - timedelta(days=7),
                level='Fortgeschritten',
                note='Übungsaufgaben sicher gelöst',
            ),
            make_model(
                SkillProgress,
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
    seed_categories()
