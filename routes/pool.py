# -*- coding: utf-8 -*-
"""Player Pool - public interest registration + admin tools (blueprint 'pool')."""
import hashlib
from datetime import datetime
from urllib.parse import quote

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app)

from models import db, PoolPlayer
from utils.supabase_storage import upload_photo_to_supabase

pool_bp = Blueprint('pool', __name__)

# Common countries for the dropdown (extend as needed).
POOL_COUNTRIES = [
    'Spain', 'Italy', 'Germany', 'France', 'United Kingdom', 'Portugal',
    'Netherlands', 'Belgium', 'Austria', 'Switzerland', 'Ireland', 'Poland',
    'Sweden', 'Norway', 'Denmark', 'Finland', 'Czech Republic', 'Greece',
    'Turkey', 'United States', 'Canada', 'Australia', 'Other',
]

POOL_STATUSES = ['new', 'contacted', 'interested', 'joined_team', 'declined', 'wpc_customer']

# status -> bootstrap badge colour
STATUS_COLORS = {
    'new': 'primary', 'contacted': 'info', 'interested': 'warning',
    'joined_team': 'success', 'declined': 'secondary', 'wpc_customer': 'dark',
}

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def validate_dupr(value):
    """Normalize and validate a DUPR value.

    Accepts comma or dot decimals and up to 3 decimal places; valid range 1.0-8.0.
    Returns (normalized_str, ok). Empty/invalid -> (None, False).
    """
    v = (value or '').strip().replace(',', '.')
    if not v:
        return None, False
    try:
        f = float(v)
    except ValueError:
        return None, False
    if not (1.0 <= f <= 8.0):
        return None, False
    return str(round(f, 3)), True


