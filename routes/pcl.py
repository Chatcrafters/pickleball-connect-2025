from urllib.parse import quote
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from models import db, PCLTournament, PCLTeam, PCLRegistration, Player, SHIRT_SIZES, COUNTRY_FLAGS, get_whatsapp_sponsor_block
from datetime import datetime, date
from werkzeug.utils import secure_filename
from utils.supabase_storage import upload_photo_to_supabase, get_photo_url
from utils.whatsapp import send_whatsapp_message, send_captain_invitation_template
import base64
import os
import csv
import io
import json
from urllib.parse import quote

pcl = Blueprint('pcl', __name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads/pcl'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# TRANSLATIONS (Fixed UTF-8 + Quick Add Extensions)
# ============================================================================

TRANSLATIONS = {
    'EN': {
        'page_title': 'PCL Player Registration',
        'team': 'Team',
        'personal_info': 'Personal Information',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'email': 'Email',
        'phone': 'Phone',
        'phone_help': 'With country code (+49, +34, etc.)',
        'gender': 'Gender',
        'male': 'Male',
        'female': 'Female',
        'birth_year': 'Birth Year',
        'role': 'Role',
        'player': 'Player',
        'captain': 'Captain',
        'shirt_info': 'Shirt Information',
        'shirt_size': 'Shirt Size',
        'shirt_second': 'Second Shirt (optional)',
        'shirt_third': 'Third Shirt (optional)',
        'shirt_total_price': 'Total',
        'shirt_payment_info': 'Each shirt costs 15 EUR. Shirts are ordered and printed by us according to official PCL specifications. Payment is settled through your team captain.',
        'profile': 'Profile',
        'photo': 'Profile Photo',
        'photo_help': 'Required. JPG, PNG, max 5MB. Square format recommended.',
        'upload_photo': 'Upload Photo',
        'bio': 'Short Bio',
        'bio_placeholder': 'Tell us about yourself, your pickleball journey...',
        'bio_help': 'Tell us about yourself (50-500 characters)',
        'social_media': 'Social Media',
        'optional_info': 'Optional Information',
        'video_url': 'Video URL (Highlight Reel)',
        'dupr_rating': 'DUPR Rating',
        'language': 'Preferred Language',
        'privacy_accept': 'I accept the data processing for PCL registration',
        'submit': 'Register',
        'update': 'Update Registration',
        'required': 'Required',
        'optional': 'Optional',
        'select': 'Select',
        'success_title': 'Registration Complete!',
        'success_message': 'Thank you for registering for PCL.',
        'missing_fields': 'Please complete all required fields',
        'captain_dashboard': 'Captain Dashboard',
        'team_status': 'Team Status',
        'registration_link': 'Registration Link for Players',
        'copy_link': 'Copy Link',
        'link_copied': 'Link copied!',
        'players_registered': 'Players',
        'men': 'Men',
        'women': 'Women',
        'complete': 'Complete',
        'incomplete': 'Incomplete',
        'photo_missing': 'Photo missing',
        'deadline': 'Deadline',
        'days_left': 'days left',
        'send_reminder': 'Send Reminder',
        'export_data': 'Export Team Data',
        'missing': 'Missing',
        'no_players': 'No players yet',
        'requirements': 'Requirements',
        'team_size': 'Team Size',
        'required_per_player': 'Required per Player',
        'captain_link_warning': 'This link is only for you as captain. Do not share!',
        # Quick Add specific
        'quick_add_title': 'Quick Add Player',
        'quick_add_player': 'Add Player',
        'quick_add_info': 'The player will complete their profile via WhatsApp link',
        'add_player': 'Add Player',
        'back_to_dashboard': 'Back to Dashboard',
        'send_link_now': 'Send WhatsApp link immediately',
        'send_link_help': 'Player receives a link to complete their profile',
        'phone_invalid': 'Please enter a valid phone number with country code',
        'quick_actions': 'Quick Actions',
        'send_all_links': 'Send All Links',
        'send_all_confirm': 'Send links to all incomplete players?',
        'player_added': 'Player added successfully!',
        'player_added_whatsapp': 'Player added and WhatsApp sent!',
        'whatsapp_sent': 'WhatsApp sent!',
        'whatsapp_failed': 'WhatsApp could not be sent',
        # Complete Profile specific
        'complete_profile_title': 'Complete Your Profile',
        'hello': 'Hello',
        'profile_progress': 'Profile Progress',
        'save_profile': 'Save Profile',
        'profile_saved': 'Profile saved successfully!',
        'data_protection': 'Your data is securely stored',
        'contact': 'Contact',
    },
    'DE': {
        'page_title': 'PCL Spieler-Registrierung',
        'team': 'Team',
        'personal_info': 'Persoenliche Informationen',
        'first_name': 'Vorname',
        'last_name': 'Nachname',
        'email': 'E-Mail',
        'phone': 'Telefon',
        'phone_help': 'Mit Laendervorwahl (+49, +34, etc.)',
        'gender': 'Geschlecht',
        'male': 'Maennlich',
        'female': 'Weiblich',
        'birth_year': 'Geburtsjahr',
        'role': 'Rolle',
        'player': 'Spieler',
        'captain': 'Kapitaen',
        'shirt_info': 'Shirt-Informationen',
        'shirt_size': 'Shirt-GrÃ¶ÃŸe',
        'shirt_second': 'Zweites Shirt (optional)',
        'shirt_third': 'Drittes Shirt (optional)',
        'shirt_total_price': 'Gesamt',
        'shirt_payment_info': 'Jedes Shirt kostet 15 EUR. Die Shirts werden von uns gemÃ¤ÃŸ den offiziellen PCL-Vorgaben bestellt und bedruckt. Die Abrechnung erfolgt Ã¼ber den TeamkapitÃ¤n.',
        'profile': 'Profil',
        'photo': 'Profilbild',
        'photo_help': 'Pflichtfeld. JPG, PNG, max 5MB. Quadratisches Format empfohlen.',
        'upload_photo': 'Foto hochladen',
        'bio': 'Kurze Bio',
        'bio_placeholder': 'Erzaehl uns von dir und deiner Pickleball-Reise...',
        'bio_help': 'Erzaehl uns von dir (50-500 Zeichen)',
        'social_media': 'Social Media',
        'optional_info': 'Optionale Informationen',
        'video_url': 'Video-URL (Highlight-Video)',
        'dupr_rating': 'DUPR Rating',
        'language': 'Bevorzugte Sprache',
        'privacy_accept': 'Ich stimme der Datenverarbeitung fuer die PCL-Registrierung zu',
        'submit': 'Registrieren',
        'update': 'Registrierung aktualisieren',
        'required': 'Pflicht',
        'optional': 'Optional',
        'select': 'Auswaehlen',
        'success_title': 'Registrierung erfolgreich!',
        'success_message': 'Danke fuer deine Registrierung zur PCL.',
        'missing_fields': 'Bitte fuelle alle Pflichtfelder aus',
        'captain_dashboard': 'Kapitaen Dashboard',
        'team_status': 'Team-Status',
        'registration_link': 'Registrierungslink fuer Spieler',
        'copy_link': 'Link kopieren',
        'link_copied': 'Link kopiert!',
        'players_registered': 'Spieler',
        'men': 'Maenner',
        'women': 'Frauen',
        'complete': 'Vollstaendig',
        'incomplete': 'Unvollstaendig',
        'photo_missing': 'Foto fehlt',
        'deadline': 'Deadline',
        'days_left': 'Tage uebrig',
        'send_reminder': 'Erinnerung senden',
        'export_data': 'Team-Daten exportieren',
        'missing': 'Fehlt',
        'no_players': 'Noch keine Spieler',
        'requirements': 'Anforderungen',
        'team_size': 'Teamgroesse',
        'required_per_player': 'Pro Spieler erforderlich',
        'captain_link_warning': 'Dieser Link ist nur fuer dich als Kapitaen. Nicht teilen!',
        # Quick Add specific
        'quick_add_title': 'Spieler schnell hinzufuegen',
        'quick_add_player': 'Spieler hinzufuegen',
        'quick_add_info': 'Der Spieler vervollstaendigt sein Profil ueber den WhatsApp-Link',
        'add_player': 'Spieler hinzufuegen',
        'back_to_dashboard': 'Zurueck zum Dashboard',
        'send_link_now': 'WhatsApp-Link sofort senden',
        'send_link_help': 'Spieler erhaelt Link zur Profil-Vervollstaendigung',
        'phone_invalid': 'Bitte gueltige Telefonnummer mit Laendervorwahl eingeben',
        'quick_actions': 'Schnellaktionen',
        'send_all_links': 'Alle Links senden',
        'send_all_confirm': 'Links an alle unvollstaendigen Spieler senden?',
        'player_added': 'Spieler erfolgreich hinzugefuegt!',
        'player_added_whatsapp': 'Spieler hinzugefuegt und WhatsApp gesendet!',
        'whatsapp_sent': 'WhatsApp gesendet!',
        'whatsapp_failed': 'WhatsApp konnte nicht gesendet werden',
        # Complete Profile specific
        'complete_profile_title': 'Profil vervollstaendigen',
        'hello': 'Hallo',
        'profile_progress': 'Profil-Fortschritt',
        'save_profile': 'Profil speichern',
        'profile_saved': 'Profil erfolgreich gespeichert!',
        'data_protection': 'Deine Daten werden sicher gespeichert',
        'contact': 'Kontakt',
    },
    'ES': {
        'page_title': 'Registro de Jugadores PCL',
        'team': 'Equipo',
        'personal_info': 'InformaciÃƒÂ³n Personal',
        'first_name': 'Nombre',
        'last_name': 'Apellido',
        'email': 'Correo electrÃƒÂ³nico',
        'phone': 'Telefono',
        'phone_help': 'Con cÃƒÂ³digo de pais (+34, +49, etc.)',
        'gender': 'Genero',
        'male': 'Masculino',
        'female': 'Femenino',
        'birth_year': 'AÃƒÂ±o de nacimiento',
        'role': 'Rol',
        'player': 'Jugador',
        'captain': 'CapitÃƒÂ¡n',
        'shirt_info': 'InformaciÃ³n de la Camiseta',
        'shirt_size': 'Talla de camiseta',
        'shirt_second': 'Segunda camiseta (opcional)',
        'shirt_third': 'Tercera camiseta (opcional)',
        'shirt_total_price': 'Total',
        'shirt_payment_info': 'Cada camiseta cuesta 15 EUR. Las camisetas son pedidas e impresas por nosotros segÃºn las especificaciones oficiales de la PCL. El pago se gestiona a travÃ©s del capitÃ¡n del equipo.',
        'profile': 'Perfil',
        'photo': 'Foto de perfil',
        'photo_help': 'Obligatorio. JPG, PNG, mÃƒÂ¡x 5MB. Formato cuadrado recomendado.',
        'upload_photo': 'Subir foto',
        'bio': 'Biografia breve',
        'bio_placeholder': 'Cuentanos sobre ti y tu viaje en pickleball...',
        'bio_help': 'Cuentanos sobre ti (50-500 caracteres)',
        'social_media': 'Redes Sociales',
        'optional_info': 'InformaciÃƒÂ³n Opcional',
        'video_url': 'URL del Video (Highlights)',
        'dupr_rating': 'Rating DUPR',
        'language': 'Idioma preferido',
        'privacy_accept': 'Acepto el procesamiento de datos para el registro PCL',
        'submit': 'Registrarse',
        'update': 'Actualizar registro',
        'required': 'Obligatorio',
        'optional': 'Opcional',
        'select': 'Seleccionar',
        'success_title': 'Registro completado!',
        'success_message': 'Gracias por registrarte en PCL.',
        'missing_fields': 'Por favor completa todos los campos obligatorios',
        'captain_dashboard': 'Panel del CapitÃƒÂ¡n',
        'team_status': 'Estado del Equipo',
        'registration_link': 'Enlace de registro para jugadores',
        'copy_link': 'Copiar enlace',
        'link_copied': 'Enlace copiado!',
        'players_registered': 'Jugadores',
        'men': 'Hombres',
        'women': 'Mujeres',
        'complete': 'Completo',
        'incomplete': 'Incompleto',
        'photo_missing': 'Falta foto',
        'deadline': 'Fecha limite',
        'days_left': 'dias restantes',
        'send_reminder': 'Enviar recordatorio',
        'export_data': 'Exportar datos del equipo',
        'missing': 'Falta',
        'no_players': 'Sin jugadores todavia',
        'requirements': 'Requisitos',
        'team_size': 'TamaÃƒÂ±o del equipo',
        'required_per_player': 'Requerido por jugador',
        'captain_link_warning': 'Este enlace es solo para ti como capitÃƒÂ¡n. No compartir!',
        # Quick Add specific
        'quick_add_title': 'AÃƒÂ±adir jugador rÃƒÂ¡pido',
        'quick_add_player': 'AÃƒÂ±adir jugador',
        'quick_add_info': 'El jugador completarÃƒÂ¡ su perfil a traves del enlace de WhatsApp',
        'add_player': 'AÃƒÂ±adir jugador',
        'back_to_dashboard': 'Volver al panel',
        'send_link_now': 'Enviar enlace WhatsApp ahora',
        'send_link_help': 'El jugador recibirÃƒÂ¡ un enlace para completar su perfil',
        'phone_invalid': 'Por favor ingresa un nÃƒÂºmero vÃƒÂ¡lido con cÃƒÂ³digo de pais',
        'quick_actions': 'Acciones rÃƒÂ¡pidas',
        'send_all_links': 'Enviar todos los enlaces',
        'send_all_confirm': 'Ã‚Â¿Enviar enlaces a todos los jugadores incompletos?',
        'player_added': 'Jugador aÃƒÂ±adido exitosamente!',
        'player_added_whatsapp': 'Jugador aÃƒÂ±adido y WhatsApp enviado!',
        'whatsapp_sent': 'WhatsApp enviado!',
        'whatsapp_failed': 'No se pudo enviar WhatsApp',
        # Complete Profile specific
        'complete_profile_title': 'Completa tu perfil',
        'hello': 'Hola',
        'profile_progress': 'Progreso del perfil',
        'save_profile': 'Guardar perfil',
        'profile_saved': 'Perfil guardado exitosamente!',
        'data_protection': 'Tus datos estÃƒÂ¡n almacenados de forma segura',
        'contact': 'Contacto',
    },
    'FR': {
        'page_title': 'Inscription Joueur PCL',
        'team': 'Ãƒâ€°quipe',
        'personal_info': 'Informations Personnelles',
        'first_name': 'Prenom',
        'last_name': 'Nom',
        'email': 'E-mail',
        'phone': 'Telephone',
        'phone_help': 'Avec indicatif pays (+33, +49, etc.)',
        'gender': 'Genre',
        'male': 'Homme',
        'female': 'Femme',
        'birth_year': 'Annee de naissance',
        'role': 'RÃƒÂ´le',
        'player': 'Joueur',
        'captain': 'Capitaine',
        'shirt_info': 'Informations Maillot',
        'shirt_size': 'Taille du maillot',
        'shirt_second': 'Second maillot (optionnel)',
        'shirt_third': 'TroisiÃ¨me maillot (optionnel)',
        'shirt_total_price': 'Total',
        'shirt_payment_info': 'Chaque maillot coÃ»te 15 EUR. Les maillots sont commandÃ©s et imprimÃ©s par nous selon les spÃ©cifications officielles de la PCL. Le paiement est gÃ©rÃ© par le capitaine de l\'Ã©quipe.',
        'profile': 'Profil',
        'photo': 'Photo de profil',
        'photo_help': 'Obligatoire. JPG, PNG, max 5Mo. Format carre recommande.',
        'upload_photo': 'Telecharger photo',
        'bio': 'Courte bio',
        'bio_placeholder': 'Parlez-nous de vous et de votre parcours pickleball...',
        'bio_help': 'Parlez-nous de vous (50-500 caractÃƒÂ¨res)',
        'social_media': 'Reseaux Sociaux',
        'optional_info': 'Informations Optionnelles',
        'video_url': 'URL Video (Highlights)',
        'dupr_rating': 'Rating DUPR',
        'language': 'Langue preferee',
        'privacy_accept': "J'accepte le traitement des donnees pour l'inscription PCL",
        'submit': "S'inscrire",
        'update': "Mettre a jour l'inscription",
        'required': 'Obligatoire',
        'optional': 'Optionnel',
        'select': 'Selectionner',
        'success_title': 'Inscription reussie!',
        'success_message': 'Merci pour votre inscription a PCL.',
        'missing_fields': 'Veuillez remplir tous les champs obligatoires',
        'captain_dashboard': 'Tableau de bord Capitaine',
        'team_status': "Statut de l'equipe",
        'registration_link': "Lien d'inscription pour les joueurs",
        'copy_link': 'Copier le lien',
        'link_copied': 'Lien copie!',
        'players_registered': 'Joueurs',
        'men': 'Hommes',
        'women': 'Femmes',
        'complete': 'Complet',
        'incomplete': 'Incomplet',
        'photo_missing': 'Photo manquante',
        'deadline': 'Date limite',
        'days_left': 'jours restants',
        'send_reminder': 'Envoyer un rappel',
        'export_data': "Exporter les donnees de l'equipe",
        'missing': 'Manquant',
        'no_players': 'Pas encore de joueurs',
        'requirements': 'Exigences',
        'team_size': "Taille de l'equipe",
        'required_per_player': 'Requis par joueur',
        'captain_link_warning': 'Ce lien est uniquement pour vous en tant que capitaine. Ne pas partager!',
        # Quick Add specific
        'quick_add_title': 'Ajouter un joueur rapidement',
        'quick_add_player': 'Ajouter un joueur',
        'quick_add_info': 'Le joueur completera son profil via le lien WhatsApp',
        'add_player': 'Ajouter joueur',
        'back_to_dashboard': 'Retour au tableau de bord',
        'send_link_now': 'Envoyer le lien WhatsApp maintenant',
        'send_link_help': 'Le joueur recevra un lien pour completer son profil',
        'phone_invalid': 'Veuillez entrer un numero valide avec indicatif pays',
        'quick_actions': 'Actions rapides',
        'send_all_links': 'Envoyer tous les liens',
        'send_all_confirm': 'Envoyer les liens a tous les joueurs incomplets?',
        'player_added': 'Joueur ajoute avec succÃƒÂ¨s!',
        'player_added_whatsapp': 'Joueur ajoute et WhatsApp envoye!',
        'whatsapp_sent': 'WhatsApp envoye!',
        'whatsapp_failed': "Impossible d'envoyer WhatsApp",
        # Complete Profile specific
        'complete_profile_title': 'Completez votre profil',
        'hello': 'Bonjour',
        'profile_progress': 'Progression du profil',
        'save_profile': 'Enregistrer le profil',
        'profile_saved': 'Profil enregistre avec succÃƒÂ¨s!',
        'data_protection': 'Vos donnees sont stockees en toute securite',
        'contact': 'Contact',
    }
}

def get_translations(lang='EN'):
    """Get translations for a language, fallback to EN"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['EN'])


# ============================================================================
# WHATSAPP MESSAGE TEMPLATES FOR PROFILE COMPLETION
# ============================================================================

def get_profile_completion_message(registration, profile_url, lang='EN'):
    """Get WhatsApp message for profile completion in the specified language"""
    
    team = registration.team
    tournament = team.tournament
    
    messages = {
        'EN': f"""Ã°Å¸Ââ€œ PCL {tournament.name}

Hi {registration.first_name}! Ã°Å¸â€˜â€¹

You've been added to Team {team.country_flag} {team.country_name} ({team.age_category}).

Please complete your profile:
Ã°Å¸â€˜â€° {profile_url}

Required:
Ã¢Å“â€œ Profile photo
Ã¢Å“â€œ Shirt size
Ã¢Å“â€œ Short bio

Ã¢ÂÂ° Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Questions? Contact your team captain.

See you on the court! 
WPC Series Europe""",

        'DE': f"""Ã°Å¸Ââ€œ PCL {tournament.name}

Hallo {registration.first_name}! Ã°Å¸â€˜â€¹

Du wurdest zu Team {team.country_flag} {team.country_name} ({team.age_category}) hinzugefuegt.

Bitte vervollstaendige dein Profil:
Ã°Å¸â€˜â€° {profile_url}

Erforderlich:
Ã¢Å“â€œ Profilbild
Ã¢Å“â€œ Shirt-Name & Groesse
Ã¢Å“â€œ Kurze Bio

Ã¢ÂÂ° Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Fragen? Kontaktiere deinen Team-Kapitaen.

Bis bald auf dem Court! 
WPC Series Europe""",

        'ES': f"""Ã°Å¸Ââ€œ PCL {tournament.name}

Hola {registration.first_name}! Ã°Å¸â€˜â€¹

Has sido aÃƒÂ±adido al equipo {team.country_flag} {team.country_name} ({team.age_category}).

Por favor completa tu perfil:
Ã°Å¸â€˜â€° {profile_url}

Requerido:
Ã¢Å“â€œ Foto de perfil
Ã¢Å“â€œ Talla de camiseta
Ã¢Å“â€œ Breve biografia

Ã¢ÂÂ° Fecha limite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Ã‚Â¿Preguntas? Contacta a tu capitÃƒÂ¡n.

Nos vemos en la cancha! 
WPC Series Europe""",

        'FR': f"""Ã°Å¸Ââ€œ PCL {tournament.name}

Bonjour {registration.first_name}! Ã°Å¸â€˜â€¹

Vous avez ete ajoute a l'equipe {team.country_flag} {team.country_name} ({team.age_category}).

Veuillez completer votre profil:
Ã°Å¸â€˜â€° {profile_url}

Requis:
Ã¢Å“â€œ Photo de profil
Ã¢Å“â€œ Taille du maillot
Ã¢Å“â€œ Courte bio

Ã¢ÂÂ° Date limite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Questions? Contactez votre capitaine.

Ãƒâ‚¬ bientÃƒÂ´t sur le court! 
WPC Series Europe"""
    }
    
    return messages.get(lang, messages['EN'])


# ============================================================================
# ADMIN ROUTES
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
        tournament = PCLTournament(
            name=request.form['name'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
            location=request.form['location'],
            description=request.form.get('description'),
            registration_deadline=datetime.strptime(request.form['registration_deadline'], '%Y-%m-%dT%H:%M')
        )
        
        try:
            db.session.add(tournament)
            db.session.commit()
            flash(f'Tournament "{tournament.name}" created!', 'success')
            return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/admin_tournament_form.html', tournament=None)


@pcl.route('/admin/tournament/<int:tournament_id>')
def admin_tournament_detail(tournament_id):
    """Admin view of a tournament with all teams"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    teams_19 = tournament.teams.filter_by(age_category='+19').order_by(PCLTeam.country_name).all()
    teams_50 = tournament.teams.filter_by(age_category='+50').order_by(PCLTeam.country_name).all()
    
    return render_template('pcl/admin_tournament_detail.html', 
                         tournament=tournament,
                         teams_19=teams_19,
                         teams_50=teams_50,
                         now=datetime.utcnow())


@pcl.route('/media/<int:tournament_id>')
def media_page(tournament_id):
    """Public media page with all player photos and info for social media"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    teams_data = []
    total_players = 0
    players_with_photos = 0
    
    for team in tournament.teams.order_by(PCLTeam.country_name).all():
        players = team.registrations.all()
        total_players += len(players)
        players_with_photos += len([p for p in players if p.photo_filename])
        
        if players:
            teams_data.append({
                'team': team,
                'players': players
            })
    
    return render_template('pcl/media_page.html',
                         tournament=tournament,
                         teams_data=teams_data,
                         total_players=total_players,
                         players_with_photos=players_with_photos)


@pcl.route('/admin/tournament/<int:tournament_id>/add-team', methods=['GET', 'POST'])
def add_team(tournament_id):
    """Add a team to a tournament"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        country_code = request.form['country_code'].upper()
        
        team = PCLTeam(
            tournament_id=tournament.id,
            country_code=country_code,
            country_name=request.form['country_name'],
            country_flag=COUNTRY_FLAGS.get(country_code, 'ðŸ³ï¸'),
            age_category=request.form['age_category'],
            min_men=int(request.form.get('min_men', 2)),
            max_men=int(request.form.get('max_men', 4)),
            min_women=int(request.form.get('min_women', 2)),
            max_women=int(request.form.get('max_women', 4)),
            captain_token=PCLTeam.generate_token()
        )
        
        try:
            db.session.add(team)
            db.session.commit()
            flash(f'Team {team.country_flag} {team.country_name} {team.age_category} added!', 'success')
            return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/admin_add_team.html', 
                         tournament=tournament,
                         country_flags=COUNTRY_FLAGS)


