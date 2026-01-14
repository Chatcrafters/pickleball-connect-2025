from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from models import db, PCLTournament, PCLTeam, PCLRegistration, Player, SHIRT_SIZES, COUNTRY_FLAGS
from datetime import datetime, date
from werkzeug.utils import secure_filename
from utils.supabase_storage import upload_photo_to_supabase, get_photo_url
from utils.whatsapp import send_profile_completion_link
import os
import csv
import io

pcl = Blueprint('pcl', __name__)

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================
UPLOAD_FOLDER = 'static/uploads/pcl'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# MULTI-LANGUAGE TRANSLATIONS
# ============================================================================
TRANSLATIONS = {
    'EN': {
        'page_title': 'PCL Player Registration',
        'team': 'Team',
        'personal_info': 'Personal Information',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'email': 'Email',
        'phone': 'Phone (optional)',
        'gender': 'Gender',
        'male': 'Male',
        'female': 'Female',
        'birth_year': 'Birth Year',
        'role': 'Role',
        'player': 'Player',
        'captain': 'Team Captain',
        'shirt_info': 'Shirt Information',
        'shirt_name': 'Name on Shirt',
        'shirt_name_help': 'How your name appears on the jersey',
        'shirt_size': 'Shirt Size',
        'profile': 'Profile',
        'photo': 'Profile Photo',
        'photo_help': 'Required. JPG, PNG, max 5MB. Square format recommended.',
        'bio': 'Short Bio',
        'bio_placeholder': 'Tell us about yourself, your pickleball journey...',
        'social_media': 'Social Media (optional)',
        'optional_info': 'Optional Information',
        'video_url': 'Video URL (Highlight Reel)',
        'dupr_rating': 'DUPR Rating',
        'language': 'Preferred Language',
        'privacy_accept': 'I accept the data processing for PCL registration',
        'submit': 'Register',
        'update': 'Update Registration',
        'required': 'Required',
        'success_title': 'Registration Complete!',
        'success_message': 'Thank you for registering for PCL.',
        'captain_dashboard': 'Team Captain Dashboard',
        'team_status': 'Team Status',
        'registration_link': 'Registration Link for Players',
        'copy_link': 'Copy Link',
        'players_registered': 'Players Registered',
        'men': 'Men',
        'women': 'Women',
        'complete': 'Complete',
        'incomplete': 'Incomplete',
        'send_reminder': 'Send Profile Link',
        'export_data': 'Export CSV',
    },
    'DE': {
        'page_title': 'PCL Spieler-Registrierung',
        'team': 'Team',
        'personal_info': 'Persönliche Informationen',
        'first_name': 'Vorname',
        'last_name': 'Nachname',
        'email': 'E-Mail',
        'phone': 'Telefon (optional)',
        'gender': 'Geschlecht',
        'male': 'Männlich',
        'female': 'Weiblich',
        'birth_year': 'Geburtsjahr',
        'role': 'Rolle',
        'player': 'Spieler',
        'captain': 'Teamkapitän',
        'shirt_info': 'Shirt-Informationen',
        'shirt_name': 'Name auf dem Shirt',
        'shirt_name_help': 'So erscheint dein Name auf dem Trikot',
        'shirt_size': 'Shirt-Größe',
        'profile': 'Profil',
        'photo': 'Profilbild',
        'photo_help': 'Pflichtfeld. JPG, PNG, max 5MB. Quadratisches Format empfohlen.',
        'bio': 'Kurze Bio',
        'bio_placeholder': 'Erzähl uns von dir und deiner Pickleball-Reise...',
        'social_media': 'Social Media (optional)',
        'optional_info': 'Optionale Informationen',
        'video_url': 'Video-URL (Highlight-Video)',
        'dupr_rating': 'DUPR Rating',
        'language': 'Bevorzugte Sprache',
        'privacy_accept': 'Ich stimme der Datenverarbeitung für die PCL-Registrierung zu',
        'submit': 'Registrieren',
        'update': 'Registrierung aktualisieren',
        'required': 'Pflichtfeld',
        'success_title': 'Registrierung erfolgreich!',
        'success_message': 'Danke für deine Registrierung zur PCL.',
        'captain_dashboard': 'Teamkapitän Dashboard',
        'team_status': 'Team-Status',
        'registration_link': 'Registrierungslink für Spieler',
        'copy_link': 'Link kopieren',
        'players_registered': 'Registrierte Spieler',
        'men': 'Männer',
        'women': 'Frauen',
        'complete': 'Vollständig',
        'incomplete': 'Unvollständig',
        'send_reminder': 'Profil-Link senden',
        'export_data': 'CSV exportieren',
    },
    'ES': {
        'page_title': 'Registro de Jugadores PCL',
        'team': 'Equipo',
        'personal_info': 'Información Personal',
        'first_name': 'Nombre',
        'last_name': 'Apellido',
        'email': 'Correo electrónico',
        'phone': 'Teléfono (opcional)',
        'gender': 'Género',
        'male': 'Masculino',
        'female': 'Femenino',
        'birth_year': 'Año de nacimiento',
        'role': 'Rol',
        'player': 'Jugador',
        'captain': 'Capitán',
        'shirt_info': 'Información de la Camiseta',
        'shirt_name': 'Nombre en la camiseta',
        'shirt_name_help': 'Así aparecerá tu nombre en la camiseta',
        'shirt_size': 'Talla de camiseta',
        'profile': 'Perfil',
        'photo': 'Foto de perfil',
        'photo_help': 'Obligatorio. JPG, PNG, máx 5MB. Formato cuadrado recomendado.',
        'bio': 'Biografía breve',
        'bio_placeholder': 'Cuéntanos sobre ti y tu viaje en pickleball...',
        'social_media': 'Redes Sociales (opcional)',
        'optional_info': 'Información Opcional',
        'video_url': 'URL del Video (Highlights)',
        'dupr_rating': 'Rating DUPR',
        'language': 'Idioma preferido',
        'privacy_accept': 'Acepto el procesamiento de datos para el registro PCL',
        'submit': 'Registrarse',
        'update': 'Actualizar registro',
        'required': 'Obligatorio',
        'success_title': '¡Registro completado!',
        'success_message': 'Gracias por registrarte en PCL.',
        'captain_dashboard': 'Panel del Capitán',
        'team_status': 'Estado del Equipo',
        'registration_link': 'Enlace de registro para jugadores',
        'copy_link': 'Copiar enlace',
        'players_registered': 'Jugadores registrados',
        'men': 'Hombres',
        'women': 'Mujeres',
        'complete': 'Completo',
        'incomplete': 'Incompleto',
        'send_reminder': 'Enviar enlace de perfil',
        'export_data': 'Exportar CSV',
    },
    'FR': {
        'page_title': 'Inscription Joueur PCL',
        'team': 'Équipe',
        'personal_info': 'Informations Personnelles',
        'first_name': 'Prénom',
        'last_name': 'Nom',
        'email': 'E-mail',
        'phone': 'Téléphone (optionnel)',
        'gender': 'Genre',
        'male': 'Homme',
        'female': 'Femme',
        'birth_year': 'Année de naissance',
        'role': 'Rôle',
        'player': 'Joueur',
        'captain': 'Capitaine',
        'shirt_info': 'Informations Maillot',
        'shirt_name': 'Nom sur le maillot',
        'shirt_name_help': 'Comment votre nom apparaîtra sur le maillot',
        'shirt_size': 'Taille du maillot',
        'profile': 'Profil',
        'photo': 'Photo de profil',
        'photo_help': 'Obligatoire. JPG, PNG, max 5Mo. Format carré recommandé.',
        'bio': 'Courte bio',
        'bio_placeholder': 'Parlez-nous de vous et de votre parcours pickleball...',
        'social_media': 'Réseaux Sociaux (optionnel)',
        'optional_info': 'Informations Optionnelles',
        'video_url': 'URL Vidéo (Highlights)',
        'dupr_rating': 'Rating DUPR',
        'language': 'Langue préférée',
        'privacy_accept': "J'accepte le traitement des données pour l'inscription PCL",
        'submit': "S'inscrire",
        'update': "Mettre à jour l'inscription",
        'required': 'Obligatoire',
        'success_title': 'Inscription réussie!',
        'success_message': 'Merci pour votre inscription à PCL.',
        'captain_dashboard': 'Tableau de bord Capitaine',
        'team_status': "Statut de l'équipe",
        'registration_link': "Lien d'inscription pour les joueurs",
        'copy_link': 'Copier le lien',
        'players_registered': 'Joueurs inscrits',
        'men': 'Hommes',
        'women': 'Femmes',
        'complete': 'Complet',
        'incomplete': 'Incomplet',
        'send_reminder': 'Envoyer lien de profil',
        'export_data': 'Exporter CSV',
    }
}

