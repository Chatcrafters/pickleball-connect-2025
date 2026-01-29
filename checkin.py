"""
Tournament Check-in System for Pickleball Connect
Speichere als: checkin.py

Registriere in deiner App:
    from checkin import checkin
    app.register_blueprint(checkin)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from models import db, Event, SHIRT_SIZES
from models import TournamentCheckinSettings, TournamentParticipant, TournamentCheckin, CheckinSyncQueue
from datetime import datetime
import secrets

try:
    import qrcode
    from io import BytesIO
    import base64
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("Warning: qrcode not installed. Run: pip install qrcode[pil]")

try:
    from wallet_pass import generate_pkpass, is_apple_wallet_available
    # Don't cache at import time - check dynamically
    WALLET_PASS_MODULE_AVAILABLE = True
except ImportError as e:
    WALLET_PASS_MODULE_AVAILABLE = False
    is_apple_wallet_available = lambda: False
    print(f"Warning: wallet_pass module not available: {e}")
except Exception as e:
    WALLET_PASS_MODULE_AVAILABLE = False
    is_apple_wallet_available = lambda: False
    print(f"Error loading wallet_pass: {e}")

checkin = Blueprint('checkin', __name__)


# ============================================================================
# CONSTANTS
# ============================================================================

TSHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']

COUNTRY_PHONE_CODES = {
    'Spain': '+34', 'Germany': '+49', 'Italy': '+39', 'France': '+33',
    'Portugal': '+351', 'United Kingdom': '+44', 'United States': '+1',
    'Sweden': '+46', 'Denmark': '+45', 'Netherlands': '+31', 'Belgium': '+32',
    'Austria': '+43', 'Switzerland': '+41', 'Poland': '+48', 'Hungary': '+36',
    'Slovakia': '+421', 'Serbia': '+381', 'Latvia': '+371', 'Malta': '+356',
    'Ireland': '+353', 'Canada': '+1', 'Argentina': '+54', 'Brazil': '+55',
    'Thailand': '+66',
}

TRANSLATIONS = {
    'en': {
        'page_title': 'Tournament Check-in',
        'welcome': 'Welcome',
        'checkin_title': 'Complete Your Check-in',
        'emergency_contact': 'Emergency Contact',
        'emergency_name': 'Contact Name',
        'emergency_phone': 'Contact Phone',
        'emergency_help': 'Person to contact in case of emergency',
        'date_of_birth': 'Date of Birth',
        'phone': 'Your Phone Number',
        'phone_help': 'With country code (e.g., +34 612 345 678)',
        'whatsapp_optin': 'I agree to receive tournament updates via WhatsApp',
        'tshirt_size': 'T-Shirt Size',
        'liability': 'Liability Waiver',
        'submit': 'Complete Check-in',
        'success_title': 'Check-in Complete!',
        'success_message': 'Please proceed to the welcome pack station.',
        'show_confirmation': 'Show this screen to receive your welcome pack',
        'already_checked_in': 'You have already checked in',
    },
    'de': {
        'page_title': 'Turnier Check-in',
        'welcome': 'Willkommen',
        'checkin_title': 'Check-in abschließen',
        'emergency_contact': 'Notfallkontakt',
        'emergency_name': 'Name des Kontakts',
        'emergency_phone': 'Telefonnummer',
        'emergency_help': 'Person für Notfall',
        'date_of_birth': 'Geburtsdatum',
        'phone': 'Ihre Telefonnummer',
        'phone_help': 'Mit Ländervorwahl (z.B. +49 170 1234567)',
        'whatsapp_optin': 'Turnier-Updates per WhatsApp erhalten',
        'tshirt_size': 'T-Shirt Größe',
        'liability': 'Haftungsausschluss',
        'submit': 'Check-in abschließen',
        'success_title': 'Check-in abgeschlossen!',
        'success_message': 'Bitte gehen Sie zur Welcome Pack Station.',
        'show_confirmation': 'Zeigen Sie diesen Bildschirm für Ihr Welcome Pack',
        'already_checked_in': 'Sie haben bereits eingecheckt',
    },
    'es': {
        'page_title': 'Check-in del Torneo',
        'welcome': 'Bienvenido',
        'checkin_title': 'Completa tu Check-in',
        'emergency_contact': 'Contacto de Emergencia',
        'emergency_name': 'Nombre del Contacto',
        'emergency_phone': 'Teléfono del Contacto',
        'emergency_help': 'Persona para emergencias',
        'date_of_birth': 'Fecha de Nacimiento',
        'phone': 'Tu Número de Teléfono',
        'phone_help': 'Con código de país (ej. +34 612 345 678)',
        'whatsapp_optin': 'Recibir actualizaciones por WhatsApp',
        'tshirt_size': 'Talla de Camiseta',
        'liability': 'Exención de Responsabilidad',
        'submit': 'Completar Check-in',
        'success_title': '¡Check-in Completado!',
        'success_message': 'Dirígete a la estación de welcome pack.',
        'show_confirmation': 'Muestra esta pantalla para tu welcome pack',
        'already_checked_in': 'Ya has completado el check-in',
    },
    'fr': {
        'page_title': 'Check-in du Tournoi',
        'welcome': 'Bienvenue',
        'checkin_title': 'Complétez votre Check-in',
        'emergency_contact': "Contact d'Urgence",
        'emergency_name': 'Nom du Contact',
        'emergency_phone': 'Téléphone',
        'emergency_help': "Personne pour urgences",
        'date_of_birth': 'Date de Naissance',
        'phone': 'Votre Numéro',
        'phone_help': 'Avec indicatif (ex. +33 6 12 34 56 78)',
        'whatsapp_optin': 'Recevoir les mises à jour par WhatsApp',
        'tshirt_size': 'Taille de T-Shirt',
        'liability': 'Décharge de Responsabilité',
        'submit': 'Terminer le Check-in',
        'success_title': 'Check-in Terminé!',
        'success_message': 'Rendez-vous au stand welcome pack.',
        'show_confirmation': 'Montrez cet écran pour votre welcome pack',
        'already_checked_in': 'Check-in déjà effectué',
    }
}

DEFAULT_LIABILITY_WAIVERS = {
    "en": {
        "version": "2025-v1",
        "title": "Liability Waiver & Health Declaration",
        "text": """I hereby declare that:

