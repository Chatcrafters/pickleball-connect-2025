"""
Auth Routes - Login for Directors and Admins only
Players use token-based access (no login needed)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from models import db, User
from functools import wraps

auth = Blueprint('auth', __name__, url_prefix='/auth')


# ============================================================================
# DECORATORS
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte einloggen', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte einloggen', 'warning')
            return redirect(url_for('auth.login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Keine Berechtigung', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


# ============================================================================
# LOGIN / LOGOUT
# ============================================================================

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Email und Passwort erforderlich', 'danger')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Ungueltige Anmeldedaten', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Account ist deaktiviert', 'danger')
            return redirect(url_for('auth.login'))
        
        # Login successful
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.get_full_name()
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        flash(f'Willkommen, {user.get_full_name()}!', 'success')
        return redirect(url_for('auth.dashboard'))
    
    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    session.clear()
    flash('Erfolgreich abgemeldet', 'success')
    return redirect(url_for('main.index'))


# ============================================================================
# DASHBOARD
# ============================================================================

@auth.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    
    if user.role == 'admin':
        # Admin stats
        total_users = User.query.count()
        directors = User.query.filter_by(role='director').count()
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        return render_template('auth/dashboard.html', 
                             user=user,
                             stats={'total': total_users, 'directors': directors},
                             recent_users=recent_users)
    else:
        # Director dashboard
        return render_template('auth/dashboard.html', user=user)


# ============================================================================
# PROFILE
# ============================================================================

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.organization = request.form.get('organization', '').strip()
        
        # Password change
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            if len(new_password) < 6:
                flash('Passwort muss mindestens 6 Zeichen haben', 'danger')
                return redirect(url_for('auth.profile'))
            user.set_password(new_password)
        
        db.session.commit()
        session['user_name'] = user.get_full_name()
        flash('Profil aktualisiert!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', user=user)


# ============================================================================
# ADMIN: USER MANAGEMENT
# ============================================================================

@auth.route('/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users.html', users=users)


@auth.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'director')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        if not email or not password:
            flash('Email und Passwort erforderlich', 'danger')
            return redirect(url_for('auth.create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email bereits registriert', 'danger')
            return redirect(url_for('auth.create_user'))
        
        user = User(
            email=email,
            role=role if role in ['director', 'admin'] else 'director',
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {email} erstellt!', 'success')
        return redirect(url_for('auth.admin_users'))
    
    return render_template('auth/create_user.html')


@auth.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Dont deactivate yourself
    if user.id == session['user_id']:
        flash('Du kannst dich nicht selbst deaktivieren', 'danger')
        return redirect(url_for('auth.admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'aktiviert' if user.is_active else 'deaktiviert'
    flash(f'{user.email} wurde {status}', 'success')
    return redirect(url_for('auth.admin_users'))


@auth.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == session['user_id']:
        flash('Du kannst dich nicht selbst loeschen', 'danger')
        return redirect(url_for('auth.admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'{user.email} geloescht', 'success')
    return redirect(url_for('auth.admin_users'))