@pcl.route('/admin/team/<int:team_id>')
def admin_team_detail(team_id):
    """Admin view of a specific team with captain management"""
    team = PCLTeam.query.get_or_404(team_id)
    
    men = team.registrations.filter_by(gender='male').all()
    women = team.registrations.filter_by(gender='female').all()
    captains = team.registrations.filter_by(is_captain=True).all()
    stats = team.get_stats()
    
    return render_template('pcl/admin_team_detail.html', 
                         team=team,
                         men=men,
                         women=women,
                         captains=captains,
                         stats=stats)


@pcl.route('/admin/team/<int:team_id>/add-captain', methods=['POST'])
def add_captain(team_id):
    """Admin adds a captain to a team"""
    team = PCLTeam.query.get_or_404(team_id)
    
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    gender = request.form.get('gender', 'male')
    language = request.form.get('language', 'EN')
    is_playing = request.form.get('is_playing') == 'on'
    send_whatsapp = request.form.get('send_whatsapp') == 'on'
    
    if not first_name or not last_name or not phone:
        flash('First name, last name and phone are required!', 'danger')
        return redirect(url_for('pcl.admin_team_detail', team_id=team_id))
    
    # Normalize phone
    phone = phone.replace(' ', '').replace('-', '')
    if not phone.startswith('+'):
        phone = '+' + phone
    
    captain = PCLRegistration(
        team_id=team.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        gender=gender,
        is_captain=True,
        is_playing=is_playing,
        preferred_language=language,
        status='incomplete'
    )
    
    captain.generate_profile_token()
    
    try:
        db.session.add(captain)
        db.session.commit()
        
        if is_playing:
            flash(f'Captain {first_name} {last_name} added as player!', 'success')
        else:
            flash(f'Captain {first_name} {last_name} added (not playing)!', 'success')
        
        # Send WhatsApp: (1) captain invitation template, (2) player registration link to forward
        if send_whatsapp and phone:
            # MESSAGE 1: Captain invitation via approved Content Template
            result1 = send_captain_invitation_template(
                team=team,
                captain_name=first_name,
                captain_phone=phone,
                captain_token=team.captain_token,
                language=language
            )

            if result1.get('status') == 'sent':
                captain.whatsapp_sent_at = datetime.now()
                db.session.commit()
                flash(f'Captain invitation sent to {first_name}!', 'success')
            else:
                flash(f'Captain invitation failed: {result1.get("error", "Unknown")}', 'warning')

            # MESSAGE 2: Registration link for captain to forward to team group
            team_name = f"{team.country_flag} {team.country_name} {team.age_category}"
            registration_url = request.host_url.rstrip('/') + url_for('pcl.player_register', token=team.captain_token) + '?lang=' + language
            player_link_messages = {
                'EN': f"Hi {first_name}, here is the registration link for {team_name} players. Please forward this to your team WhatsApp group:\n\n{registration_url}\n\nPlayers will be asked to complete their profile (photo, bio, shirt size).",
                'DE': f"Hallo {first_name}, hier ist der Registrierungslink fuer die Spieler von {team_name}. Bitte leite ihn an die Team-WhatsApp-Gruppe weiter:\n\n{registration_url}\n\nDie Spieler werden gebeten, ihr Profil zu vervollstaendigen (Foto, Bio, Shirtgroesse).",
                'ES': f"Hola {first_name}, aqui esta el enlace de registro para los jugadores de {team_name}. Por favor reenvialo al grupo WhatsApp:\n\n{registration_url}\n\nLos jugadores deben completar su perfil (foto, bio, talla).",
                'FR': f"Bonjour {first_name}, voici le lien d inscription pour les joueurs de {team_name}. Transmettez-le au groupe WhatsApp:\n\n{registration_url}\n\nLes joueurs doivent completer leur profil (photo, bio, taille).",
            }
            player_link_message = player_link_messages.get(language.upper(), player_link_messages['EN'])
            result2 = send_whatsapp_message(phone, player_link_message)
            if result2.get('status') != 'sent':
                flash(f'Player-link message failed: {result2.get("error", "Unknown")}', 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('pcl.admin_team_detail', team_id=team_id))


