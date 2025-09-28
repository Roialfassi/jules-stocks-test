import csv
import io
import json
from datetime import datetime, timezone
from services import sqlite_service

def log_action(user_id, action_type, action_category, action_data, session_id=None):
    """
    Logs a user action to the 'userActions' table in SQLite.
    """
    try:
        db = sqlite_service.get_db()
        db.execute(
            """
            INSERT INTO userActions (user_id, session_id, action_type, action_category, action_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, session_id, action_type, action_category, json.dumps(action_data), datetime.now(timezone.utc))
        )
        db.commit()
    except Exception as e:
        print(f"Error logging action for user {user_id}: {e}")

def record_consent(user_id, ip_address):
    """
    Updates the user's document with consent information.
    """
    try:
        db = sqlite_service.get_db()
        db.execute(
            "UPDATE users SET consentGiven = 1, consentTimestamp = ?, consentIP = ? WHERE id = ?",
            (datetime.now(timezone.utc), ip_address, user_id)
        )
        db.commit()
    except Exception as e:
        print(f"Error recording consent for user {user_id}: {e}")

def export_data_to_csv(table_name):
    """
    Exports all rows from a specified SQLite table to a CSV string.
    """
    db = sqlite_service.get_db()
    try:
        # Basic security check to prevent SQL injection on table names
        if not table_name.isalnum():
            raise ValueError("Invalid table name")

        cursor = db.execute(f'SELECT * FROM {table_name}')
        rows = cursor.fetchall()

        if not rows:
            return ""

        headers = [description[0] for description in cursor.description]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)

        return output.getvalue()

    except Exception as e:
        print(f"Error exporting table {table_name} to CSV: {e}")
        return None

def get_admin_dashboard_analytics():
    """
    Fetches aggregate data for the admin dashboard from SQLite.
    """
    try:
        db = sqlite_service.get_db()

        total_users = db.execute('SELECT COUNT(id) FROM users').fetchone()[0]
        total_trades = db.execute('SELECT COUNT(id) FROM transactions').fetchone()[0]

        users_by_group_rows = db.execute(
            'SELECT researchGroup, COUNT(id) FROM users GROUP BY researchGroup'
        ).fetchall()

        users_by_group = {1: 0, 2: 0, 3: 0, 4: 0}
        for row in users_by_group_rows:
            users_by_group[row['researchGroup']] = row[1]

        return {
            'totalUsers': total_users,
            'usersByGroup': users_by_group,
            'totalTrades': total_trades,
            'lastUpdated': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        print(f"Error fetching admin analytics: {e}")
        return {}