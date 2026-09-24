"""
Admin Authentication Utilities
"""
from functools import wraps
from flask import redirect, url_for, session, request
import os

def check_admin_password(password):
    """Check if password matches admin password"""
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    return password == admin_password

def admin_required(f):
    """Decorator to require a logged-in, active user with role 'admin'.

    Uses the user accounts from routes/auth.py (session['user_id']); the old
    session['is_admin'] flag is no longer set anywhere since the switch to
    user accounts.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import User

        user = User.query.get(session['user_id']) if 'user_id' in session else None
        if not user or not user.is_active or user.role != 'admin':
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