@pcl.route('/admin/team/<int:team_id>/export')
def export_team_data(team_id):
    """Export team data as CSV"""
    team = PCLTeam.query.get_or_404(team_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Phone', 'Gender', 'Birth Year',
        'Captain', 'Shirt Size', 'Shirt Size 2', 'Shirt Size 3', 'Bio',
        'Instagram', 'TikTok', 'YouTube', 'Twitter', 'DUPR', 'Status', 'Photo URL'
    ])

    for reg in team.registrations.all():
        writer.writerow([
            reg.first_name, reg.last_name, reg.email or '', reg.phone or '', reg.gender, reg.birth_year or '',
            'Yes' if reg.is_captain else 'No', reg.shirt_size or '', reg.shirt_size_2 or '', reg.shirt_size_3 or '', reg.bio or '',
            reg.instagram or '', reg.tiktok or '', reg.youtube or '', reg.twitter or '',
            reg.dupr_rating or '', reg.status, reg.photo_filename or ''
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
    """Export shirt list as Excel with order summary"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    # Collect all registrations
    all_regs = []
    incomplete = []
    
    for team in tournament.teams.all():
        for reg in team.registrations.all():
            base = {
                'team': f"{team.country_flag} {team.country_name}",
                'category': team.age_category,
                'player': f"{reg.first_name} {reg.last_name}"
            }
            size1 = (reg.shirt_size or '').strip()
            size2 = (reg.shirt_size_2 or '').strip()
            size3 = (reg.shirt_size_3 or '').strip()

            if size1:
                all_regs.append({**base, 'size': size1, 'shirt_no': 1})
            else:
                incomplete.append({**base, 'size': '', 'shirt_no': 1})

            if size2:
                all_regs.append({**base, 'size': size2, 'shirt_no': 2})

            if size3:
                all_regs.append({**base, 'size': size3, 'shirt_no': 3})
    
    # Create workbook
    wb = Workbook()
    
    # Styles
    header_fill = PatternFill('solid', fgColor='1F4E79')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    warning_fill = PatternFill('solid', fgColor='FFC7CE')
    warning_font = Font(bold=True, color='9C0006')
    yellow_fill = PatternFill('solid', fgColor='FFFFCC')
    size_header_fill = PatternFill('solid', fgColor='D9E1F2')
    border = Side(style='thin', color='000000')
    thin_border = Border(left=border, right=border, top=border, bottom=border)
    
    # === SHEET 1: BestellÃ¼bersicht ===
    ws1 = wb.active
    ws1.title = "BestellÃ¼bersicht"
    
    # Title
    ws1['A1'] = f'PCL SHIRT BESTELLUNG - {tournament.name}'
    ws1['A1'].font = Font(bold=True, size=16)
    ws1.merge_cells('A1:D1')
    
    ws1['A3'] = 'ZUSAMMENFASSUNG NACH GRÃ–SSEN'
    ws1['A3'].font = Font(bold=True, size=14)
    
    # Size counts
    size_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    size_counts = {}
    for reg in all_regs:
        size = reg['size'].upper()
        size_counts[size] = size_counts.get(size, 0) + 1
    
    ws1['A4'] = 'GrÃ¶ÃŸe'
    ws1['B4'] = 'Anzahl'
    ws1['A4'].font = header_font
    ws1['B4'].font = header_font
    ws1['A4'].fill = header_fill
    ws1['B4'].fill = header_fill
    ws1['A4'].border = thin_border
    ws1['B4'].border = thin_border
    
    row = 5
    for size in size_order:
        count = size_counts.get(size, 0)
        if count > 0:
            ws1[f'A{row}'] = size
            ws1[f'B{row}'] = count
            ws1[f'A{row}'].border = thin_border
            ws1[f'B{row}'].border = thin_border
            ws1[f'B{row}'].alignment = Alignment(horizontal='center')
            row += 1
    
    # Total
    ws1[f'A{row}'] = 'GESAMT'
    ws1[f'B{row}'] = len(all_regs)
    ws1[f'A{row}'].font = Font(bold=True)
    ws1[f'B{row}'].font = Font(bold=True)
    ws1[f'A{row}'].border = thin_border
    ws1[f'B{row}'].border = thin_border
    
    # Incomplete section
    if incomplete:
        row += 3
        ws1[f'A{row}'] = f'âš ï¸ FEHLENDE DATEN ({len(incomplete)} Spieler)'
        ws1[f'A{row}'].font = warning_font
        ws1[f'A{row}'].fill = warning_fill
        ws1.merge_cells(f'A{row}:D{row}')
        
        row += 1
        for col, header in enumerate(['Spieler', 'Team', 'Kategorie', 'Fehlt'], 1):
            cell = ws1.cell(row=row, column=col, value=header)
            cell.font = Font(bold=True)
            cell.border = thin_border
        
        row += 1
        for inc in incomplete:
            missing = []
            if not inc['size']:
                missing.append('GrÃ¶ÃŸe')

            ws1.cell(row=row, column=1, value=inc['player']).border = thin_border
            ws1.cell(row=row, column=2, value=inc['team']).border = thin_border
            ws1.cell(row=row, column=3, value=inc['category']).border = thin_border
            ws1.cell(row=row, column=4, value=', '.join(missing)).border = thin_border
            for col in range(1, 5):
                ws1.cell(row=row, column=col).fill = yellow_fill
            row += 1
    
    ws1.column_dimensions['A'].width = 30
    ws1.column_dimensions['B'].width = 15
    ws1.column_dimensions['C'].width = 12
    ws1.column_dimensions['D'].width = 20
    
    # === SHEET 2: Nach GrÃ¶ÃŸe sortiert ===
    ws2 = wb.create_sheet("Nach GrÃ¶ÃŸe")
    row = 1
    
    for size in size_order:
        size_regs = [r for r in all_regs if r['size'].upper() == size]
        if not size_regs:
            continue
        
        ws2[f'A{row}'] = f'GRÃ–SSE {size} ({len(size_regs)} StÃ¼ck)'
        ws2[f'A{row}'].font = Font(bold=True, size=12)
        ws2[f'A{row}'].fill = size_header_fill
        ws2.merge_cells(f'A{row}:D{row}')
        row += 1
        
        for col, header in enumerate(['Spieler', 'Shirt #', 'Team', 'Kat.'], 1):
            cell = ws2.cell(row=row, column=col, value=header)
            cell.font = Font(bold=True)
            cell.border = thin_border
        row += 1

        for reg in sorted(size_regs, key=lambda x: (x['team'], x['player'], x['shirt_no'])):
            ws2.cell(row=row, column=1, value=reg['player']).border = thin_border
            ws2.cell(row=row, column=2, value=reg['shirt_no']).border = thin_border
            ws2.cell(row=row, column=3, value=reg['team']).border = thin_border
            ws2.cell(row=row, column=4, value=reg['category']).border = thin_border
            row += 1
        row += 1
    
    ws2.column_dimensions['A'].width = 25
    ws2.column_dimensions['B'].width = 30
    ws2.column_dimensions['C'].width = 20
    ws2.column_dimensions['D'].width = 8
    
    # === SHEET 3: Nach Team sortiert ===
    ws3 = wb.create_sheet("Nach Team")
    
    headers = ['Team', 'Kategorie', 'Spieler', 'GrÃ¶ÃŸe', 'Shirt #']
    for col, h in enumerate(headers, 1):
        cell = ws3.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    sorted_regs = sorted(all_regs, key=lambda x: (x['team'], x['category'], x['player'], x['shirt_no']))
    for r, reg in enumerate(sorted_regs, 2):
        ws3.cell(row=r, column=1, value=reg['team']).border = thin_border
        ws3.cell(row=r, column=2, value=reg['category']).border = thin_border
        ws3.cell(row=r, column=3, value=reg['player']).border = thin_border
        ws3.cell(row=r, column=4, value=reg['size']).border = thin_border
        ws3.cell(row=r, column=5, value=reg['shirt_no']).border = thin_border
    
    ws3.column_dimensions['A'].width = 20
    ws3.column_dimensions['B'].width = 10
    ws3.column_dimensions['C'].width = 25
    ws3.column_dimensions['D'].width = 10
    ws3.column_dimensions['E'].width = 30
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'pcl_{tournament.id}_shirt_bestellung.xlsx'
    )



# ============================================================================
# CAPTAIN ROUTES (Secret Link)
# ============================================================================
@pcl.route('/team/<token>')
def captain_dashboard(token):
    """Captain dashboard - accessed via secret link, shows all teams for this captain"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    
    lang = request.args.get('lang', 'EN').upper()
    if lang not in TRANSLATIONS:
        lang = 'EN'
    
    t = get_translations(lang)
    
    # Find captain in this team (to get phone number)
    current_captain = team.registrations.filter_by(is_captain=True).first()
    
    # Find ALL teams where this person is captain (by phone number)
    other_teams = []
    if current_captain and current_captain.phone:
        # Find all captain registrations with same phone
        all_captain_regs = PCLRegistration.query.filter_by(
            phone=current_captain.phone,
            is_captain=True
        ).all()
        
        # Get unique teams (excluding current)
        for reg in all_captain_regs:
            if reg.team_id != team.id:
                other_team = PCLTeam.query.get(reg.team_id)
                if other_team and other_team not in other_teams:
                    other_teams.append(other_team)
    
    stats = team.get_stats()
    men = team.registrations.filter_by(gender='male').all()
    women = team.registrations.filter_by(gender='female').all()
    
    days_left = (team.tournament.registration_deadline - datetime.now()).days
    
    registration_url = request.host_url.rstrip('/') + url_for('pcl.player_register', token=token)
    quick_add_url = request.host_url.rstrip('/') + url_for('pcl.quick_add_player', token=token)
    
    # Share messages for WhatsApp
    share_messages = {
        'EN': f"""Hello Team!

Please complete your PCL profile for {team.country_name} {team.age_category} at {team.tournament.name}:

{registration_url}?lang=EN

Required:
- Profile photo
- Short bio
- Shirt size

Thank you!""",
        'DE': f"""Hallo Team!

Bitte vervollstaendigt euer PCL Profil fuer {team.country_name} {team.age_category} bei {team.tournament.name}:

{registration_url}?lang=DE

Benoetigt werden:
- Profilbild
- Kurze Bio
- Shirtgroesse

Danke!""",
        'ES': f"""Hola Equipo!

Por favor completa tu perfil PCL para {team.country_name} {team.age_category} en {team.tournament.name}:

{registration_url}?lang=ES

Requerido:
- Foto de perfil
- Biografia breve
- Talla de camiseta

Gracias!""",
        'FR': f"""Bonjour l'equipe!

Veuillez completer votre profil PCL pour {team.country_name} {team.age_category} a {team.tournament.name}:

{registration_url}?lang=FR

Requis:
- Photo de profil
- Courte bio
- Taille du maillot

Merci!"""
    }
    
    share_message = share_messages.get(lang, share_messages['EN'])
    share_message_encoded = quote(share_message)
    
    # Individual player message
    player_messages = {
        'EN': f"Hi! Please complete your PCL profile for {team.country_name} {team.age_category}: {registration_url}?lang=EN",
        'DE': f"Hallo! Bitte vervollstaendige dein PCL Profil fuer {team.country_name} {team.age_category}: {registration_url}?lang=DE",
        'ES': f"Hola! Por favor completa tu perfil PCL para {team.country_name} {team.age_category}: {registration_url}?lang=ES",
        'FR': f"Salut! Veuillez completer votre profil PCL pour {team.country_name} {team.age_category}: {registration_url}?lang=FR"
    }
    player_message_encoded = quote(player_messages.get(lang, player_messages['EN']))
    
    return render_template('pcl/captain_dashboard.html',
                         team=team,
                         other_teams=other_teams,
                         stats=stats,
                         men=men,
                         women=women,
                         days_left=days_left,
                         registration_url=registration_url,
                         quick_add_url=quick_add_url,
                         share_message=share_message,
                         share_message_encoded=share_message_encoded,
                         player_message_encoded=player_message_encoded,
                         t=t,
                         current_lang=lang)


# ============================================================================
# QUICK ADD PLAYER (NEW!)
# ============================================================================

@pcl.route('/team/<token>/quick-add', methods=['GET', 'POST'])
def quick_add_player(token):
    """Quick add player - minimal form for captains"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    
    lang = request.args.get('lang', request.form.get('preferred_language', 'EN')).upper()
    if lang not in TRANSLATIONS:
        lang = 'EN'
    
    t = get_translations(lang)
    stats = team.get_stats()
    
    # Check deadline
    if datetime.now() > team.tournament.registration_deadline:
        flash('Registration is closed.', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender')
        preferred_language = request.form.get('preferred_language', lang)
        send_whatsapp = request.form.get('send_whatsapp') == 'on'
        
        # Validate
        if not first_name or not last_name or not phone or not gender:
            flash(t['missing_fields'], 'danger')
            return redirect(url_for('pcl.quick_add_player', token=token, lang=lang))
        
        # Normalize phone number
        phone = phone.replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Create registration with minimal data
        registration = PCLRegistration(
            team_id=team.id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            gender=gender,
            preferred_language=preferred_language,
            status='incomplete'
        )
        
        # Generate profile token
        registration.generate_profile_token()
        
        try:
            db.session.add(registration)
            db.session.commit()
            
            # Send WhatsApp if requested
            if send_whatsapp and phone:
                profile_url = request.host_url.rstrip('/') + url_for('pcl.complete_profile', profile_token=registration.profile_token)
                message = get_profile_completion_message(registration, profile_url, preferred_language)
                sponsor_block = get_whatsapp_sponsor_block(pcl_tournament_id=team.tournament_id, language=preferred_language)
                message += sponsor_block

                result = send_whatsapp_message(phone, message, test_mode=False)
                
                if result.get('status') in ['sent', 'queued']:
                    flash(t['player_added_whatsapp'], 'success')
                else:
                    flash(f"{t['player_added']} ({t['whatsapp_failed']})", 'warning')
            else:
                flash(t['player_added'], 'success')
            
            return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/quick_add_player.html',
                         team=team,
                         stats=stats,
                         t=t,
                         current_lang=lang)


# ============================================================================
# COMPLETE PROFILE (PUBLIC - via profile_token)
# ============================================================================
@pcl.route('/complete/<profile_token>', methods=['GET', 'POST'])
def complete_profile(profile_token):
    """Public profile completion page - accessed via WhatsApp link"""
    registration = PCLRegistration.query.filter_by(profile_token=profile_token).first_or_404()
    team = registration.team
    
    lang = request.args.get('lang', registration.preferred_language or 'EN').upper()
    if lang not in TRANSLATIONS:
        lang = 'EN'
    
    t = get_translations(lang)
    
    # Calculate completion percentage
    missing_fields = registration.get_missing_fields()
    total_required = 3  # photo, shirt_size, bio
    completed = total_required - len(missing_fields)
    completion_percent = int((completed / total_required) * 100)
    
    # Parse existing additional photos
    additional_photos_list = []
    if registration.additional_photos:
        try:
            additional_photos_list = json.loads(registration.additional_photos)
        except:
            additional_photos_list = []
    
    if request.method == 'POST':
        # Handle profile photo upload
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                result = upload_photo_to_supabase(file, folder='players')
                if result['success']:
                    registration.photo_filename = result['url']
                else:
                    flash(f'Photo upload failed: {result["error"]}', 'warning')
        
        # Handle photos to delete
        photos_to_delete = request.form.get('photos_to_delete', '')
        if photos_to_delete:
            urls_to_delete = photos_to_delete.split('|||')
            additional_photos_list = [url for url in additional_photos_list if url not in urls_to_delete]
        
        # Handle additional photos upload
        if 'additional_photos' in request.files:
            files = request.files.getlist('additional_photos')
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    if len(additional_photos_list) >= 5:
                        break  # Max 5 photos
                    result = upload_photo_to_supabase(file, folder='players/social')
                    if result['success']:
                        additional_photos_list.append(result['url'])
        
        # Save additional photos as JSON
        registration.additional_photos = json.dumps(additional_photos_list) if additional_photos_list else None
        
        # Update other fields
        registration.shirt_size = request.form.get('shirt_size') or registration.shirt_size
        registration.shirt_size_2 = request.form.get('shirt_size_2') or registration.shirt_size_2
        registration.shirt_size_3 = request.form.get('shirt_size_3') or registration.shirt_size_3
        registration.bio = request.form.get('bio', '').strip() or registration.bio
        registration.email = request.form.get('email', '').strip() or registration.email
        registration.birth_year = int(request.form['birth_year']) if request.form.get('birth_year') else registration.birth_year
        registration.instagram = request.form.get('instagram', '').strip().replace('@', '') or registration.instagram
        registration.tiktok = request.form.get('tiktok', '').strip().replace('@', '') or registration.tiktok
        registration.youtube = request.form.get('youtube', '').strip() or registration.youtube
        registration.twitter = request.form.get('twitter', '').strip().replace('@', '') or registration.twitter
        registration.dupr_rating = request.form.get('dupr_rating', '').strip() or registration.dupr_rating
        registration.video_url = request.form.get('video_url', '').strip() or registration.video_url
        
        # Check completeness
        registration.check_completeness()
        
        try:
            db.session.commit()
            flash(t['profile_saved'], 'success')
            return redirect(url_for('pcl.complete_profile', profile_token=profile_token, lang=lang))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/complete_profile.html',
                         registration=registration,
                         team=team,
                         shirt_sizes=SHIRT_SIZES,
                         missing_fields=missing_fields,
                         completion_percent=completion_percent,
                         additional_photos_list=additional_photos_list,
                         t=t,
                         current_lang=lang)


# ============================================================================
# SEND PROFILE LINKS (WhatsApp)
# ============================================================================

@pcl.route('/team/<token>/send-link/<int:registration_id>', methods=['POST'])
def send_single_profile_link(token, registration_id):
    """Send profile completion link to a single player"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    # Verify registration belongs to this team
    if registration.team_id != team.id:
        flash('Invalid request!', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    lang = request.args.get('lang', registration.preferred_language or 'EN')
    t = get_translations(lang)
    
    if not registration.phone:
        flash(f'{registration.first_name}: No phone number!', 'warning')
        return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))
    
    # Generate token if not exists
    if not registration.profile_token:
        registration.generate_profile_token()
        db.session.commit()
    
    # Build URL and send
    profile_url = request.host_url.rstrip('/') + url_for('pcl.complete_profile', profile_token=registration.profile_token)
    message = get_profile_completion_message(registration, profile_url, registration.preferred_language or 'EN')
    sponsor_block = get_whatsapp_sponsor_block(pcl_tournament_id=team.tournament_id, language=registration.preferred_language or 'EN')
    message += sponsor_block

    result = send_whatsapp_message(registration.phone, message, test_mode=False)
    
    if result.get('status') in ['sent', 'queued']:
        registration.whatsapp_sent_at = datetime.now()
        db.session.commit()
        flash(f'{registration.first_name}: {t["whatsapp_sent"]}', 'success')
    else:
        flash(f'{registration.first_name}: {t["whatsapp_failed"]}', 'danger')
    
    return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))