def get_translations(lang='EN'):
    """Get translations for a language, fallback to EN"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['EN'])


# ============================================================================
# ADMIN ROUTES - TOURNAMENT MANAGEMENT
# ============================================================================

@pcl.route('/admin')
def admin_dashboard():
    """PCL Admin Dashboard - Overview of all tournaments"""
    tournaments = PCLTournament.query.order_by(PCLTournament.start_date.desc()).all()
    return render_template('pcl/admin_dashboard.html', tournaments=tournaments)


@pcl.route('/admin/tournament/create', methods=['GET', 'POST'])
def create_tournament():
    """Create a new PCL tournament"""
    if request.method == 'POST':
        try:
            tournament = PCLTournament(
                name=request.form['name'],
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
                location=request.form['location'],
                description=request.form.get('description'),
                registration_deadline=datetime.strptime(request.form['registration_deadline'], '%Y-%m-%dT%H:%M')
            )
            
            db.session.add(tournament)
            db.session.commit()
            flash(f'Tournament "{tournament.name}" created successfully!', 'success')
            return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating tournament: {str(e)}', 'danger')
    
    return render_template('pcl/admin_tournament_form.html', tournament=None)


@pcl.route('/admin/tournament/<int:tournament_id>')
def admin_tournament_detail(tournament_id):
    """Admin view of a tournament with all teams"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    # Group teams by age category
    teams_19 = tournament.teams.filter_by(age_category='+19').order_by(PCLTeam.country_name).all()
    teams_50 = tournament.teams.filter_by(age_category='+50').order_by(PCLTeam.country_name).all()
    
    return render_template('pcl/admin_tournament_detail.html', 
                         tournament=tournament,
                         teams_19=teams_19,
                         teams_50=teams_50,
                         now=datetime.utcnow())


