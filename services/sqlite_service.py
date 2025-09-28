import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext
import bcrypt
import uuid
import random
from datetime import datetime, timezone

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

def get_user_by_email(email):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    return user

def get_user_by_id(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return user

def create_user_with_group(email, password, username, consent_given, ip_address):
    db = get_db()
    try:
        if get_user_by_email(email):
            raise ValueError("Email address is already in use by another account.")

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = str(uuid.uuid4())
        research_group = random.randint(1, 4)

        cursor = db.execute('SELECT COUNT(id) FROM users')
        participant_id = f"P{cursor.fetchone()[0] + 1:04d}"

        db.execute(
            """
            INSERT INTO users (id, email, password, username, participantId, researchGroup, consentGiven, consentTimestamp, consentIP, createdAt, lastLogin, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email, hashed_password, username, participant_id, research_group, 1 if consent_given else 0, datetime.now(timezone.utc), ip_address, datetime.now(timezone.utc), datetime.now(timezone.utc), 'user')
        )
        db.execute(
            """
            INSERT INTO balances (user_id, cashBalance, investedValue, totalPortfolioValue)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, 10000.00, 0.0, 10000.00)
        )
        db.execute(
            """
            INSERT INTO gamification (user_id) VALUES (?)
            """,
            (user_id,)
        )
        db.commit()
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        raise ValueError("Email address is already in use by another account.")
    except Exception as e:
        db.rollback()
        raise e