import csv
import io
from datetime import datetime
from services import firebase_service

def log_action(user_id, action_type, action_category, action_data, session_id=None):
    """
    Logs a user action to the 'userActions' collection in Firestore.
    """
    try:
        db = firebase_service.db
        action_ref = db.collection('userActions').document()
        action_ref.set({
            'userId': user_id,
            'sessionId': session_id,  # Can be integrated with Flask session
            'actionType': action_type,
            'actionCategory': action_category,
            'actionData': action_data,  # This can be a dict with more details
            'timestamp': datetime.utcnow()
        })
    except Exception as e:
        print(f"Error logging action for user {user_id}: {e}")

def record_consent(user_id, ip_address):
    """
    Updates the user's document with consent information.
    This is now integrated into create_user_with_group in firebase_service.
    This function can be used if consent needs to be re-recorded.
    """
    try:
        db = firebase_service.db
        user_ref = db.collection('users').document(user_id)
        user_ref.update({
            'consentGiven': True,
            'consentTimestamp': datetime.utcnow(),
            'consentIP': ip_address
        })
    except Exception as e:
        print(f"Error recording consent for user {user_id}: {e}")

def export_data_to_csv(collection_name):
    """
    Exports all documents from a specified Firestore collection to a CSV string.
    This is a basic implementation. A real-world version would handle
    nested data and relationships more gracefully.
    """
    try:
        db = firebase_service.db
        docs = db.collection(collection_name).stream()

        # Use an in-memory string buffer to build the CSV
        output = io.StringIO()

        first_doc = True
        writer = None

        for doc in docs:
            data = doc.to_dict()
            # Add the document ID to the data
            data['doc_id'] = doc.id

            if first_doc:
                # Initialize CSV writer with headers from the first document
                headers = sorted(data.keys())
                writer = csv.DictWriter(output, fieldnames=headers)
                writer.writeheader()
                first_doc = False

            # Clean data for CSV writing (e.g., convert datetimes to ISO format)
            clean_data = {}
            for key, value in data.items():
                if isinstance(value, datetime):
                    clean_data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                     # Simple serialization for nested objects.
                    clean_data[key] = str(value)
                else:
                    clean_data[key] = value

            # Ensure all headers are present in the row
            row_data = {h: clean_data.get(h, '') for h in headers}
            writer.writerow(row_data)

        return output.getvalue()

    except Exception as e:
        print(f"Error exporting collection {collection_name} to CSV: {e}")
        return None

def get_admin_dashboard_analytics():
    """
    Fetches aggregate data for the admin dashboard.
    """
    try:
        db = firebase_service.db

        # Total users
        total_users = len(list(db.collection('users').stream()))

        # Users per group
        users_by_group = {1: 0, 2: 0, 3: 0, 4: 0}
        for user_doc in db.collection('users').stream():
            group = user_doc.to_dict().get('researchGroup', 0)
            if group in users_by_group:
                users_by_group[group] += 1

        # Total trades
        total_trades = len(list(db.collection('transactions').stream()))

        return {
            'totalUsers': total_users,
            'usersByGroup': users_by_group,
            'totalTrades': total_trades,
            'lastUpdated': datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error fetching admin analytics: {e}")
        return {}