@pcl.route('/admin/tournament/<int:tournament_id>/add-team', methods=['GET', 'POST'])
def add_team(tournament_id):
    """Add a team to a tournament"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        try:
            country_code = request.form['country_code'].upper()
            
            team = PCLTeam(
                tournament_id=tournament.id,
                country_code=country_code,
                country_name=request.form['country_name'],
                country_flag=COUNTRY_FLAGS.get(country_code, '🏳️'),
                age_category=request.form['age_category'],
                min_men=int(request.form.get('min_men', 2)),
                max_men=int(request.form.get('max_men', 4)),
                min_women=int(request.form.get('min_women', 2)),
                max_women=int(request.form.get('max_women', 4)),
                captain_token=PCLTeam.generate_token()
            )
            
            db.session.add(team)
            db.session.commit()
            flash(f'Team {team.country_flag} {team.country_name} {team.age_category} added!', 'success')
            return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding team: {str(e)}', 'danger')
    
    return render_template('pcl/admin_add_team.html', 
                         tournament=tournament,
                         country_flags=COUNTRY_FLAGS)


@pcl.route('/admin/team/<int:team_id>')
def admin_team_detail(team_id):
    """Admin view of a specific team with edit/delete functionality"""
    team = PCLTeam.query.get_or_404(team_id)
    
    men = team.registrations.filter_by(gender='male').all()
    women = team.registrations.filter_by(gender='female').all()
    
    return render_template('pcl/admin_team_detail.html', 
                         team=team,
                         men=men,
                         women=women)


@pcl.route('/admin/team/<int:team_id>/delete', methods=['POST'])
def delete_team(team_id):
    """Delete a team and all its registrations"""
    team = PCLTeam.query.get_or_404(team_id)
    tournament_id = team.tournament_id
    team_name = f"{team.country_name} {team.age_category}"
    
    try:
        # Delete all registrations first
        PCLRegistration.query.filter_by(team_id=team_id).delete()
        db.session.delete(team)
        db.session.commit()
        flash(f'Team "{team_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting team: {str(e)}', 'danger')
    
    return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament_id))


@pcl.route('/admin/team/<int:team_id>/export')
def export_team_data(team_id):
    """Export team data as CSV"""
    team = PCLTeam.query.get_or_404(team_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Phone', 'Gender', 'Birth Year',
        'Captain', 'Shirt Name', 'Shirt Size', 'Status', 'Bio'
    ])
    
    for reg in team.registrations.all():
        writer.writerow([
            reg.first_name,
            reg.last_name,
            reg.email,
            reg.phone or '',
            reg.gender,
            reg.birth_year or '',
            'Yes' if reg.is_captain else 'No',
            reg.shirt_name,
            reg.shirt_size,
            reg.status,
            reg.bio or ''
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'pcl_{team.country_code}_{team.age_category}_players.csv'
    )


@pcl.route('/admin/export-shirts/<int:tournament_id>')
def export_shirt_list(tournament_id):
    """Export shirt list for all teams"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Team', 'Category', 'Shirt Name', 'Size', 'Player Name'])
    
    for team in tournament.teams.all():
        for reg in team.registrations.all():
            writer.writerow([
                f"{team.country_flag} {team.country_name}",
                team.age_category,
                reg.shirt_name,
                reg.shirt_size,
                f"{reg.first_name} {reg.last_name}"
            ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'pcl_{tournament.id}_shirt_list.csv'
    )


# ============================================================================
# CAPTAIN DASHBOARD ROUTES (Secret Link Access)
# ============================================================================

@pcl.route('/team/<token>')
def captain_dashboard(token):
    """Captain dashboard - accessed via secret captain token"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    
    lang = request.args.get('lang', 'EN').upper()
    if lang not in TRANSLATIONS:
        lang = 'EN'
    
    t = get_translations(lang)
    
    stats = team.get_stats()
    men = team.registrations.filter_by(gender='male').all()
    women = team.registrations.filter_by(gender='female').all()
    
    days_left = (team.tournament.registration_deadline - datetime.now()).days
    
    registration_url = request.host_url.rstrip('/') + url_for('pcl.player_register', token=token)
    
    return render_template('pcl/captain_dashboard.html',
                         team=team,
                         stats=stats,
                         men=men,
                         women=women,
                         days_left=days_left,
                         registration_url=registration_url,
                         t=t,
                         current_lang=lang)


# ============================================================================
# PLAYER REGISTRATION ROUTES
# ============================================================================

@pcl.route('/register/<token>', methods=['GET', 'POST'])
def player_register(token):
    """Player registration form with Supabase photo upload"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    
    lang = request.args.get('lang', request.form.get('preferred_language', 'EN')).upper()
    if lang not in TRANSLATIONS:
        lang = 'EN'
    
    t = get_translations(lang)
    
    # Check if registration is still open
    if datetime.now() > team.tournament.registration_deadline:
        flash('Registration period has closed.', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    if request.method == 'POST':
        photo_url = None
        
        # Handle photo upload to Supabase
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                result = upload_photo_to_supabase(file, folder='pcl-players')
                if result['success']:
                    photo_url = result['url']
                else:
                    flash(f'Photo upload failed: {result["error"]}', 'warning')
        
        # Create registration
        registration = PCLRegistration(
            team_id=team.id,
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form['email'],
            phone=request.form.get('phone'),
            gender=request.form['gender'],
            birth_year=int(request.form['birth_year']) if request.form.get('birth_year') else None,
            is_captain=request.form.get('is_captain') == 'on',
            shirt_name=request.form['shirt_name'],
            shirt_size=request.form['shirt_size'],
            photo_filename=photo_url,
            bio=request.form.get('bio'),
            instagram=request.form.get('instagram'),
            tiktok=request.form.get('tiktok'),
            youtube=request.form.get('youtube'),
            twitter=request.form.get('twitter'),
            video_url=request.form.get('video_url'),
            dupr_rating=request.form.get('dupr_rating'),
            preferred_language=lang
        )
        
        registration.check_completeness()
        
        try:
            db.session.add(registration)
            db.session.commit()
            
            return redirect(url_for('pcl.registration_success', 
                                  registration_id=registration.id,
                                  lang=lang))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration error: {str(e)}', 'danger')
    
    return render_template('pcl/player_register.html',
                         team=team,
                         shirt_sizes=SHIRT_SIZES,
                         t=t,
                         current_lang=lang)


@pcl.route('/register/success/<int:registration_id>')
def registration_success(registration_id):
    """Registration success page"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    lang = request.args.get('lang', registration.preferred_language).upper()
    t = get_translations(lang)
    
    return render_template('pcl/registration_success.html',
                         registration=registration,
                         t=t)


@pcl.route('/register/edit/<int:registration_id>', methods=['GET', 'POST'])
def edit_registration(registration_id):
    """Edit existing registration with photo upload"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    team = registration.team
    
    lang = request.args.get('lang', request.form.get('preferred_language', registration.preferred_language)).upper()
    if lang not in TRANSLATIONS:
        lang = 'EN'
    
    t = get_translations(lang)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            registration.first_name = request.form['first_name']
            registration.last_name = request.form['last_name']
            registration.email = request.form['email']
            registration.phone = request.form.get('phone')
            registration.gender = request.form['gender']
            registration.birth_year = int(request.form['birth_year']) if request.form.get('birth_year') else None
            registration.is_captain = request.form.get('is_captain') == 'on'
            registration.shirt_name = request.form['shirt_name']
            registration.shirt_size = request.form['shirt_size']
            registration.bio = request.form.get('bio')
            registration.instagram = request.form.get('instagram')
            registration.tiktok = request.form.get('tiktok')
            registration.youtube = request.form.get('youtube')
            registration.twitter = request.form.get('twitter')
            registration.video_url = request.form.get('video_url')
            registration.dupr_rating = request.form.get('dupr_rating')
            registration.preferred_language = lang
            
            # Handle photo upload
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and allowed_file(file.filename):
                    result = upload_photo_to_supabase(file, folder='pcl-players')
                    if result['success']:
                        registration.photo_filename = result['url']
                    else:
                        flash(f'Photo upload failed: {result["error"]}', 'warning')
            
            registration.check_completeness()
            
            db.session.commit()
            flash('Registration updated successfully!', 'success')
            
            return redirect(url_for('pcl.registration_success', 
                                  registration_id=registration.id,
                                  lang=lang))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating registration: {str(e)}', 'danger')
    
    return render_template('pcl/pcl_registration_edit.html',
                         registration=registration,
                         team=team,
                         shirt_sizes=SHIRT_SIZES,
                         t=t,
                         current_lang=lang)


@pcl.route('/admin/registration/<int:registration_id>/edit', methods=['GET', 'POST'])
def admin_edit_registration(registration_id):
    """Admin edit for registration"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    if request.method == 'POST':
        try:
            registration.first_name = request.form['first_name']
            registration.last_name = request.form['last_name']
            registration.email = request.form['email']
            registration.phone = request.form.get('phone')
            registration.gender = request.form['gender']
            registration.birth_year = int(request.form['birth_year']) if request.form.get('birth_year') else None
            registration.is_captain = request.form.get('is_captain') == 'on'
            registration.shirt_name = request.form['shirt_name']
            registration.shirt_size = request.form['shirt_size']
            registration.bio = request.form.get('bio')
            registration.instagram = request.form.get('instagram')
            registration.tiktok = request.form.get('tiktok')
            registration.youtube = request.form.get('youtube')
            registration.twitter = request.form.get('twitter')
            registration.video_url = request.form.get('video_url')
            registration.dupr_rating = request.form.get('dupr_rating')
            registration.preferred_language = request.form.get('preferred_language', 'EN')
            registration.status = request.form.get('status', 'incomplete')
            
            # Handle photo upload
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and allowed_file(file.filename):
                    result = upload_photo_to_supabase(file, folder='pcl-players')
                    if result['success']:
                        registration.photo_filename = result['url']
            
            registration.check_completeness()
            
            db.session.commit()
            flash('Registration updated successfully!', 'success')
            
            return redirect(url_for('pcl.admin_team_detail', team_id=registration.team_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/pcl_registration_edit.html',
                         registration=registration,
                         team=registration.team,
                         shirt_sizes=SHIRT_SIZES,
                         is_admin=True)


@pcl.route('/admin/registration/<int:registration_id>/delete', methods=['POST'])
def delete_registration(registration_id):
    """Delete a registration"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    team_id = registration.team_id
    player_name = f"{registration.first_name} {registration.last_name}"
    
    try:
        db.session.delete(registration)
        db.session.commit()
        flash(f'Player "{player_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting player: {str(e)}', 'danger')
    
    return redirect(url_for('pcl.admin_team_detail', team_id=team_id))


# ============================================================================
# WHATSAPP PROFILE LINK ROUTES
# ============================================================================

@pcl.route('/team/<token>/send-profile-link/<int:registration_id>', methods=['POST'])
def send_player_profile_link(token, registration_id):
    """Send profile completion link to a single player"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    # Verify registration belongs to this team
    if registration.team_id != team.id:
        flash('Invalid request!', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    # Create player if doesn't exist
    if not registration.player:
        player = Player(
            first_name=registration.first_name,
            last_name=registration.last_name,
            phone=registration.phone or '',
            email=registration.email,
            preferred_language=registration.preferred_language
        )
        player.generate_update_token()
        db.session.add(player)
        registration.player = player
        db.session.commit()
    
    player = registration.player
    
    # Generate token if not exists
    if not player.update_token:
        player.generate_update_token()
        db.session.commit()
    
    # Send WhatsApp message
    result = send_profile_completion_link(player, test_mode=False)
    
    if result['status'] == 'sent':
        flash(f'Profile link sent to {player.first_name}!', 'success')
    else:
        flash(f'Error sending link: {result.get("error", "Unknown error")}', 'danger')
    
    return redirect(url_for('pcl.captain_dashboard', token=token))


@pcl.route('/team/<token>/send-all-profile-links', methods=['POST'])
def send_all_profile_links(token):
    """Send profile completion links to all team players"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    registrations = team.registrations.all()
    
    sent_count = 0
    error_count = 0
    
    for registration in registrations:
        if not registration.phone:
            error_count += 1
            continue
        
        # Create player if doesn't exist
        if not registration.player:
            player = Player(
                first_name=registration.first_name,
                last_name=registration.last_name,
                phone=registration.phone,
                email=registration.email,
                preferred_language=registration.preferred_language
            )
            player.generate_update_token()
            db.session.add(player)
            registration.player = player
        
        player = registration.player
        
        # Generate token if not exists
        if not player.update_token:
            player.generate_update_token()
        
        # Send WhatsApp
        result = send_profile_completion_link(player, test_mode=False)
        
        if result['status'] == 'sent':
            sent_count += 1
        else:
            error_count += 1
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    if sent_count > 0:
        flash(f'✅ {sent_count} profile link(s) sent!', 'success')
    if error_count > 0:
        flash(f'⚠️ {error_count} message(s) could not be sent.', 'warning')
    
    return redirect(url_for('pcl.captain_dashboard', token=token))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@pcl.route('/api/team/<token>/status')
def api_team_status(token):
    """API endpoint for team status (JSON response)"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    stats = team.get_stats()
    
    return jsonify({
        'team': f"{team.country_flag} {team.country_name} {team.age_category}",
        'stats': stats,
        'deadline': team.tournament.registration_deadline.isoformat(),
        'is_complete': stats['is_complete']
    })