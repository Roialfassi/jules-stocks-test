from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from services import sqlite_service

def login_required(f):
    """
    Decorator to ensure a user is logged in via session before accessing a view.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))

        # Optional: re-verify user exists and refresh session data if needed
        if 'user' not in session:
             user = sqlite_service.get_user_by_id(session["user_id"])
             if not user:
                 session.clear()
                 if request.path.startswith('/api/'):
                    return jsonify({'status': 'error', 'message': 'User not found'}), 401
                 return redirect(url_for('login'))
             session['user'] = {
                'uid': user['id'],
                'email': user['email'],
                'username': user['username'],
                'researchGroup': user['researchGroup'],
                'role': user['role']
             }

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