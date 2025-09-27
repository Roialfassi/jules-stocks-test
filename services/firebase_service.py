import os
import random
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, firestore

db = None

def initialize_firebase(config_path):
    """
    Initializes the Firebase Admin SDK using a service account.
    """
    global db
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(config_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': f"https://{os.environ.get('FIREBASE_PROJECT_ID')}.firebaseio.com"
            })
            db = firestore.client()
            print("Firebase initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            raise e
    if db is None:
        db = firestore.client()

def verify_token(id_token):
    """
    Verifies the Firebase ID token and returns the decoded token.
    Returns None if the token is invalid.
    """
    if not id_token:
        return None
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

def get_user(uid):
    """
    Retrieves a user's profile from the Firestore 'users' collection.
    """
    try:
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            return user_doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting user {uid}: {e}")
        return None

def create_user_with_group(email, password, username, consent_given, ip_address):
    """
    Creates a new user in Firebase Auth and a corresponding document in Firestore.
    Assigns the user to a random research group and gives them an initial balance.
    """
    try:
        # 1. Create user in Firebase Authentication
        user_record = auth.create_user(email=email, password=password, display_name=username)
        uid = user_record.uid

        # 2. Assign to a random research group (1-4)
        research_group = random.randint(1, 4)

        # 3. Generate a unique participant ID
        users_count = db.collection('users').stream()
        participant_id = f"P{sum(1 for _ in users_count) + 1:04d}"

        # 4. Create user document in Firestore
        user_ref = db.collection('users').document(uid)
        user_data = {
            'email': email,
            'username': username,
            'participantId': participant_id,
            'researchGroup': research_group,
            'consentGiven': consent_given,
            'consentTimestamp': datetime.utcnow(),
            'consentIP': ip_address,
            'createdAt': datetime.utcnow(),
            'lastLogin': datetime.utcnow(),
            'role': 'user' # Default role
        }
        user_ref.set(user_data)

        # 5. Initialize user's balance
        balance_ref = db.collection('balances').document(uid)
        balance_ref.set({
            'cashBalance': 10000.00,
            'investedValue': 0.0,
            'totalPortfolioValue': 10000.00,
            'totalRealizedPnL': 0.0,
            'totalUnrealizedPnL': 0.0,
            'totalTrades': 0,
            'winningTrades': 0,
            'losingTrades': 0,
            'lastCalculated': datetime.utcnow()
        })

        # 6. Initialize gamification stats
        gamification_ref = db.collection('gamification').document(uid)
        gamification_ref.set({
            'totalXP': 0,
            'currentLevel': 1,
            'xpToNextLevel': 100,
            'loginStreak': 1,
            'tradingStreak': 0,
            'profitableStreak': 0,
            'achievementsViewed': 0,
            'leaderboardViews': 0
        })

        print(f"Successfully created user {uid} in group {research_group}")
        return user_record

    except auth.EmailAlreadyExistsError:
        raise ValueError("Email address is already in use by another account.")
    except Exception as e:
        print(f"Error creating user: {e}")
        raise e

def send_password_reset_email(email):
    """
    Sends a password reset email to the given email address.
    """
    try:
        link = auth.generate_password_reset_link(email)
        # Here you would integrate with an email service (e.g., SendGrid, Mailgun)
        # to send the link to the user. For this project, we'll just print it.
        print(f"Password reset link for {email}: {link}")
        return True
    except auth.UserNotFoundError:
        # Don't reveal that the user does not exist
        print(f"Password reset requested for non-existent user: {email}")
        return True
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False