@pcl.route('/team/<token>/send-all-links', methods=['POST'])
def send_all_profile_links(token):
    """Send profile completion links to all incomplete players"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    
    lang = request.args.get('lang', 'EN')
    t = get_translations(lang)
    
    sent_count = 0
    error_count = 0
    
    # Get all incomplete registrations with phone numbers
    incomplete = team.registrations.filter(
        PCLRegistration.status != 'complete',
        PCLRegistration.phone.isnot(None),
        PCLRegistration.phone != ''
    ).all()
    
    for registration in incomplete:
        # Generate token if not exists
        if not registration.profile_token:
            registration.generate_profile_token()
        
        profile_url = request.host_url.rstrip('/') + url_for('pcl.complete_profile', profile_token=registration.profile_token)
        message = get_profile_completion_message(registration, profile_url, registration.preferred_language or 'EN')
        sponsor_block = get_whatsapp_sponsor_block(pcl_tournament_id=team.tournament_id, language=registration.preferred_language or 'EN')
        message += sponsor_block

        result = send_whatsapp_message(registration.phone, message, test_mode=False)
        
        if result.get('status') in ['sent', 'queued']:
            sent_count += 1
        else:
            error_count += 1
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving: {str(e)}', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))
    
    if sent_count > 0:
        flash(f'Ã¢Å“â€¦ {sent_count} {t["whatsapp_sent"]}', 'success')
    if error_count > 0:
        flash(f'Ã¢Å¡Â Ã¯Â¸Â {error_count} {t["whatsapp_failed"]}', 'warning')
    if sent_count == 0 and error_count == 0:
        flash('No incomplete players with phone numbers found.', 'info')
    
    return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))


# ============================================================================
# DELETE PLAYER
# ============================================================================

@pcl.route('/team/<token>/delete-player/<int:registration_id>', methods=['POST'])
def delete_player(token, registration_id):
    """Delete a player from the team (captain only)"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    # Verify registration belongs to this team
    if registration.team_id != team.id:
        flash('Invalid request!', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    # Don't allow deleting captain
    if registration.is_captain:
        flash('Cannot delete the captain!', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    lang = request.args.get('lang', 'EN')
    player_name = f"{registration.first_name} {registration.last_name}"
    
    try:
        db.session.delete(registration)
        db.session.commit()
        flash(f'{player_name} wurde geloescht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('pcl.captain_dashboard', token=token, lang=lang))


# ============================================================================
# PLAYER REGISTRATION (Original Full Form)
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
        flash('Registration is closed.', 'danger')
        return redirect(url_for('pcl.captain_dashboard', token=token))
    
    if request.method == 'POST':
        # Handle profile photo upload to Supabase
        photo_url = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                result = upload_photo_to_supabase(file, folder='players')
                if result['success']:
                    photo_url = result['url']
                else:
                    flash(f'Photo upload failed: {result["error"]}', 'warning')
        
        # Handle additional photos upload
        additional_photos_list = []
        if 'additional_photos' in request.files:
            files = request.files.getlist('additional_photos')
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    if len(additional_photos_list) >= 5:
                        break  # Max 5 photos
                    result = upload_photo_to_supabase(file, folder='players/social')
                    if result['success']:
                        additional_photos_list.append(result['url'])
        
        # Create registration
        registration = PCLRegistration(
            team_id=team.id,
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            gender=request.form['gender'],
            birth_year=int(request.form['birth_year']) if request.form.get('birth_year') else None,
            is_captain=request.form.get('is_captain') == 'on',
            shirt_size=request.form.get('shirt_size'),
            shirt_size_2=request.form.get('shirt_size_2') or None,
            shirt_size_3=request.form.get('shirt_size_3') or None,
            photo_filename=photo_url,
            bio=request.form.get('bio'),
            instagram=request.form.get('instagram', '').replace('@', ''),
            tiktok=request.form.get('tiktok', '').replace('@', ''),
            youtube=request.form.get('youtube'),
            twitter=request.form.get('twitter', '').replace('@', ''),
            video_url=request.form.get('video_url'),
            dupr_rating=request.form.get('dupr_rating'),
            preferred_language=lang,
            additional_photos=json.dumps(additional_photos_list) if additional_photos_list else None
        )
        
        registration.generate_profile_token()
        registration.check_completeness()
        
        try:
            db.session.add(registration)
            db.session.commit()
            
            return redirect(url_for('pcl.registration_success', 
                                  registration_id=registration.id,
                                  lang=lang))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
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
    """Edit existing registration"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    team = registration.team
    
    lang = request.args.get('lang', registration.preferred_language).upper()
    t = get_translations(lang)
    
    if request.method == 'POST':
        registration.first_name = request.form['first_name']
        registration.last_name = request.form['last_name']
        registration.email = request.form.get('email')
        registration.phone = request.form.get('phone')
        registration.gender = request.form['gender']
        registration.birth_year = int(request.form['birth_year']) if request.form.get('birth_year') else None
        registration.is_captain = request.form.get('is_captain') == 'on'
        registration.is_playing = request.form.get('is_playing') == 'on'
        registration.shirt_size = request.form.get('shirt_size')
        registration.shirt_size_2 = request.form.get('shirt_size_2') or None
        registration.shirt_size_3 = request.form.get('shirt_size_3') or None
        registration.bio = request.form.get('bio')
        registration.instagram = request.form.get('instagram', '').replace('@', '')
        registration.tiktok = request.form.get('tiktok', '').replace('@', '')
        registration.youtube = request.form.get('youtube')
        registration.twitter = request.form.get('twitter', '').replace('@', '')
        registration.video_url = request.form.get('video_url')
        registration.dupr_rating = request.form.get('dupr_rating')
        registration.preferred_language = lang
        
        # Handle new photo upload
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                result = upload_photo_to_supabase(file, folder='players')
                if result['success']:
                    registration.photo_filename = result['url']
        
        registration.check_completeness()
        
        try:
            db.session.commit()
            flash(t['success_message'], 'success')
            return redirect(url_for('pcl.registration_success', 
                                  registration_id=registration.id,
                                  lang=lang))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/player_register.html',
                         team=team,
                         registration=registration,
                         shirt_sizes=SHIRT_SIZES,
                         t=t,
                         current_lang=lang,
                         edit_mode=True)


# ============================================================================
# ADMIN REGISTRATION EDIT
# ============================================================================

@pcl.route('/admin/registration/<int:registration_id>/edit', methods=['GET', 'POST'])
def admin_edit_registration(registration_id):
    """Admin edit registration"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    team = registration.team
    
    if request.method == 'POST':
        registration.first_name = request.form['first_name']
        registration.last_name = request.form['last_name']
        registration.email = request.form.get('email')
        registration.phone = request.form.get('phone')
        registration.gender = request.form['gender']
        registration.birth_year = int(request.form['birth_year']) if request.form.get('birth_year') else None
        registration.is_captain = request.form.get('is_captain') == 'on'
        registration.shirt_size = request.form.get('shirt_size')
        registration.shirt_size_2 = request.form.get('shirt_size_2') or None
        registration.shirt_size_3 = request.form.get('shirt_size_3') or None
        registration.bio = request.form.get('bio')
        registration.instagram = request.form.get('instagram', '').replace('@', '')
        registration.tiktok = request.form.get('tiktok', '').replace('@', '')
        registration.youtube = request.form.get('youtube')
        registration.twitter = request.form.get('twitter', '').replace('@', '')
        registration.video_url = request.form.get('video_url')
        registration.dupr_rating = request.form.get('dupr_rating')
        registration.preferred_language = request.form.get('preferred_language', 'EN')
        registration.status = request.form.get('status', registration.status)
        
        # Handle photo URL or file upload
        photo_url = request.form.get('photo_filename')
        if photo_url:
            registration.photo_filename = photo_url
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                result = upload_photo_to_supabase(file, folder='players')
                if result['success']:
                    registration.photo_filename = result['url']
        
        registration.check_completeness()
        
        try:
            db.session.commit()
            flash(f'Registration for {registration.first_name} {registration.last_name} updated!', 'success')
            return redirect(url_for('pcl.admin_team_detail', team_id=team.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('pcl/pcl_registration_edit.html',
                         registration=registration,
                         team=team)


# ============================================================================
# DELETE ROUTES
# ============================================================================

@pcl.route('/admin/team/<int:team_id>/delete', methods=['POST'])
def delete_team(team_id):
    """Delete a team and all its registrations"""
    team = PCLTeam.query.get_or_404(team_id)
    tournament_id = team.tournament_id
    team_name = f"{team.country_name} {team.age_category}"
    
    try:
        PCLRegistration.query.filter_by(team_id=team_id).delete()
        db.session.delete(team)
        db.session.commit()
        flash(f'Team "{team_name}" deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting team: {str(e)}', 'danger')
    
    return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament_id))


@pcl.route('/admin/registration/<int:registration_id>/delete', methods=['POST'])
def delete_registration(registration_id):
    """Delete a single player registration"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    team_id = registration.team_id
    player_name = f"{registration.first_name} {registration.last_name}"
    
    try:
        db.session.delete(registration)
        db.session.commit()
        flash(f'Registration "{player_name}" deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting registration: {str(e)}', 'danger')
    
    return redirect(url_for('pcl.admin_team_detail', team_id=team_id))


# ============================================================================
# CAPTAIN MESSAGING (WhatsApp Invitations & Reminders)
# ============================================================================

def get_captain_invitation_message(team, captain_name, captain_url, language='EN'):
    """Get captain invitation message in specified language"""
    messages = {
        'EN': f""" PCL {team.tournament.name} - Team Captain Invitation

Hi {captain_name}! Ã°Å¸â€˜â€¹

You have been selected as Captain for {team.country_flag} {team.country_name} {team.age_category}!

Ã°Å¸â€œâ€¹ Your responsibilities:
Ã¢â‚¬Â¢ Register your team players
Ã¢â‚¬Â¢ Ensure all profiles are complete
Ã¢â‚¬Â¢ Coordinate with your team

Ã°Å¸â€â€” Your secret Captain Dashboard:
{captain_url}

Ã¢Å¡Â Ã¯Â¸Â Keep this link private - only you should have access!

Ã°Å¸â€œâ€¦ Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Let's go! 
WPC Series Europe""",
        
        'DE': f""" PCL {team.tournament.name} - Team-Kapitaen Einladung

Hallo {captain_name}! Ã°Å¸â€˜â€¹

Du wurdest als Kapitaen fuer {team.country_flag} {team.country_name} {team.age_category} ausgewaehlt!

Ã°Å¸â€œâ€¹ Deine Aufgaben:
Ã¢â‚¬Â¢ Team-Spieler registrieren
Ã¢â‚¬Â¢ Alle Profile vervollstaendigen
Ã¢â‚¬Â¢ Mit deinem Team koordinieren

Ã°Å¸â€â€” Dein geheimes Kapitaen-Dashboard:
{captain_url}

Ã¢Å¡Â Ã¯Â¸Â Behalte diesen Link privat - nur du solltest Zugriff haben!

Ã°Å¸â€œâ€¦ Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Los geht's! 
WPC Series Europe""",
        
        'ES': f""" PCL {team.tournament.name} - InvitaciÃƒÂ³n CapitÃƒÂ¡n

Hola {captain_name}! Ã°Å¸â€˜â€¹

Has sido seleccionado como CapitÃƒÂ¡n de {team.country_flag} {team.country_name} {team.age_category}!

Ã°Å¸â€œâ€¹ Tus responsabilidades:
Ã¢â‚¬Â¢ Registrar los jugadores del equipo
Ã¢â‚¬Â¢ Asegurar que todos los perfiles esten completos
Ã¢â‚¬Â¢ Coordinar con tu equipo

Ã°Å¸â€â€” Tu Panel de CapitÃƒÂ¡n secreto:
{captain_url}

Ã¢Å¡Â Ã¯Â¸Â Manten este enlace privado!

Ã°Å¸â€œâ€¦ Fecha limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Vamos! 
WPC Series Europe""",
        
        'FR': f""" PCL {team.tournament.name} - Invitation Capitaine

Bonjour {captain_name}! Ã°Å¸â€˜â€¹

Vous avez ete selectionne comme Capitaine de {team.country_flag} {team.country_name} {team.age_category}!

Ã°Å¸â€œâ€¹ Vos responsabilites:
Ã¢â‚¬Â¢ Inscrire les joueurs de l'equipe
Ã¢â‚¬Â¢ S'assurer que tous les profils sont complets
Ã¢â‚¬Â¢ Coordonner avec votre equipe

Ã°Å¸â€â€” Votre Tableau de bord Capitaine secret:
{captain_url}

Ã¢Å¡Â Ã¯Â¸Â Gardez ce lien prive!

Ã°Å¸â€œâ€¦ Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

C'est parti! 
WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """Get captain reminder message in specified language"""
    messages = {
        'EN': f"""Ã¢ÂÂ° PCL {team.tournament.name} - Reminder!

Hi {captain_name}!

Your team {team.country_flag} {team.country_name} {team.age_category} is not yet complete.

Ã°Å¸â€œÅ  Current status:
Ã°Å¸â€˜Â¨ Men: {stats['men']}/{team.min_men}-{team.max_men}
Ã°Å¸â€˜Â© Women: {stats['women']}/{team.min_women}-{team.max_women}
Ã¢Å“â€œ Complete profiles: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Ã°Å¸â€â€” Captain Dashboard:
{captain_url}

Ã°Å¸â€œâ€¦ Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Please complete your team! 
WPC Series Europe""",
        
        'DE': f"""Ã¢ÂÂ° PCL {team.tournament.name} - Erinnerung!

Hallo {captain_name}!

Dein Team {team.country_flag} {team.country_name} {team.age_category} ist noch nicht vollstaendig.

Ã°Å¸â€œÅ  Aktueller Status:
Ã°Å¸â€˜Â¨ Maenner: {stats['men']}/{team.min_men}-{team.max_men}
Ã°Å¸â€˜Â© Frauen: {stats['women']}/{team.min_women}-{team.max_women}
Ã¢Å“â€œ Vollstaendige Profile: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Ã°Å¸â€â€” Kapitaen-Dashboard:
{captain_url}

Ã°Å¸â€œâ€¦ Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Bitte vervollstaendige dein Team! 
WPC Series Europe""",
        
        'ES': f"""Ã¢ÂÂ° PCL {team.tournament.name} - Recordatorio!

Hola {captain_name}!

Tu equipo {team.country_flag} {team.country_name} {team.age_category} aÃƒÂºn no estÃƒÂ¡ completo.

Ã°Å¸â€œÅ  Estado actual:
Ã°Å¸â€˜Â¨ Hombres: {stats['men']}/{team.min_men}-{team.max_men}
Ã°Å¸â€˜Â© Mujeres: {stats['women']}/{team.min_women}-{team.max_women}
Ã¢Å“â€œ Perfiles completos: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Ã°Å¸â€â€” Panel de CapitÃƒÂ¡n:
{captain_url}

Ã°Å¸â€œâ€¦ Fecha limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Por favor completa tu equipo! 
WPC Series Europe""",
        
        'FR': f"""Ã¢ÂÂ° PCL {team.tournament.name} - Rappel!

Bonjour {captain_name}!

Votre equipe {team.country_flag} {team.country_name} {team.age_category} n'est pas encore complÃƒÂ¨te.

Ã°Å¸â€œÅ  Statut actuel:
Ã°Å¸â€˜Â¨ Hommes: {stats['men']}/{team.min_men}-{team.max_men}
Ã°Å¸â€˜Â© Femmes: {stats['women']}/{team.min_women}-{team.max_women}
Ã¢Å“â€œ Profils complets: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Ã°Å¸â€â€” Tableau de bord Capitaine:
{captain_url}

Ã°Å¸â€œâ€¦ Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Veuillez completer votre equipe! 
WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


@pcl.route('/admin/team/<int:team_id>/send-captain-invite', methods=['GET', 'POST'])
def send_captain_invite(team_id):
    """Send captain invitation via WhatsApp"""
    team = PCLTeam.query.get_or_404(team_id)
    captain_reg = team.registrations.filter_by(is_captain=True).first()
    
    if request.method == 'POST':
        captain_name = request.form.get('captain_name', 'Captain')
        captain_phone = request.form.get('captain_phone', '')
        language = request.form.get('language', 'EN')
        test_mode = request.form.get('test_mode') == 'on'
        
        if not captain_phone:
            flash('Phone number is required!', 'danger')
            return redirect(url_for('pcl.send_captain_invite', team_id=team_id))
        
        captain_url = request.host_url.rstrip('/') + url_for('pcl.captain_dashboard', token=team.captain_token)
        message = get_captain_invitation_message(team, captain_name, captain_url, language)
        sponsor_block = get_whatsapp_sponsor_block(pcl_tournament_id=team.tournament_id, language=language)
        message += sponsor_block

        result = send_whatsapp_message(captain_phone, message, test_mode=test_mode)
        
        if result.get('status') in ['sent', 'queued', 'test_mode']:
            mode_text = " (TEST MODE)" if test_mode else ""
            flash(f'Captain invitation sent to {captain_name}{mode_text}!', 'success')
        else:
            flash(f'Error sending: {result.get("error", "Unknown error")}', 'danger')
        
        return redirect(url_for('pcl.admin_team_detail', team_id=team_id))
    
    return render_template('pcl/send_captain_invite.html', 
                         team=team,
                         captain_reg=captain_reg)


@pcl.route('/admin/team/<int:team_id>/send-captain-reminder', methods=['POST'])
def send_captain_reminder(team_id):
    """Send captain reminder via WhatsApp"""
    team = PCLTeam.query.get_or_404(team_id)
    
    captain_name = request.form.get('captain_name', 'Captain')
    captain_phone = request.form.get('captain_phone', '')
    language = request.form.get('language', 'EN')
    test_mode = request.form.get('test_mode') == 'on'
    
    if not captain_phone:
        flash('Phone number is required!', 'danger')
        return redirect(url_for('pcl.admin_team_detail', team_id=team_id))
    
    captain_url = request.host_url.rstrip('/') + url_for('pcl.captain_dashboard', token=team.captain_token)
    stats = team.get_stats()
    message = get_captain_reminder_message(team, captain_name, captain_url, stats, language)
    sponsor_block = get_whatsapp_sponsor_block(pcl_tournament_id=team.tournament_id, language=language)
    message += sponsor_block

    result = send_whatsapp_message(captain_phone, message, test_mode=test_mode)
    
    if result.get('status') in ['sent', 'queued', 'test_mode']:
        mode_text = " (TEST MODE)" if test_mode else ""
        flash(f'Reminder sent to {captain_name}{mode_text}!', 'success')
    else:
        flash(f'Error sending: {result.get("error", "Unknown error")}', 'danger')
    
    return redirect(url_for('pcl.admin_team_detail', team_id=team_id))


@pcl.route('/admin/tournament/<int:tournament_id>/send-all-reminders', methods=['POST'])
def send_all_captain_reminders(tournament_id):
    """Send reminders to all captains with incomplete teams"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    test_mode = request.form.get('test_mode') == 'on'
    
    sent_count = 0
    error_count = 0
    skipped_count = 0
    
    for team in tournament.teams.all():
        stats = team.get_stats()
        
        if stats['is_complete']:
            skipped_count += 1
            continue
        
        captain_reg = team.registrations.filter_by(is_captain=True).first()
        
        if not captain_reg or not captain_reg.phone:
            error_count += 1
            continue
        
        captain_url = request.host_url.rstrip('/') + url_for('pcl.captain_dashboard', token=team.captain_token)
        message = get_captain_reminder_message(
            team,
            captain_reg.first_name,
            captain_url,
            stats,
            captain_reg.preferred_language or 'EN'
        )
        sponsor_block = get_whatsapp_sponsor_block(pcl_tournament_id=team.tournament_id, language=captain_reg.preferred_language or 'EN')
        message += sponsor_block

        result = send_whatsapp_message(captain_reg.phone, message, test_mode=test_mode)
        
        if result.get('status') in ['sent', 'queued', 'test_mode']:
            sent_count += 1
        else:
            error_count += 1
    
    mode_text = " (TEST MODE)" if test_mode else ""
    if sent_count > 0:
        flash(f'{sent_count} reminder(s) sent{mode_text}!', 'success')
    if skipped_count > 0:
        flash(f'{skipped_count} complete team(s) skipped.', 'info')
    if error_count > 0:
        flash(f'{error_count} could not be sent (no captain/phone).', 'warning')
    
    return redirect(url_for('pcl.admin_tournament_detail', tournament_id=tournament_id))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@pcl.route('/api/team/<token>/status')
def api_team_status(token):
    """API endpoint for team status (for AJAX updates)"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    stats = team.get_stats()
    
    return jsonify({
        'team': f"{team.country_flag} {team.country_name} {team.age_category}",
        'stats': stats,
        'deadline': team.tournament.registration_deadline.isoformat(),
        'is_complete': stats['is_complete']
    })


@pcl.route('/api/team/<token>/players')
def api_team_players(token):
    """API endpoint for team players list"""
    team = PCLTeam.query.filter_by(captain_token=token).first_or_404()
    
    players = []
    for reg in team.registrations.all():
        players.append({
            'id': reg.id,
            'name': f"{reg.first_name} {reg.last_name}",
            'gender': reg.gender,
            'status': reg.status,
            'has_photo': bool(reg.photo_filename),
            'has_bio': bool(reg.bio),
            'shirt_size': reg.shirt_size,
            'shirt_size_2': reg.shirt_size_2,
            'shirt_size_3': reg.shirt_size_3,
            'missing_fields': reg.get_missing_fields()
        })
    
    return jsonify({
        'team': f"{team.country_flag} {team.country_name} {team.age_category}",
        'players': players,
        'stats': team.get_stats()
    })

# ============================================================================
# PLAYER CARDS ROUTES
# ============================================================================
@pcl.route('/cards/tournament/<int:tournament_id>')
def player_cards_tournament(tournament_id):
    """Player cards generator for entire tournament"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    registrations = []
    for team in tournament.teams.order_by(PCLTeam.country_name).all():
        for reg in team.registrations.all():
            registrations.append(reg)
    
    # Use first team as default for template compatibility
    first_team = tournament.teams.first()
    
    return render_template('pcl/player_cards.html',
                         team=first_team,
                         tournament=tournament,
                         registrations=registrations,
                         all_teams=True)

@pcl.route('/cards/team/<int:team_id>')
def player_cards_team(team_id):
    """Player cards generator for a single team"""
    team = PCLTeam.query.get_or_404(team_id)
    registrations = team.registrations.all()
    
    return render_template('pcl/player_cards.html',
                         team=team,
                         tournament=team.tournament,
                         registrations=registrations,
                         all_teams=False)


# ============================================================================
# CHECK-IN SYSTEM
# ============================================================================

# Helper: QR Code Generation
def generate_qr_code_base64(data, size=200):
    """Generate QR code as base64 string"""
    try:
        import qrcode
        from PIL import Image
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        return None


def get_qr_code_url(data, size=200):
    """Get QR code URL (fallback if qrcode library not available)"""
    import urllib.parse
    encoded = urllib.parse.quote(data)
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}"


# Check-in Translations
CHECKIN_TRANSLATIONS = {
    'EN': {
        'checkin_title': 'Tournament Check-in',
        'welcome': 'Welcome',
        'team': 'Team',
        'shirt_size': 'Shirt Size',
        'checkin_button': 'Check In Now',
        'already_checked_in': 'Already Checked In',
        'checked_in_at': 'Checked in at',
        'success_title': 'Check-in Complete!',
        'success_message': 'Please proceed to the Welcome Desk to collect your welcome pack.',
        'show_pass': 'Show this pass at the Welcome Desk',
        'add_to_wallet': 'Add to Apple Wallet',
        'save_pass': 'Save / Screenshot',
        'staff_station': 'Staff Check-in Station',
        'scan_qr': 'Scan QR Code',
        'search_player': 'Search Player',
        'not_found': 'Player not found',
        'checkin_success': 'Successfully checked in',
        'total_players': 'Total Players',
        'checked_in': 'Checked In',
        'pending': 'Pending',
    },
    'DE': {
        'checkin_title': 'Turnier Check-in',
        'welcome': 'Willkommen',
        'team': 'Team',
        'shirt_size': 'Shirt-GrÃ¶ÃŸe',
        'checkin_button': 'Jetzt einchecken',
        'already_checked_in': 'Bereits eingecheckt',
        'checked_in_at': 'Eingecheckt um',
        'success_title': 'Check-in erfolgreich!',
        'success_message': 'Bitte gehe zum Welcome Desk um dein Welcome Pack abzuholen.',
        'show_pass': 'Zeige diesen Pass am Welcome Desk',
        'add_to_wallet': 'Zu Apple Wallet hinzufÃ¼gen',
        'save_pass': 'Speichern / Screenshot',
        'staff_station': 'Staff Check-in Station',
        'scan_qr': 'QR-Code scannen',
        'search_player': 'Spieler suchen',
        'not_found': 'Spieler nicht gefunden',
        'checkin_success': 'Erfolgreich eingecheckt',
        'total_players': 'Gesamt Spieler',
        'checked_in': 'Eingecheckt',
        'pending': 'Ausstehend',
    },
    'ES': {
        'checkin_title': 'Check-in del Torneo',
        'welcome': 'Bienvenido',
        'team': 'Equipo',
        'shirt_size': 'Talla de Camiseta',
        'checkin_button': 'Hacer Check-in',
        'already_checked_in': 'Ya registrado',
        'checked_in_at': 'Registrado a las',
        'success_title': 'Â¡Check-in completado!',
        'success_message': 'Por favor dirÃ­gete al Welcome Desk para recoger tu pack de bienvenida.',
        'show_pass': 'Muestra este pase en el Welcome Desk',
        'add_to_wallet': 'AÃ±adir a Apple Wallet',
        'save_pass': 'Guardar / Captura',
        'staff_station': 'EstaciÃ³n de Check-in Staff',
        'scan_qr': 'Escanear cÃ³digo QR',
        'search_player': 'Buscar jugador',
        'not_found': 'Jugador no encontrado',
        'checkin_success': 'Check-in exitoso',
        'total_players': 'Total Jugadores',
        'checked_in': 'Registrados',
        'pending': 'Pendientes',
    },
    'FR': {
        'checkin_title': 'Check-in du Tournoi',
        'welcome': 'Bienvenue',
        'team': 'Ã‰quipe',
        'shirt_size': 'Taille de Maillot',
        'checkin_button': 'Check-in maintenant',
        'already_checked_in': 'DÃ©jÃ  enregistrÃ©',
        'checked_in_at': 'EnregistrÃ© Ã ',
        'success_title': 'Check-in rÃ©ussi!',
        'success_message': 'Veuillez vous rendre au Welcome Desk pour rÃ©cupÃ©rer votre pack de bienvenue.',
        'show_pass': 'Montrez ce pass au Welcome Desk',
        'add_to_wallet': 'Ajouter Ã  Apple Wallet',
        'save_pass': 'Sauvegarder / Capture',
        'staff_station': 'Station de Check-in Staff',
        'scan_qr': 'Scanner le code QR',
        'search_player': 'Rechercher un joueur',
        'not_found': 'Joueur non trouvÃ©',
        'checkin_success': 'Check-in rÃ©ussi',
        'total_players': 'Total Joueurs',
        'checked_in': 'EnregistrÃ©s',
        'pending': 'En attente',
    }
}

def get_checkin_translations(lang='EN'):
    return CHECKIN_TRANSLATIONS.get(lang, CHECKIN_TRANSLATIONS['EN'])


# ============================================================================
# PLAYER SELF CHECK-IN ROUTES
# ============================================================================

@pcl.route('/checkin/<token>')
def player_checkin(token):
    """Player check-in page - accessed via QR code or link"""
    registration = PCLRegistration.query.filter_by(profile_token=token).first_or_404()
    team = registration.team
    tournament = team.tournament
    
    lang = request.args.get('lang', registration.preferred_language or 'EN').upper()
    if lang not in CHECKIN_TRANSLATIONS:
        lang = 'EN'
    t = get_checkin_translations(lang)
    
    # Generate QR code
    checkin_url = request.host_url.rstrip('/') + url_for('pcl.player_checkin', token=token)
    qr_base64 = generate_qr_code_base64(checkin_url, size=250)
    qr_url = get_qr_code_url(checkin_url, size=250) if not qr_base64 else None
    
    return render_template('pcl/checkin.html',
                         registration=registration,
                         team=team,
                         tournament=tournament,
                         qr_base64=qr_base64,
                         qr_url=qr_url,
                         t=t,
                         current_lang=lang)


@pcl.route('/checkin/<token>/confirm', methods=['POST'])
def confirm_checkin(token):
    """Process player check-in with phone and GDPR consent"""
    registration = PCLRegistration.query.filter_by(profile_token=token).first_or_404()

    lang = request.form.get('language', registration.preferred_language or 'EN').upper()

    # Check if already checked in
    if registration.checked_in:
        return redirect(url_for('pcl.wallet_pass', token=token, lang=lang))

    # Get form data
    phone = request.form.get('phone', '').strip()
    privacy_accepted = request.form.get('privacy_accepted') == 'on'
    whatsapp_optin = request.form.get('whatsapp_optin') == 'on'
    marketing_optin = request.form.get('marketing_optin') == 'on'

    # Validate required fields
    if not phone:
        flash('Phone number is required', 'danger')
        return redirect(url_for('pcl.player_checkin', token=token))

    if not privacy_accepted:
        flash('You must accept the Privacy Policy', 'danger')
        return redirect(url_for('pcl.player_checkin', token=token))

    # Save consent and phone
    registration.phone = phone
    registration.preferred_language = lang
    registration.privacy_accepted = True
    registration.privacy_accepted_at = datetime.utcnow()
    registration.whatsapp_optin = whatsapp_optin
    registration.marketing_optin = marketing_optin

    # Perform check-in
    registration.checked_in = True
    registration.checked_in_at = datetime.utcnow()

    try:
        db.session.commit()
        return redirect(url_for('pcl.wallet_pass', token=token, lang=lang))
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('pcl.player_checkin', token=token))
# ============================================================================
# WALLET PASS (Web Version)
# ============================================================================

@pcl.route('/checkin/pass/<token>')
def wallet_pass(token):
    """Show wallet-style pass after check-in"""
    registration = PCLRegistration.query.filter_by(profile_token=token).first_or_404()
    team = registration.team
    tournament = team.tournament
    
    lang = request.args.get('lang', registration.preferred_language or 'EN').upper()
    if lang not in CHECKIN_TRANSLATIONS:
        lang = 'EN'
    t = get_checkin_translations(lang)
    
    # Generate QR code
    checkin_url = request.host_url.rstrip('/') + url_for('pcl.player_checkin', token=token)
    qr_base64 = generate_qr_code_base64(checkin_url, size=180)
    qr_url = get_qr_code_url(checkin_url, size=180) if not qr_base64 else None
    
    return render_template('pcl/wallet_pass.html',
                         registration=registration,
                         team=team,
                         tournament=tournament,
                         qr_base64=qr_base64,
                         qr_url=qr_url,
                         t=t,
                         current_lang=lang)


# ============================================================================
# APPLE WALLET (.pkpass)
# ============================================================================

@pcl.route('/checkin/pass/<token>/apple')
def apple_wallet_pass(token):
    """Generate Apple Wallet .pkpass file"""
    registration = PCLRegistration.query.filter_by(profile_token=token).first_or_404()
    team = registration.team
    tournament = team.tournament
    
    try:
        from utils.wallet_pass import create_pkpass, is_apple_wallet_available
        
        if not is_apple_wallet_available():
            flash('Apple Wallet is not configured', 'warning')
            return redirect(url_for('pcl.wallet_pass', token=token))
        
        pkpass_data = create_pkpass(
            registration=registration,
            team=team,
            tournament=tournament
        )
        
        if pkpass_data:
            filename = f"WPC_{registration.first_name}_{registration.last_name}.pkpass"
            return send_file(
                io.BytesIO(pkpass_data),
                mimetype='application/vnd.apple.pkpass',
                as_attachment=True,
                download_name=filename
            )
        else:
            flash('Error generating Apple Wallet pass', 'danger')
            return redirect(url_for('pcl.wallet_pass', token=token))
            
    except ImportError:
        flash('Apple Wallet module not available', 'warning')
        return redirect(url_for('pcl.wallet_pass', token=token))
    except Exception as e:
        print(f"Apple Wallet Error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('pcl.wallet_pass', token=token))


# ============================================================================
# ADMIN: STAFF CHECK-IN STATION
# ============================================================================

@pcl.route('/admin/tournament/<int:tournament_id>/checkin')
def staff_checkin_station(tournament_id):
    """Staff check-in station dashboard"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    # Get all registrations for this tournament
    registrations = PCLRegistration.query.join(PCLTeam).filter(
        PCLTeam.tournament_id == tournament_id
    ).order_by(PCLRegistration.last_name).all()
    
    # Stats
    total = len(registrations)
    checked_in = len([r for r in registrations if r.checked_in])
    pending = total - checked_in
    
    # Group by team
    teams_data = {}
    for reg in registrations:
        team_key = f"{reg.team.country_flag} {reg.team.country_name} {reg.team.age_category}"
        if team_key not in teams_data:
            teams_data[team_key] = {
                'team': reg.team,
                'players': [],
                'checked_in': 0,
                'total': 0
            }
        teams_data[team_key]['players'].append(reg)
        teams_data[team_key]['total'] += 1
        if reg.checked_in:
            teams_data[team_key]['checked_in'] += 1
    
    t = get_checkin_translations('EN')
    
    return render_template('pcl/staff_checkin.html',
                         tournament=tournament,
                         registrations=registrations,
                         teams_data=teams_data,
                         stats={'total': total, 'checked_in': checked_in, 'pending': pending},
                         t=t)


@pcl.route('/admin/tournament/<int:tournament_id>/checkin/search')
def staff_search_player(tournament_id):
    """Search for player (AJAX endpoint)"""
    query = request.args.get('q', '').strip().lower()
    
    if len(query) < 2:
        return jsonify({'players': []})
    
    registrations = PCLRegistration.query.join(PCLTeam).filter(
        PCLTeam.tournament_id == tournament_id,
        db.or_(
            PCLRegistration.first_name.ilike(f'%{query}%'),
            PCLRegistration.last_name.ilike(f'%{query}%')
        )
    ).limit(10).all()

    players = []
    for reg in registrations:
        players.append({
            'id': reg.id,
            'name': f"{reg.first_name} {reg.last_name}",
            'team': f"{reg.team.country_flag} {reg.team.country_name} {reg.team.age_category}",
            'shirt_size': reg.shirt_size,
            'shirt_size_2': reg.shirt_size_2,
            'shirt_size_3': reg.shirt_size_3,
            'checked_in': reg.checked_in,
            'checked_in_at': reg.checked_in_at.strftime('%H:%M') if reg.checked_in_at else None,
            'photo': reg.photo_filename
        })
    
    return jsonify({'players': players})


@pcl.route('/admin/checkin/<int:registration_id>', methods=['POST'])
def staff_do_checkin(registration_id):
    """Staff performs check-in for a player"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    if not registration.checked_in:
        registration.checked_in = True
        registration.checked_in_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'{registration.first_name} {registration.last_name} checked in!',
                'checked_in_at': registration.checked_in_at.strftime('%H:%M')
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({
            'success': True,
            'message': 'Already checked in',
            'checked_in_at': registration.checked_in_at.strftime('%H:%M') if registration.checked_in_at else None
        })


@pcl.route('/admin/checkin/<int:registration_id>/undo', methods=['POST'])
def staff_undo_checkin(registration_id):
    """Undo a check-in (staff only)"""
    registration = PCLRegistration.query.get_or_404(registration_id)
    
    registration.checked_in = False
    registration.checked_in_at = None
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Check-in undone'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN: QR CODE GENERATION
# ============================================================================

@pcl.route('/admin/tournament/<int:tournament_id>/qrcodes')
def generate_qrcodes(tournament_id):
    """Generate printable QR codes for all players"""
    tournament = PCLTournament.query.get_or_404(tournament_id)
    
    registrations = PCLRegistration.query.join(PCLTeam).filter(
        PCLTeam.tournament_id == tournament_id
    ).order_by(PCLTeam.country_name, PCLRegistration.last_name).all()
    
    # Generate tokens if missing
    for reg in registrations:
        if not reg.profile_token:
            reg.generate_profile_token()
    
    try:
        db.session.commit()
    except:
        db.session.rollback()
    
    # Generate QR codes
    players_with_qr = []
    base_url = request.host_url.rstrip('/')
    
    for reg in registrations:
        checkin_url = f"{base_url}/pcl/checkin/{reg.profile_token}"
        qr_base64 = generate_qr_code_base64(checkin_url, size=150)
        qr_url = get_qr_code_url(checkin_url, size=150) if not qr_base64 else None
        
        players_with_qr.append({
            'registration': reg,
            'qr_base64': qr_base64,
            'qr_url': qr_url,
            'checkin_url': checkin_url
        })
    
    return render_template('pcl/qrcodes_print.html',
                         tournament=tournament,
                         players=players_with_qr)


# ============================================================================
# API: LIVE STATS
# ============================================================================

@pcl.route('/api/checkin/stats/<int:tournament_id>')
def checkin_stats_api(tournament_id):
    """Get live check-in stats (for dashboard auto-refresh)"""
    registrations = PCLRegistration.query.join(PCLTeam).filter(
        PCLTeam.tournament_id == tournament_id
    ).all()
    
    total = len(registrations)
    checked_in = len([r for r in registrations if r.checked_in])
    
    # Recent check-ins
    recent = PCLRegistration.query.join(PCLTeam).filter(
        PCLTeam.tournament_id == tournament_id,
        PCLRegistration.checked_in == True
    ).order_by(PCLRegistration.checked_in_at.desc()).limit(5).all()
    
    return jsonify({
        'total': total,
        'checked_in': checked_in,
        'pending': total - checked_in,
        'percentage': round(checked_in / total * 100, 1) if total > 0 else 0,
        'recent': [
            {
                'name': f"{r.first_name} {r.last_name}",
                'team': f"{r.team.country_flag} {r.team.country_name}",
                'time': r.checked_in_at.strftime('%H:%M') if r.checked_in_at else None
            }
            for r in recent
        ]
    })
@pcl.route('/terms')
def terms():
    """Privacy Policy and Terms page"""
    return render_template('terms.html')