1. Physical Fitness: I am physically fit to participate in this pickleball tournament and have no medical conditions that would prevent safe participation.

2. Assumption of Risk: I understand that pickleball involves physical activity and carries inherent risks of injury. I voluntarily assume all risks associated with my participation.

3. Liability Release: I release the tournament organizers, venue, sponsors from any claims arising from my participation, except in cases of gross negligence.

4. Medical Authorization: In case of emergency, I authorize the organizers to seek medical treatment on my behalf.

5. Accurate Information: I confirm that all information provided is accurate and complete.""",
        "checkbox_label": "I accept the liability waiver and health declaration"
    },
    "de": {
        "version": "2025-v1",
        "title": "Haftungsausschluss & Gesundheitserklärung",
        "text": """Hiermit erkläre ich:

1. Körperliche Fitness: Ich bin körperlich in der Lage, an diesem Pickleball-Turnier teilzunehmen und habe keine gesundheitlichen Einschränkungen.

2. Risikoübernahme: Mir ist bewusst, dass Pickleball Verletzungsrisiken birgt. Ich übernehme freiwillig alle Risiken.

3. Haftungsfreistellung: Ich stelle die Veranstalter von allen Ansprüchen frei, ausgenommen bei grober Fahrlässigkeit.

4. Medizinische Vollmacht: Im Notfall ermächtige ich die Veranstalter, medizinische Behandlung zu veranlassen.

5. Richtige Angaben: Ich bestätige, dass alle Angaben korrekt und vollständig sind.""",
        "checkbox_label": "Ich akzeptiere den Haftungsausschluss"
    },
    "es": {
        "version": "2025-v1",
        "title": "Exención de Responsabilidad y Declaración de Salud",
        "text": """Por la presente declaro que:

