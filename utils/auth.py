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
    """Decorator to require admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
