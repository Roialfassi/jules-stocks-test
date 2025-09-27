from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from services import firebase_service

def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a view.
    Verifies the Firebase ID token from the session or Authorization header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = None
        # 1. Check for token in session
        if 'user_token' in session:
            id_token = session['user_token']
        # 2. Check for Bearer token in Authorization header (for API requests)
        elif 'Authorization' in request.headers:
            auth_header = request.headers.get('Authorization')
            if auth_header.startswith('Bearer '):
                id_token = auth_header.split(' ')[1]

        if not id_token:
            # If it's an API request, return 401 Unauthorized
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Authentication token required'}), 401
            # For web pages, redirect to login
            return redirect(url_for('login', next=request.url))

        # 3. Verify the token
        decoded_token = firebase_service.verify_token(id_token)
        if not decoded_token:
            # Clear session if token is invalid
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 401
            return redirect(url_for('login'))

        # 4. Store user info in session for easy access
        uid = decoded_token['uid']
        if 'user' not in session or session['user']['uid'] != uid:
            user_profile = firebase_service.get_user(uid)
            if user_profile:
                session['user'] = {
                    'uid': uid,
                    'email': user_profile.get('email'),
                    'username': user_profile.get('username'),
                    'researchGroup': user_profile.get('researchGroup'),
                    'role': user_profile.get('role', 'user')
                }
            else:
                # User exists in Auth but not in Firestore, something is wrong
                session.clear()
                return jsonify({'status': 'error', 'message': 'User profile not found'}), 500

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to restrict access to admin users.
    Must be used *after* @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Administrator access required'}), 403
            # You might want to redirect to a specific 'unauthorized' page
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function