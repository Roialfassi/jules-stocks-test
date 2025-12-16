from services.db import db
import datetime
import uuid
import csv
import io

class ResearchService:
    def log_action(self, user_id, action_type, details=None):
        action_id = str(uuid.uuid4())
        db.collection('userActions').document(action_id).set({
            'userId': user_id,
            'actionType': action_type,
            'details': details or {},
            'timestamp': datetime.datetime.now().isoformat()
        })

    def get_study_stats(self):
        # Count users per group
        users = db.collection('users').stream()
        groups = {1: 0, 2: 0, 3: 0, 4: 0}
        total_users = 0

        for u in users:
            data = u.to_dict()
            g = data.get('researchGroup', 1)
            if g in groups:
                groups[g] += 1
            total_users += 1

        return {
            'totalUsers': total_users,
            'groups': groups
        }

    def export_users_csv(self):
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['UserID', 'ParticipantID', 'Email', 'Group', 'CreatedAt', 'ConsentGiven'])

        users = db.collection('users').stream()
        for u in users:
            d = u.to_dict()
            writer.writerow([
                u.id if hasattr(u, 'id') else d.get('id'),
                d.get('participantId'),
                d.get('email'),
                d.get('researchGroup'),
                d.get('createdAt'),
                d.get('consentGiven')
            ])

        return output.getvalue()

    def export_trades_csv(self):
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['TransactionID', 'UserID', 'Symbol', 'Type', 'Quantity', 'Price', 'TotalAmount', 'Timestamp'])

        txs = db.collection('transactions').stream()
        for t in txs:
            d = t.to_dict()
            writer.writerow([
                t.id if hasattr(t, 'id') else d.get('id', ''), # MockDB issues with IDs
                d.get('userId'),
                d.get('symbol'),
                d.get('type'),
                d.get('quantity'),
                d.get('price'),
                d.get('totalAmount'),
                d.get('timestamp')
            ])

        return output.getvalue()

research_service = ResearchService()