1. Aptitud Física: Estoy físicamente apto/a para participar en este torneo de pickleball y no tengo condiciones médicas que lo impidan.

2. Asunción de Riesgos: Entiendo que el pickleball conlleva riesgos de lesión. Asumo voluntariamente todos los riesgos.

3. Liberación de Responsabilidad: Libero a los organizadores de cualquier reclamación, excepto en casos de negligencia grave.

4. Autorización Médica: En caso de emergencia, autorizo a los organizadores a buscar tratamiento médico.

5. Información Veraz: Confirmo que toda la información proporcionada es precisa y completa.""",
        "checkbox_label": "Acepto la exención de responsabilidad"
    },
    "fr": {
        "version": "2025-v1",
        "title": "Décharge de Responsabilité et Déclaration de Santé",
        "text": """Je déclare par la présente que:

1. Condition Physique: Je suis physiquement apte à participer à ce tournoi de pickleball et n'ai aucune condition médicale l'empêchant.

2. Acceptation des Risques: Je comprends que le pickleball comporte des risques de blessure. J'assume volontairement tous les risques.

3. Décharge de Responsabilité: Je dégage les organisateurs de toute réclamation, sauf en cas de négligence grave.

4. Autorisation Médicale: En cas d'urgence, j'autorise les organisateurs à faire appel à des soins médicaux.