# ---- Translations (ASCII-only for ES/FR) -----------------------------------
POOL_TRANSLATIONS = {
    'EN': {
        'hero_title': 'Join the WPC/PCL Player Pool',
        'hero_sub': 'One profile, every tournament.',
        'value_1': 'Tournament updates via WhatsApp and email',
        'value_2': 'Get found by captains in your country',
        'value_3': 'Permanent player profile across all tournaments',
        'value_4': 'Early bird access for upcoming tournaments',
        'first_name': 'First name', 'last_name': 'Last name', 'email': 'Email',
        'phone': 'WhatsApp number', 'country': 'Country', 'age_category': 'Age category',
        'gender': 'Gender', 'birth_year': 'Birth year', 'birth_year_help': '4 digits, e.g. 1985', 'dupr': 'DUPR rating',
        'pool_dupr_singles_label': 'DUPR Singles', 'pool_dupr_doubles_label': 'DUPR Doubles',
        'pool_dupr_help': "Both DUPR ratings are required. See dupr.com if you don't have your rating yet.",
        'pool_dupr_invalid': 'DUPR must be a number between 1.0 and 8.0',
        'photo': 'Photo', 'bio': 'About me', 'language': 'Preferred language',
        'male': 'Male', 'female': 'Female', 'required': 'required', 'optional': 'optional',
        'select': 'Select', 'phone_help': 'With country code, e.g. +34 600 123 456',
        'dupr_help': 'Your DUPR rating if you have one - see dupr.com',
        'consent_gdpr': 'I consent to my data being stored and used for WPC/PCL communications',
        'consent_marketing': 'I want to receive tournament updates via WhatsApp and email',
        'submit': 'Join the Pool',
        'success_title': 'Welcome to the Pool',
        'success_next': 'What happens next',
        'success_n1': 'Captains in your country can now see your profile',
        'success_n2': 'You will be notified about upcoming tournaments',
        'success_n3': 'You can edit your profile anytime with this link',
        'already_in_pool': 'You are already in the pool. Here is your edit link',
        'back_home': 'Back to homepage',
        'edit_profile': 'Edit your profile',
        'save': 'Save', 'admin_section_title': 'Player Pool',
        'status_new': 'New', 'status_contacted': 'Contacted', 'status_interested': 'Interested',
        'status_joined_team': 'Joined team', 'status_declined': 'Declined', 'status_wpc_customer': 'WPC customer',
        'data_note': 'Your data is stored securely and only used for WPC/PCL tournament communications.',
    },
    'DE': {
        'hero_title': 'Tritt dem WPC/PCL Spieler-Pool bei',
        'hero_sub': 'Ein Profil, alle Turniere.',
        'value_1': 'Turnier-Updates per WhatsApp und E-Mail',
        'value_2': 'Werde von Kapitaenen in deinem Land gefunden',
        'value_3': 'Dauerhaftes Spielerprofil fuer alle Turniere',
        'value_4': 'Frueher Zugang zu kommenden Turnieren',
        'first_name': 'Vorname', 'last_name': 'Nachname', 'email': 'E-Mail',
        'phone': 'WhatsApp-Nummer', 'country': 'Land', 'age_category': 'Alterskategorie',
        'gender': 'Geschlecht', 'birth_year': 'Geburtsjahr', 'birth_year_help': '4 Ziffern, z.B. 1985', 'dupr': 'DUPR-Wertung',
        'pool_dupr_singles_label': 'DUPR Singles', 'pool_dupr_doubles_label': 'DUPR Doubles',
        'pool_dupr_help': 'Beide DUPR-Werte sind erforderlich. Siehe dupr.com falls du noch keinen Wert hast.',
        'pool_dupr_invalid': 'DUPR muss eine Zahl zwischen 1.0 und 8.0 sein',
        'photo': 'Foto', 'bio': 'Ueber mich', 'language': 'Bevorzugte Sprache',
        'male': 'Maennlich', 'female': 'Weiblich', 'required': 'Pflicht', 'optional': 'optional',
        'select': 'Auswaehlen', 'phone_help': 'Mit Laendervorwahl, z.B. +49 170 1234567',
        'dupr_help': 'Deine DUPR-Wertung falls vorhanden - siehe dupr.com',
        'consent_gdpr': 'Ich stimme der Speicherung und Nutzung meiner Daten fuer WPC/PCL-Kommunikation zu',
        'consent_marketing': 'Ich moechte Turnier-Updates per WhatsApp und E-Mail erhalten',
        'submit': 'Dem Pool beitreten',
        'success_title': 'Willkommen im Pool',
        'success_next': 'Wie es weitergeht',
        'success_n1': 'Kapitaene in deinem Land sehen jetzt dein Profil',
        'success_n2': 'Du wirst ueber kommende Turniere informiert',
        'success_n3': 'Du kannst dein Profil jederzeit mit diesem Link bearbeiten',
        'already_in_pool': 'Du bist bereits im Pool. Hier ist dein Bearbeitungs-Link',
        'back_home': 'Zur Startseite',
        'edit_profile': 'Profil bearbeiten',
        'save': 'Speichern', 'admin_section_title': 'Spieler-Pool',
        'status_new': 'Neu', 'status_contacted': 'Kontaktiert', 'status_interested': 'Interessiert',
        'status_joined_team': 'Team beigetreten', 'status_declined': 'Abgelehnt', 'status_wpc_customer': 'WPC-Kunde',
        'data_note': 'Deine Daten werden sicher gespeichert und nur fuer WPC/PCL-Turnierkommunikation verwendet.',
    },
    'ES': {
        'hero_title': 'Unete al Pool de Jugadores WPC/PCL',
        'hero_sub': 'Un perfil, todos los torneos.',
        'value_1': 'Novedades de torneos por WhatsApp y email',
        'value_2': 'Que los capitanes de tu pais te encuentren',
        'value_3': 'Perfil de jugador permanente para todos los torneos',
        'value_4': 'Acceso anticipado a los proximos torneos',
        'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Email',
        'phone': 'Numero de WhatsApp', 'country': 'Pais', 'age_category': 'Categoria de edad',
        'gender': 'Genero', 'birth_year': 'Ano de nacimiento', 'birth_year_help': '4 digitos, p.ej. 1985', 'dupr': 'Rating DUPR',
        'pool_dupr_singles_label': 'DUPR Singles', 'pool_dupr_doubles_label': 'DUPR Doubles',
        'pool_dupr_help': 'Ambos valores DUPR son obligatorios. Visita dupr.com si aun no tienes uno.',
        'pool_dupr_invalid': 'DUPR debe ser un numero entre 1.0 y 8.0',
        'photo': 'Foto', 'bio': 'Sobre mi', 'language': 'Idioma preferido',
        'male': 'Hombre', 'female': 'Mujer', 'required': 'obligatorio', 'optional': 'opcional',
        'select': 'Seleccionar', 'phone_help': 'Con prefijo, p.ej. +34 600 123 456',
        'dupr_help': 'Tu rating DUPR si lo tienes - ver dupr.com',
        'consent_gdpr': 'Doy mi consentimiento para almacenar y usar mis datos en comunicaciones WPC/PCL',
        'consent_marketing': 'Quiero recibir novedades de torneos por WhatsApp y email',
        'submit': 'Unirme al Pool',
        'success_title': 'Bienvenido al Pool',
        'success_next': 'Que pasa ahora',
        'success_n1': 'Los capitanes de tu pais ya pueden ver tu perfil',
        'success_n2': 'Recibiras avisos sobre los proximos torneos',
        'success_n3': 'Puedes editar tu perfil en cualquier momento con este enlace',
        'already_in_pool': 'Ya estas en el pool. Aqui tienes tu enlace de edicion',
        'back_home': 'Volver al inicio',
        'edit_profile': 'Editar tu perfil',
        'save': 'Guardar', 'admin_section_title': 'Pool de Jugadores',
        'status_new': 'Nuevo', 'status_contacted': 'Contactado', 'status_interested': 'Interesado',
        'status_joined_team': 'En un equipo', 'status_declined': 'Rechazado', 'status_wpc_customer': 'Cliente WPC',
        'data_note': 'Tus datos se almacenan de forma segura y solo se usan para comunicaciones de torneos WPC/PCL.',
    },
    'FR': {
        'hero_title': 'Rejoignez le Pool de Joueurs WPC/PCL',
        'hero_sub': 'Un profil, tous les tournois.',
        'value_1': 'Actualites des tournois par WhatsApp et email',
        'value_2': 'Soyez trouve par les capitaines de votre pays',
        'value_3': 'Profil de joueur permanent pour tous les tournois',
        'value_4': 'Acces anticipe aux prochains tournois',
        'first_name': 'Prenom', 'last_name': 'Nom', 'email': 'Email',
        'phone': 'Numero WhatsApp', 'country': 'Pays', 'age_category': 'Categorie age',
        'gender': 'Genre', 'birth_year': 'Annee de naissance', 'birth_year_help': '4 chiffres, p.ex. 1985', 'dupr': 'Classement DUPR',
        'pool_dupr_singles_label': 'DUPR Singles', 'pool_dupr_doubles_label': 'DUPR Doubles',
        'pool_dupr_help': "Les deux valeurs DUPR sont obligatoires. Voir dupr.com si vous n'avez pas encore de classement.",
        'pool_dupr_invalid': 'DUPR doit etre un nombre entre 1.0 et 8.0',
        'photo': 'Photo', 'bio': 'A propos de moi', 'language': 'Langue preferee',
        'male': 'Homme', 'female': 'Femme', 'required': 'requis', 'optional': 'optionnel',
        'select': 'Choisir', 'phone_help': 'Avec indicatif, p.ex. +33 6 12 34 56 78',
        'dupr_help': 'Votre classement DUPR si vous en avez un - voir dupr.com',
        'consent_gdpr': 'Je consens au stockage et a l usage de mes donnees pour les communications WPC/PCL',
        'consent_marketing': 'Je souhaite recevoir les actualites des tournois par WhatsApp et email',
        'submit': 'Rejoindre le Pool',
        'success_title': 'Bienvenue dans le Pool',
        'success_next': 'Et ensuite',
        'success_n1': 'Les capitaines de votre pays peuvent voir votre profil',
        'success_n2': 'Vous serez informe des prochains tournois',
        'success_n3': 'Vous pouvez modifier votre profil a tout moment avec ce lien',
        'already_in_pool': 'Vous etes deja dans le pool. Voici votre lien de modification',
        'back_home': 'Retour a l accueil',
        'edit_profile': 'Modifier votre profil',
        'save': 'Enregistrer', 'admin_section_title': 'Pool de Joueurs',
        'status_new': 'Nouveau', 'status_contacted': 'Contacte', 'status_interested': 'Interesse',
        'status_joined_team': 'Dans une equipe', 'status_declined': 'Refuse', 'status_wpc_customer': 'Client WPC',
        'data_note': 'Vos donnees sont stockees en securite et utilisees uniquement pour les communications WPC/PCL.',
    },
}


