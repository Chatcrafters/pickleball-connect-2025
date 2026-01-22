"""
Authentication routes for admin login.
"""
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from utils.auth import check_admin_password

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if request.method == 'POST':
        password = request.form.get('password', '')

        if check_admin_password(password):
            session['is_admin'] = True
            session.permanent = True  # Keep logged in for 31 days (Flask default)
            flash('Login successful!', 'success')

            # Redirect to where they wanted to go, or admin dashboard
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('pcl.admin_dashboard'))
        else:
            flash('Invalid password.', 'danger')

    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    """Logout and clear session."""
    session.pop('is_admin', None)
    flash('Logged out.', 'info')
    return redirect(url_for('main.index'))