5. Informations Exactes: Je confirme que toutes les informations fournies sont exactes.""",
        "checkbox_label": "J'accepte la décharge de responsabilité"
    }
}


# ============================================================================
# CSV PARSER FOR PICKLEBALL GLOBAL
# ============================================================================

def parse_pickleball_global_csv(csv_content, tournament_id):
    """Parse Pickleball Global CSV/TSV format"""
    participants = []
    current_country = None
    
    for line in csv_content.strip().split('\n'):
        if not line.strip():
            continue
        
        parts = [p.strip() for p in line.split('\t')]
        
        if parts[0] in ['COUNTRY', 'All Registered Players', 'TOTAL']:
            continue
        
        if len(parts) >= 3 and parts[-1] == 'VIEW':
            current_country = parts[0].strip()
            continue
        
        if len(parts) >= 3 and current_country:
            name_parts = parts[1].strip().split(' ', 1)
            first_name = name_parts[0].title() if name_parts else ''
            last_name = name_parts[1].title() if len(name_parts) > 1 else ''
            
            if first_name:
                participants.append({
                    'tournament_id': tournament_id,
                    'external_id': parts[0],
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': parts[2].strip() if len(parts) > 2 and parts[2] else None,
                    'country': current_country,
                })
    
    return participants


def import_participants_from_csv(csv_content, tournament_id):
    """Import participants, returns (imported, skipped, errors)"""
    participants = parse_pickleball_global_csv(csv_content, tournament_id)
    imported, skipped, errors = 0, 0, []
    
    for p_data in participants:
        try:
            existing = TournamentParticipant.query.filter_by(
                tournament_id=tournament_id,
                external_id=p_data['external_id']
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            participant = TournamentParticipant(**p_data)
            participant.generate_checkin_token()
            db.session.add(participant)
            imported += 1
            
        except Exception as e:
            errors.append(f"Error: {p_data.get('first_name', '?')}: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        errors.append(f"Database error: {str(e)}")
        return 0, 0, errors
    
    return imported, skipped, errors


# ============================================================================
# QR CODE GENERATION
# ============================================================================

def generate_qr_code(url, size=8):
    """Generate QR code as base64"""
    if not QR_AVAILABLE:
        return None
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=size, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@checkin.route('/admin/tournament/<int:tournament_id>/checkin')
def admin_checkin_dashboard(tournament_id):
    """Admin dashboard for check-in management"""
    tournament = Event.query.get_or_404(tournament_id)
    settings = TournamentCheckinSettings.query.filter_by(tournament_id=tournament_id).first()
    participants = TournamentParticipant.query.filter_by(tournament_id=tournament_id).all()
    
    total = len(participants)
    checked_in = sum(1 for p in participants if p.is_checked_in)
    packs_given = TournamentCheckin.query.filter_by(tournament_id=tournament_id, welcome_pack_received=True).count()
    
    by_country = {}
    for p in participants:
        country = p.country or 'Unknown'
        if country not in by_country:
            by_country[country] = {'total': 0, 'checked_in': 0}
        by_country[country]['total'] += 1
        if p.is_checked_in:
            by_country[country]['checked_in'] += 1
    
    return render_template('checkin_admin_dashboard.html',
        tournament=tournament, settings=settings, participants=participants,
        stats={'total': total, 'checked_in': checked_in, 'pending': total - checked_in,
               'packs_given': packs_given, 'by_country': by_country})


@checkin.route('/admin/tournament/<int:tournament_id>/checkin/import', methods=['GET', 'POST'])
def admin_import_participants(tournament_id):
    """Import participants from CSV"""
    tournament = Event.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        try:
            csv_content = file.read().decode('utf-8')
            imported, skipped, errors = import_participants_from_csv(csv_content, tournament_id)
            
            for error in errors[:5]:
                flash(error, 'warning')
            
            flash(f'Imported {imported} participants. Skipped {skipped} duplicates.', 'success')
            return redirect(url_for('checkin.admin_checkin_dashboard', tournament_id=tournament_id))
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('checkin_import.html', tournament=tournament)


@checkin.route('/admin/tournament/<int:tournament_id>/checkin/settings', methods=['GET', 'POST'])
def admin_checkin_settings(tournament_id):
    """Configure check-in settings"""
    tournament = Event.query.get_or_404(tournament_id)
    settings = TournamentCheckinSettings.query.filter_by(tournament_id=tournament_id).first()
    
    if request.method == 'POST':
        if not settings:
            settings = TournamentCheckinSettings(tournament_id=tournament_id)
        
        settings.liability_waiver_text = request.form.get('liability_waiver_text', '')
        settings.liability_waiver_lang = request.form.get('liability_waiver_lang', 'en')
        settings.liability_waiver_version = request.form.get('liability_waiver_version', 'v1')
        settings.checkin_open = 'checkin_open' in request.form
        
        db.session.add(settings)
        db.session.commit()
        flash('Settings saved', 'success')
        return redirect(url_for('checkin.admin_checkin_dashboard', tournament_id=tournament_id))
    
    return render_template('checkin_settings.html',
        tournament=tournament, settings=settings, default_waivers=DEFAULT_LIABILITY_WAIVERS)


@checkin.route('/admin/tournament/<int:tournament_id>/checkin/qrcodes')
def admin_generate_qrcodes(tournament_id):
    """Generate all QR codes for printing"""
    tournament = Event.query.get_or_404(tournament_id)
    participants = TournamentParticipant.query.filter_by(tournament_id=tournament_id).order_by(
        TournamentParticipant.country, TournamentParticipant.last_name).all()
    
    base_url = request.host_url.rstrip('/')
    qr_data = []
    
    for p in participants:
        url = p.get_checkin_url(base_url)
        qr_data.append({
            'participant': p,
            'url': url,
            'qr_image': generate_qr_code(url, size=5)
        })
    
    return render_template('checkin_qrcodes.html', tournament=tournament, qr_data=qr_data)


# ============================================================================
# STAFF STATION
# ============================================================================

@checkin.route('/staff/tournament/<int:tournament_id>/checkin')
def staff_checkin_station(tournament_id):
    """Staff check-in station (offline capable)"""
    tournament = Event.query.get_or_404(tournament_id)
    return render_template('checkin_staff_station.html',
        tournament=tournament, tshirt_sizes=TSHIRT_SIZES, default_waivers=DEFAULT_LIABILITY_WAIVERS)


# ============================================================================
# SELF-SERVICE CHECK-IN
# ============================================================================

@checkin.route('/checkin/self/<token>', methods=['GET', 'POST'])
def self_checkin(token):
    """Self-service check-in page"""
    participant = TournamentParticipant.query.filter_by(checkin_token=token).first_or_404()
    tournament = participant.tournament
    settings = TournamentCheckinSettings.query.filter_by(tournament_id=tournament.id).first()
    existing = TournamentCheckin.query.filter_by(participant_id=participant.id).first()
    
    lang = request.args.get('lang', 'en').lower()
    if lang not in TRANSLATIONS:
        lang = 'en'
    t = TRANSLATIONS[lang]
    
    waiver = DEFAULT_LIABILITY_WAIVERS.get(lang, DEFAULT_LIABILITY_WAIVERS['en'])
    if settings and settings.liability_waiver_text:
        waiver = {**waiver, 'text': settings.liability_waiver_text, 'version': settings.liability_waiver_version}
    
    if existing:
        return render_template('checkin_already_done.html',
            participant=participant, tournament=tournament, checkin=existing, t=t, lang=lang)
    
    if request.method == 'POST':
        try:
            dob = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
            
            checkin_record = TournamentCheckin(
                tournament_id=tournament.id,
                participant_id=participant.id,
                emergency_contact_name=request.form.get('emergency_contact_name'),
                emergency_contact_phone=request.form.get('emergency_contact_phone'),
                date_of_birth=dob,
                liability_accepted='liability_accepted' in request.form,
                liability_accepted_at=datetime.utcnow() if 'liability_accepted' in request.form else None,
                liability_waiver_version=waiver.get('version', 'v1'),
                phone_number=request.form.get('phone_number'),
                whatsapp_optin='whatsapp_optin' in request.form,
                preferred_language=lang,
                tshirt_size=request.form.get('tshirt_size'),
                checked_in_by='self',
                checkin_method='qr_self'
            )
            
            db.session.add(checkin_record)
            db.session.commit()

            # Redirect to wallet pass
            return redirect(url_for('checkin.wallet_pass', token=token))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('checkin_self_form.html',
        participant=participant, tournament=tournament, settings=settings, waiver=waiver,
        t=t, lang=lang, tshirt_sizes=TSHIRT_SIZES,
        country_phone_code=COUNTRY_PHONE_CODES.get(participant.country, ''))


@checkin.route('/checkin/wallet/<token>')
def wallet_pass(token):
    """Mobile wallet-style check-in pass"""
    participant = TournamentParticipant.query.filter_by(checkin_token=token).first_or_404()
    tournament = participant.tournament
    checkin_record = TournamentCheckin.query.filter_by(participant_id=participant.id).first()

    if not checkin_record:
        # Not checked in yet, redirect to check-in form
        return redirect(url_for('checkin.self_checkin', token=token))

    # Generate QR code for the wallet pass URL
    base_url = request.host_url.rstrip('/')
    wallet_url = f"{base_url}/checkin/wallet/{token}"
    qr_image = generate_qr_code(wallet_url, size=6)

    # Country flags mapping
    country_flags = {
        'Germany': '🇩🇪', 'Spain': '🇪🇸', 'France': '🇫🇷', 'Italy': '🇮🇹',
        'Portugal': '🇵🇹', 'United Kingdom': '🇬🇧', 'Netherlands': '🇳🇱',
        'Belgium': '🇧🇪', 'Austria': '🇦🇹', 'Switzerland': '🇨🇭',
        'Sweden': '🇸🇪', 'Denmark': '🇩🇰', 'Norway': '🇳🇴', 'Finland': '🇫🇮',
        'Poland': '🇵🇱', 'Czech Republic': '🇨🇿', 'Hungary': '🇭🇺',
        'United States': '🇺🇸', 'Canada': '🇨🇦', 'Mexico': '🇲🇽',
        'Argentina': '🇦🇷', 'Brazil': '🇧🇷', 'Thailand': '🇹🇭',
        'Ireland': '🇮🇪', 'Slovakia': '🇸🇰', 'Serbia': '🇷🇸',
        'Latvia': '🇱🇻', 'Malta': '🇲🇹', 'Greece': '🇬🇷',
    }

    return render_template('checkin_wallet_pass.html',
        participant=participant,
        tournament=tournament,
        checkin=checkin_record,
        qr_image=qr_image,
        country_flags=country_flags,
        apple_wallet_available=is_apple_wallet_available())


@checkin.route('/checkin/wallet/<token>/apple')
def apple_wallet_pass(token):
    """Generate and download Apple Wallet .pkpass file"""
    if not is_apple_wallet_available():
        flash('Apple Wallet is not configured', 'error')
        return redirect(url_for('checkin.wallet_pass', token=token))

    participant = TournamentParticipant.query.filter_by(checkin_token=token).first_or_404()
    tournament = participant.tournament
    checkin_record = TournamentCheckin.query.filter_by(participant_id=participant.id).first()

    if not checkin_record:
        return redirect(url_for('checkin.self_checkin', token=token))

    try:
        # Generate the .pkpass file
        pkpass_buffer = generate_pkpass(participant, tournament, checkin_record)

        # Send the file
        filename = f"WPC_{participant.first_name}_{participant.last_name}.pkpass"
        return send_file(
            pkpass_buffer,
            mimetype='application/vnd.apple.pkpass',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Error generating pass: {str(e)}', 'error')
        return redirect(url_for('checkin.wallet_pass', token=token))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@checkin.route('/api/debug/apple-wallet')
def api_debug_apple_wallet():
    """Debug endpoint to check Apple Wallet configuration"""
    import os

    # Direct env var check
    cert_val = os.environ.get('APPLE_PASS_CERT')
    key_val = os.environ.get('APPLE_PASS_KEY')

    return jsonify({
        'APPLE_WALLET_AVAILABLE': is_apple_wallet_available(),
        'wallet_pass_module_available': WALLET_PASS_MODULE_AVAILABLE,
        'env_vars': {
            'APPLE_PASS_CERT': bool(cert_val),
            'APPLE_PASS_KEY': bool(key_val),
            'APPLE_WWDR_CERT': bool(os.environ.get('APPLE_WWDR_CERT')),
        },
        'lengths': {
            'cert': len(cert_val) if cert_val else 0,
            'key': len(key_val) if key_val else 0,
        }
    })


@checkin.route('/api/tournament/<int:tournament_id>/checkin/init')
def api_checkin_init(tournament_id):
    """Initialize offline data"""
    tournament = Event.query.get_or_404(tournament_id)
    settings = TournamentCheckinSettings.query.filter_by(tournament_id=tournament_id).first()
    participants = TournamentParticipant.query.filter_by(tournament_id=tournament_id).all()
    checkins = {c.participant_id: c for c in TournamentCheckin.query.filter_by(tournament_id=tournament_id).all()}
    
    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'location': tournament.location},
        'settings': {'checkin_open': settings.checkin_open if settings else False,
                    'liability_waiver_text': settings.liability_waiver_text if settings else None} if settings else None,
        'participants': [{
            'id': p.id, 'external_id': p.external_id, 'first_name': p.first_name, 'last_name': p.last_name,
            'email': p.email, 'country': p.country, 'checkin_token': p.checkin_token,
            'is_checked_in': p.id in checkins,
            'checkin_data': {'tshirt_size': checkins[p.id].tshirt_size,
                            'welcome_pack_received': checkins[p.id].welcome_pack_received} if p.id in checkins else None
        } for p in participants],
        'default_waivers': DEFAULT_LIABILITY_WAIVERS,
        'tshirt_sizes': TSHIRT_SIZES,
        'generated_at': datetime.utcnow().isoformat()
    })


@checkin.route('/api/tournament/<int:tournament_id>/checkin', methods=['POST'])
def api_create_checkin(tournament_id):
    """Create check-in via API"""
    data = request.get_json()
    participant = TournamentParticipant.query.get_or_404(data.get('participant_id'))
    
    existing = TournamentCheckin.query.filter_by(participant_id=participant.id).first()
    if existing:
        return jsonify({'error': 'Already checked in'}), 409
    
    try:
        dob = datetime.strptime(data.get('date_of_birth'), '%Y-%m-%d').date() if data.get('date_of_birth') else None
        
        checkin_record = TournamentCheckin(
            tournament_id=tournament_id,
            participant_id=participant.id,
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            date_of_birth=dob,
            liability_accepted=data.get('liability_accepted', False),
            liability_accepted_at=datetime.utcnow() if data.get('liability_accepted') else None,
            phone_number=data.get('phone_number'),
            whatsapp_optin=data.get('whatsapp_optin', False),
            preferred_language=data.get('preferred_language', 'en'),
            tshirt_size=data.get('tshirt_size'),
            checked_in_by=data.get('checked_in_by', 'staff'),
            checkin_method=data.get('checkin_method', 'staff_station'),
            device_id=data.get('device_id')
        )
        
        db.session.add(checkin_record)
        db.session.commit()
        
        return jsonify({'success': True, 'checkin_id': checkin_record.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@checkin.route('/api/tournament/<int:tournament_id>/checkin/sync', methods=['POST'])
def api_sync_checkins(tournament_id):
    """Sync offline check-ins"""
    data = request.get_json()
    results = []
    
    for checkin_data in data.get('checkins', []):
        try:
            existing = TournamentCheckin.query.filter_by(participant_id=checkin_data.get('participant_id')).first()
            if existing:
                results.append({'participant_id': checkin_data.get('participant_id'), 'status': 'skipped'})
                continue
            
            dob = datetime.strptime(checkin_data.get('date_of_birth'), '%Y-%m-%d').date() if checkin_data.get('date_of_birth') else None
            
            checkin_record = TournamentCheckin(
                tournament_id=tournament_id,
                participant_id=checkin_data.get('participant_id'),
                emergency_contact_name=checkin_data.get('emergency_contact_name'),
                emergency_contact_phone=checkin_data.get('emergency_contact_phone'),
                date_of_birth=dob,
                liability_accepted=checkin_data.get('liability_accepted', False),
                phone_number=checkin_data.get('phone_number'),
                whatsapp_optin=checkin_data.get('whatsapp_optin', False),
                tshirt_size=checkin_data.get('tshirt_size'),
                checked_in_by='staff_offline',
                checkin_method='staff_station_offline',
                device_id=data.get('device_id'),
                synced_to_server=True,
                synced_at=datetime.utcnow()
            )
            
            db.session.add(checkin_record)
            results.append({'participant_id': checkin_data.get('participant_id'), 'status': 'synced'})
            
        except Exception as e:
            results.append({'participant_id': checkin_data.get('participant_id'), 'status': 'error', 'error': str(e)})
    
    db.session.commit()
    return jsonify({'success': True, 'results': results})


@checkin.route('/api/tournament/<int:tournament_id>/checkin/<int:checkin_id>/pack', methods=['POST'])
def api_mark_pack_received(tournament_id, checkin_id):
    """Mark welcome pack as received"""
    checkin_record = TournamentCheckin.query.get_or_404(checkin_id)
    
    checkin_record.welcome_pack_received = True
    checkin_record.welcome_pack_received_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})


@checkin.route('/api/tournament/<int:tournament_id>/checkin/status')
def api_checkin_status(tournament_id):
    """Get check-in statistics"""
    total = TournamentParticipant.query.filter_by(tournament_id=tournament_id).count()
    checked_in = TournamentCheckin.query.filter_by(tournament_id=tournament_id).count()
    packs_given = TournamentCheckin.query.filter_by(tournament_id=tournament_id, welcome_pack_received=True).count()
    
    return jsonify({
        'total': total, 'checked_in': checked_in, 'pending': total - checked_in,
        'packs_given': packs_given, 'updated_at': datetime.utcnow().isoformat()
    })
