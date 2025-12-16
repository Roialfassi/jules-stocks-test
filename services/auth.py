import random
import uuid
import datetime
from services.db import db, Config

class AuthService:
    def register_user(self, email, password, username=None):
        raise NotImplementedError

    def login_user(self, email, password):
        raise NotImplementedError

    def get_user(self, user_id):
        raise NotImplementedError

    def _assign_group(self):
        return random.randint(1, 4)

    def _generate_participant_id(self):
        return f"P{random.randint(1000, 9999)}"

    def verify_token(self, id_token):
        return None

class FirebaseAuthService(AuthService):
    def register_user(self, email, password, username=None, consent=False):
        from firebase_admin import auth
        try:
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )

            group = self._assign_group()
            pid = self._generate_participant_id()

            user_data = {
                'email': email,
                'username': username,
                'participantId': pid,
                'researchGroup': group,
                'createdAt': datetime.datetime.now().isoformat(),
                'role': 'user',
                'consentGiven': consent,
                'consentTimestamp': datetime.datetime.now().isoformat() if consent else None
            }

            db.collection('users').document(user_record.uid).set(user_data)
            return user_record.uid, user_data
        except Exception as e:
            print(f"Error creating user: {e}")
            raise e

    def login_user(self, email, password):
        # Using Identity Toolkit API for server-side login validation (MVP/Testing)
        import requests
        import os

        api_key = os.getenv('FIREBASE_API_KEY')
        if not api_key:
             print("FIREBASE_API_KEY not set for server-side login.")
             return None

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        try:
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                data = r.json()
                return {'id': data['localId'], 'email': email}
        except Exception as e:
            print(f"Error logging in: {e}")
        return None

    def verify_token(self, id_token):
        from firebase_admin import auth
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            return None

    def get_user(self, user_id):
        doc = db.collection('users').document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

class MockAuthService(AuthService):
    def register_user(self, email, password, username=None, consent=False):
        users = db.where('users', 'email', '==', email)
        if users:
            raise ValueError("User already exists")

        user_id = str(uuid.uuid4())
        group = self._assign_group()
        pid = self._generate_participant_id()

        user_data = {
            'id': user_id, # Inject ID
            'email': email,
            'password': password,
            'username': username,
            'participantId': pid,
            'researchGroup': group,
            'createdAt': datetime.datetime.now().isoformat(),
            'role': 'user',
            'consentGiven': consent,
            'consentTimestamp': datetime.datetime.now().isoformat() if consent else None
        }

        db.collection('users').document(user_id).set(user_data)
        return user_id, user_data

    def login_user(self, email, password):
        users = db.where('users', 'email', '==', email)
        if not users:
            return None

        user = users[0]
        # In SQLite/Mock, users[0] is the dict data
        # Check password
        if user.get('password') == password:
            return user
        return None

    def get_user(self, user_id):
        doc = db.collection('users').document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            # Ensure ID is in there
            if 'id' not in data:
                data['id'] = user_id
            return data
        return None

def get_auth_service():
    if Config.DB_TYPE == 'firebase':
        return FirebaseAuthService()
    else:
        return MockAuthService()

auth_service = get_auth_service()
