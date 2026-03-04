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


class WorkflowCategory(db.Model):
    """Die drei Hauptbereiche der App."""
    __tablename__ = 'workflow_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    icon = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    subcategories = db.relationship('SubCategory', backref='category', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
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
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
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


class SchoolProject(db.Model):
    """Tracking für Schulprojekte."""
    __tablename__ = 'school_projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='offen')  # offen / in_arbeit / fertig
    description = db.Column(db.String(1500), nullable=True)
    notes = db.Column(db.String(2000), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subject': self.subject,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'status': self.status,
            'description': self.description,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


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
    ]

    for category_data in category_definitions:
        category = WorkflowCategory.query.filter_by(name=category_data['name']).first()
        if not category:
            category = WorkflowCategory(
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
                subcategory = SubCategory(
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
                    db.session.add(TaskTemplate(
                        subcategory_id=subcategory.id,
                        title=template_data['title'],
                        description=template_data['description'],
                        example_input=template_data['example_input'],
                        tags=template_data['tags'],
                    ))
                else:
                    existing_template.description = template_data['description']
                    existing_template.example_input = template_data['example_input']
                    existing_template.tags = template_data['tags']

    db.session.commit()


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
    seed_categories()
