"""
Simple authentication decorator for admin routes.
Uses a shared admin password stored in environment variable.
"""
from functools import wraps
from flask import request, redirect, url_for, session, flash
import os

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

def admin_required(f):
    """
    Decorator to protect admin routes.
    Checks if user is authenticated via session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ADMIN_PASSWORD:
            # No password configured - block access in production
            flash('Admin access not configured. Set ADMIN_PASSWORD in environment.', 'danger')
            return redirect(url_for('main.index'))

        if not session.get('is_admin'):
            # Store the URL they wanted to access
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function


def check_admin_password(password):
    """Verify admin password."""
    if not ADMIN_PASSWORD:
        return False
    return password == ADMIN_PASSWORD