def get_pool_t(lang):
    return POOL_TRANSLATIONS.get((lang or 'EN').upper(), POOL_TRANSLATIONS['EN'])


def _lang():
    lang = request.args.get('lang') or request.form.get('preferred_language') or 'EN'
    lang = lang.upper()
    return lang if lang in POOL_TRANSLATIONS else 'EN'


def status_label(status, lang='EN'):
    return get_pool_t(lang).get('status_' + (status or 'new'), status or 'new')


def make_edit_token(player):
    """Deterministic per-player edit token derived from id + email + app secret.

    Chosen over a DB column so the feature does not depend on an edit_token
    column existing in the migration.
    """
    secret = current_app.config.get('SECRET_KEY', 'pool')
    raw = f"{player.id}:{player.email}:{secret}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:32]


def edit_url(player):
    return url_for('pool.edit_profile', player_id=player.id,
                   edit_token=make_edit_token(player), _external=True)


# ============================================================================
# PUBLIC
# ============================================================================

@pool_bp.route('/pool', methods=['GET', 'POST'])
def register():
    lang = _lang()
    t = get_pool_t(lang)

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        first = (request.form.get('first_name') or '').strip()
        last = (request.form.get('last_name') or '').strip()

        if not (first and last and email):
            flash('Please fill in first name, last name and email.', 'danger')
            return render_template('pool/register.html', t=t, current_lang=lang,
                                   countries=POOL_COUNTRIES, form_data=request.form)

        if not request.form.get('consent_gdpr'):
            flash('Please accept the data consent to continue.', 'danger')
            return render_template('pool/register.html', t=t, current_lang=lang,
                                   countries=POOL_COUNTRIES, form_data=request.form)

        # Duplicate email -> show their edit link instead of creating a second row
        existing = PoolPlayer.query.filter_by(email=email).first()
        if existing:
            return render_template('pool/register_success.html', t=t, current_lang=lang,
                                   player=existing, edit_link=edit_url(existing), already=True)

        # Both DUPR ratings are required and must be valid (1.0-8.0)
        dupr_singles, ds_ok = validate_dupr(request.form.get('dupr_singles'))
        dupr_doubles, dd_ok = validate_dupr(request.form.get('dupr_doubles'))
        if not ds_ok or not dd_ok:
            flash(t['pool_dupr_invalid'], 'danger')
            return render_template('pool/register.html', t=t, current_lang=lang,
                                   countries=POOL_COUNTRIES, form_data=request.form)

        photo_url = None
        if 'photo' in request.files:
            f = request.files['photo']
            if f and f.filename and _allowed_file(f.filename):
                result = upload_photo_to_supabase(f, folder='pool')
                if result.get('success'):
                    photo_url = result['url']
                else:
                    flash('Photo upload failed, your profile was saved without a photo.', 'warning')

        player = PoolPlayer(
            first_name=first, last_name=last, email=email,
            phone=(request.form.get('phone') or '').strip() or None,
            country_name=(request.form.get('country_name') or '').strip() or None,
            age_category=request.form.get('age_category') or None,
            gender=request.form.get('gender') or None,
            birth_year=int(request.form['birth_year']) if request.form.get('birth_year') else None,
            dupr_singles=dupr_singles,
            dupr_doubles=dupr_doubles,
            photo_url=photo_url,
            bio=(request.form.get('bio') or '').strip() or None,
            preferred_language=lang,
            consent_gdpr=True,
            consent_marketing=bool(request.form.get('consent_marketing')),
            status='new',
            source='pool',
        )
        try:
            db.session.add(player)
            db.session.commit()
            return redirect(url_for('pool.register_success', player_id=player.id, lang=lang))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    return render_template('pool/register.html', t=t, current_lang=lang,
                           countries=POOL_COUNTRIES, form_data={})


