import os
import click
from app import app
from services import sqlite_service
import bcrypt
import uuid
from datetime import datetime, timezone

@click.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
def create_admin(username, email, password):
    """Creates a new user with the admin role."""
    with app.app_context():
        db = sqlite_service.get_db()
        try:
            user = sqlite_service.get_user_by_email(email)
            if user:
                click.echo(f"Error: User with email {email} already exists.")
                return

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            user_id = str(uuid.uuid4())
            research_group = 0
            participant_id = f"ADMIN-{username.upper()}"

            db.execute(
                """
                INSERT INTO users (id, email, password, username, participantId, researchGroup, consentGiven, consentTimestamp, consentIP, createdAt, lastLogin, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, email, hashed_password, username, participant_id, research_group, 1, datetime.now(timezone.utc), 'cli', datetime.now(timezone.utc), datetime.now(timezone.utc), 'admin')
            )

            # Initialize balance for the admin user
            db.execute(
                """
                INSERT INTO balances (user_id, cashBalance, investedValue, totalPortfolioValue)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, 0.0, 0.0, 0.0)
            )

            # Initialize gamification stats for the admin user
            db.execute(
                """
                INSERT INTO gamification (user_id) VALUES (?)
                """,
                (user_id,)
            )

            db.commit()
            click.echo(f"Admin user '{username}' created successfully.")

        except Exception as e:
            db.rollback()
            click.echo(f"An error occurred: {e}")

app.cli.add_command(create_admin)