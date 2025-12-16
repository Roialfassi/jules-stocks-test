from functools import wraps
from flask import session, redirect, url_for, flash
from services.auth import auth_service

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user = auth_service.get_user(session['user_id'])
        if not user or user.get('role') != 'admin':
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function