@pool_bp.route('/pool/success')
def register_success():
    lang = _lang()
    t = get_pool_t(lang)
    player_id = request.args.get('player_id', type=int)
    player = PoolPlayer.query.get_or_404(player_id) if player_id else None
    if not player:
        return redirect(url_for('pool.register', lang=lang))
    return render_template('pool/register_success.html', t=t, current_lang=lang,
                           player=player, edit_link=edit_url(player), already=False)


@pool_bp.route('/pool/profile/<int:player_id>/<edit_token>', methods=['GET', 'POST'])
def edit_profile(player_id, edit_token):
    player = PoolPlayer.query.get_or_404(player_id)
    if edit_token != make_edit_token(player):
        return render_template('pool/register_success.html', t=get_pool_t('EN'),
                               current_lang='EN', player=None, edit_link=None,
                               already=False, invalid=True), 403
    lang = _lang() if request.args.get('lang') else (player.preferred_language or 'EN').upper()
    if lang not in POOL_TRANSLATIONS:
        lang = 'EN'
    t = get_pool_t(lang)

    if request.method == 'POST':
        # Both DUPR ratings are required and must be valid (1.0-8.0)
        dupr_singles, ds_ok = validate_dupr(request.form.get('dupr_singles'))
        dupr_doubles, dd_ok = validate_dupr(request.form.get('dupr_doubles'))
        if not ds_ok or not dd_ok:
            flash(t['pool_dupr_invalid'], 'danger')
            return redirect(url_for('pool.edit_profile', player_id=player.id, edit_token=edit_token, lang=lang))

        player.first_name = (request.form.get('first_name') or '').strip() or player.first_name
        player.last_name = (request.form.get('last_name') or '').strip() or player.last_name
        player.phone = (request.form.get('phone') or '').strip() or player.phone
        player.country_name = (request.form.get('country_name') or '').strip() or player.country_name
        player.age_category = request.form.get('age_category') or player.age_category
        player.gender = request.form.get('gender') or player.gender
        player.birth_year = int(request.form['birth_year']) if request.form.get('birth_year') else player.birth_year
        player.dupr_singles = dupr_singles
        player.dupr_doubles = dupr_doubles
        player.bio = (request.form.get('bio') or '').strip() or player.bio
        player.consent_marketing = bool(request.form.get('consent_marketing'))
        if 'photo' in request.files:
            f = request.files['photo']
            if f and f.filename and _allowed_file(f.filename):
                result = upload_photo_to_supabase(f, folder='pool')
                if result.get('success'):
                    player.photo_url = result['url']
        try:
            db.session.commit()
            flash('Profile updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('pool.edit_profile', player_id=player.id, edit_token=edit_token, lang=lang))

    return render_template('pool/register.html', t=t, current_lang=lang,
                           countries=POOL_COUNTRIES, form_data={}, edit_player=player,
                           edit_token=edit_token)


# ============================================================================
# ADMIN
# ============================================================================

@pool_bp.route('/admin/pool')
def admin_list():
    lang = _lang()
    t = get_pool_t(lang)

    q = PoolPlayer.query
    f_country = request.args.get('country') or ''
    f_age = request.args.get('age_category') or ''
    f_gender = request.args.get('gender') or ''
    f_status = request.args.get('status') or ''
    f_search = (request.args.get('q') or '').strip()

    if f_country:
        q = q.filter(PoolPlayer.country_name == f_country)
    if f_age:
        q = q.filter(PoolPlayer.age_category == f_age)
    if f_gender:
        q = q.filter(PoolPlayer.gender == f_gender)
    if f_status:
        q = q.filter(PoolPlayer.status == f_status)
    if f_search:
        like = f"%{f_search}%"
        q = q.filter(db.or_(PoolPlayer.first_name.ilike(like),
                            PoolPlayer.last_name.ilike(like),
                            PoolPlayer.email.ilike(like)))

    players = q.order_by(PoolPlayer.created_at.desc()).all()

    all_players = PoolPlayer.query.all()
    stats = {
        'total': len(all_players),
        'new': sum(1 for p in all_players if p.status == 'new'),
        'contacted': sum(1 for p in all_players if p.status == 'contacted'),
        'joined': sum(1 for p in all_players if p.status == 'joined_team'),
    }
    countries = sorted({p.country_name for p in all_players if p.country_name})

    return render_template('pool/admin_list.html', t=t, current_lang=lang,
                           players=players, stats=stats, countries=countries,
                           statuses=POOL_STATUSES, status_colors=STATUS_COLORS,
                           filters={'country': f_country, 'age_category': f_age,
                                    'gender': f_gender, 'status': f_status, 'q': f_search})


@pool_bp.route('/admin/pool/<int:player_id>')
def admin_detail(player_id):
    lang = _lang()
    t = get_pool_t(lang)
    player = PoolPlayer.query.get_or_404(player_id)
    wa_msg = quote(f"Hi {player.first_name}, this is Sergio from WPC/PCL. ")
    return render_template('pool/admin_detail.html', t=t, current_lang=lang, player=player,
                           statuses=POOL_STATUSES, status_colors=STATUS_COLORS,
                           edit_link=edit_url(player), wa_msg=wa_msg)


@pool_bp.route('/admin/pool/<int:player_id>/status', methods=['POST'])
def admin_update_status(player_id):
    player = PoolPlayer.query.get_or_404(player_id)
    new_status = request.form.get('status')
    if new_status in POOL_STATUSES:
        player.status = new_status
        if new_status == 'contacted':
            player.last_contacted_at = datetime.utcnow()
        try:
            db.session.commit()
            flash('Status updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return redirect(request.referrer or url_for('pool.admin_detail', player_id=player_id))


@pool_bp.route('/admin/pool/<int:player_id>/notes', methods=['POST'])
def admin_update_notes(player_id):
    player = PoolPlayer.query.get_or_404(player_id)
    player.admin_notes = (request.form.get('admin_notes') or '').strip() or None
    try:
        db.session.commit()
        flash('Notes saved.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('pool.admin_detail', player_id=player_id))


@pool_bp.route('/admin/pool/<int:player_id>/delete', methods=['POST'])
def admin_delete(player_id):
    player = PoolPlayer.query.get_or_404(player_id)
    try:
        db.session.delete(player)
        db.session.commit()
        flash('Pool player deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('pool.admin_list'))
