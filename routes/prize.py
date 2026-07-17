# -*- coding: utf-8 -*-
"""Prize money payouts for WPC Italy - Alba 2026 (blueprint 'prize').

Three surfaces:
  * /prize/<token>    player fills in bank + tax details (no amount shown)
  * /prize/partner    payout list for the accounting partner (own access code)
  * /prize/admin      internal status overview (app login)

Flat 20% withholding tax; net = gross - tax.
The player form is translated (DE/EN/ES/FR/IT); the partner view is
English-only, as the accounting partner works in English.
Translations are ASCII-only, matching the convention in routes/pool.py.
"""
import hmac
import os
import re
import time
from datetime import datetime
from decimal import Decimal
from functools import wraps
from io import BytesIO
from urllib.parse import quote

from flask import (Blueprint, render_template, request, redirect, url_for,
                   abort, session, send_file, current_app)

from models import db, PrizePayment
from routes.auth import login_required

prize = Blueprint('prize', __name__, url_prefix='/prize')

TOURNAMENT_NAME = 'WPC Alba 2026'
TOTAL_PLAYERS = 27

LANGUAGES = ['DE', 'EN', 'ES', 'FR', 'IT']

# Countries offered in the address / tax dropdowns.
PRIZE_COUNTRIES = [
    'Spain', 'Italy', 'Germany', 'France', 'United Kingdom', 'Portugal',
    'Netherlands', 'Belgium', 'Austria', 'Switzerland', 'Ireland', 'Poland',
    'Sweden', 'Norway', 'Denmark', 'Finland', 'Czech Republic', 'Greece',
    'Hungary', 'Romania', 'Slovakia', 'Slovenia', 'Croatia', 'Bulgaria',
    'Estonia', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Cyprus',
    'Turkey', 'United States', 'Canada', 'Australia', 'Other',
]


# ---- Translations (ASCII-only) ---------------------------------------------
TRANSLATIONS = {
    'DE': {
        'form_title': 'Preisgeld - Auszahlungsdaten',
        'form_intro': 'Damit wir dein Preisgeld ueberweisen koennen, brauchen wir noch deine Bank- und Steuerdaten.',
        'player': 'Spieler', 'results': 'Ergebnisse',
        'sec_personal': 'Persoenliche Daten', 'sec_bank': 'Bankverbindung',
        'birth_date': 'Geburtsdatum',
        'address_street': 'Strasse und Hausnummer',
        'address_zip_city': 'PLZ und Ort',
        'address_country': 'Land',
        'tax_country': 'Steuerliches Ansaessigkeitsland',
        'tax_id': 'Steuernummer / Steuer-ID',
        'account_holder': 'Kontoinhaber',
        'account_holder_help': 'Genau wie bei der Bank hinterlegt',
        'iban': 'IBAN', 'iban_help': 'Leerzeichen werden automatisch entfernt',
        'bic': 'BIC / SWIFT', 'bank_name': 'Name der Bank',
        'acct_type': 'Art des Bankkontos',
        'acct_sepa': 'Bankkonto in Europa (IBAN)',
        'acct_other': 'Bankkonto ausserhalb Europas (z.B. USA)',
        'account_number': 'Kontonummer (Account Number)',
        'routing_number': 'Routing Number / ABA',
        'routing_help': 'Nur bei US-Konten erforderlich',
        'swift': 'SWIFT / BIC',
        'bank_address': 'Adresse der Bank',
        'bank_address_help': 'Strasse, Ort und Land der Bank',
        'other_note': 'Fuer Auslandsueberweisungen benoetigen wir zusaetzlich die vollstaendige Adresse deiner Bank.',
        'select': 'Bitte waehlen',
        'submit': 'Daten absenden', 'save_changes': 'Aenderungen speichern',
        'iban_valid': 'IBAN gueltig', 'iban_invalid': 'IBAN ungueltig - bitte pruefen',
        'err_required': 'Bitte fuelle alle Felder aus.',
        'err_iban': 'Die IBAN ist ungueltig. Bitte pruefe deine Eingabe.',
        'err_birth_date': 'Bitte gib ein gueltiges Geburtsdatum an.',
        'success_title': 'Vielen Dank!',
        'success_msg': 'Wir haben deine Daten erhalten. Das Preisgeld wird in den naechsten Tagen ueberwiesen.',
        'success_edit': 'Solange die Zahlung noch nicht ausgefuehrt ist, kannst du deine Daten ueber denselben Link korrigieren.',
        'edit_hint': 'Deine Daten sind gespeichert. Du kannst sie hier noch korrigieren.',
        'locked_title': 'Zahlung ausgefuehrt',
        'locked_msg': 'Dein Preisgeld wurde bereits ueberwiesen. Deine Daten koennen daher nicht mehr geaendert werden. Bei Fragen melde dich bitte direkt bei uns.',
        'privacy_note': 'Deine Daten werden ausschliesslich fuer die Auszahlung des Preisgeldes verwendet.',
        'wa_message': ('Hallo {first_name}, herzlichen Glueckwunsch nochmals zu deinem Podiumsplatz beim WPC Italy '
                       'in Alba! Fuer die Ueberweisung deines Preisgeldes fuelle bitte kurz dieses Formular aus: '
                       '{link} Vielen Dank! Sergio - World Pickleball Connect'),
    },
    'EN': {
        'form_title': 'Prize Money - Payment Details',
        'form_intro': 'To transfer your prize money we still need your bank and tax details.',
        'player': 'Player', 'results': 'Results',
        'sec_personal': 'Personal details', 'sec_bank': 'Bank details',
        'birth_date': 'Date of birth',
        'address_street': 'Street and number',
        'address_zip_city': 'ZIP code and city',
        'address_country': 'Country',
        'tax_country': 'Country of tax residence',
        'tax_id': 'Tax number / Tax ID',
        'account_holder': 'Account holder',
        'account_holder_help': 'Exactly as registered with your bank',
        'iban': 'IBAN', 'iban_help': 'Spaces are removed automatically',
        'bic': 'BIC / SWIFT', 'bank_name': 'Bank name',
        'acct_type': 'Type of bank account',
        'acct_sepa': 'Bank account in Europe (IBAN)',
        'acct_other': 'Bank account outside Europe (e.g. USA)',
        'account_number': 'Account number',
        'routing_number': 'Routing number / ABA',
        'routing_help': 'Only required for US accounts',
        'swift': 'SWIFT / BIC',
        'bank_address': 'Bank address',
        'bank_address_help': 'Street, city and country of your bank',
        'other_note': 'For international transfers we also need the full address of your bank.',
        'select': 'Please select',
        'submit': 'Submit details', 'save_changes': 'Save changes',
        'iban_valid': 'IBAN valid', 'iban_invalid': 'IBAN invalid - please check',
        'err_required': 'Please fill in all fields.',
        'err_iban': 'The IBAN is invalid. Please check your input.',
        'err_birth_date': 'Please enter a valid date of birth.',
        'success_title': 'Thank you!',
        'success_msg': 'We have received your details. Your prize money will be transferred within the next few days.',
        'success_edit': 'As long as the payment has not been made you can correct your details via the same link.',
        'edit_hint': 'Your details are saved. You can still correct them here.',
        'locked_title': 'Payment completed',
        'locked_msg': 'Your prize money has already been transferred, so your details can no longer be changed. Please contact us directly if you have any questions.',
        'privacy_note': 'Your data is used solely to pay out your prize money.',
        'wa_message': ('Hi {first_name}, congratulations again on your podium finish at WPC Italy in Alba! '
                       'To transfer your prize money, please fill in this short form: {link} '
                       'Thank you! Sergio - World Pickleball Connect'),
    },
    'ES': {
        'form_title': 'Premio - Datos de pago',
        'form_intro': 'Para transferir tu premio necesitamos todavia tus datos bancarios y fiscales.',
        'player': 'Jugador', 'results': 'Resultados',
        'sec_personal': 'Datos personales', 'sec_bank': 'Datos bancarios',
        'birth_date': 'Fecha de nacimiento',
        'address_street': 'Calle y numero',
        'address_zip_city': 'Codigo postal y ciudad',
        'address_country': 'Pais',
        'tax_country': 'Pais de residencia fiscal',
        'tax_id': 'Numero fiscal / NIF',
        'account_holder': 'Titular de la cuenta',
        'account_holder_help': 'Exactamente como figura en tu banco',
        'iban': 'IBAN', 'iban_help': 'Los espacios se eliminan automaticamente',
        'bic': 'BIC / SWIFT', 'bank_name': 'Nombre del banco',
        'acct_type': 'Tipo de cuenta bancaria',
        'acct_sepa': 'Cuenta bancaria en Europa (IBAN)',
        'acct_other': 'Cuenta bancaria fuera de Europa (p.ej. EEUU)',
        'account_number': 'Numero de cuenta',
        'routing_number': 'Routing number / ABA',
        'routing_help': 'Solo necesario para cuentas de EEUU',
        'swift': 'SWIFT / BIC',
        'bank_address': 'Direccion del banco',
        'bank_address_help': 'Calle, ciudad y pais de tu banco',
        'other_note': 'Para transferencias internacionales necesitamos ademas la direccion completa de tu banco.',
        'select': 'Selecciona',
        'submit': 'Enviar datos', 'save_changes': 'Guardar cambios',
        'iban_valid': 'IBAN valido', 'iban_invalid': 'IBAN no valido - revisalo',
        'err_required': 'Por favor rellena todos los campos.',
        'err_iban': 'El IBAN no es valido. Por favor revisa tu entrada.',
        'err_birth_date': 'Por favor introduce una fecha de nacimiento valida.',
        'success_title': 'Muchas gracias!',
        'success_msg': 'Hemos recibido tus datos. Tu premio se transferira en los proximos dias.',
        'success_edit': 'Mientras el pago no se haya realizado puedes corregir tus datos con el mismo enlace.',
        'edit_hint': 'Tus datos estan guardados. Todavia puedes corregirlos aqui.',
        'locked_title': 'Pago realizado',
        'locked_msg': 'Tu premio ya ha sido transferido, por lo que tus datos ya no se pueden modificar. Si tienes alguna pregunta contacta con nosotros directamente.',
        'privacy_note': 'Tus datos se utilizan unicamente para el pago del premio.',
        'wa_message': ('Hola {first_name}, felicidades de nuevo por tu podio en el WPC Italy en Alba! '
                       'Para transferir tu premio, rellena por favor este breve formulario: {link} '
                       'Muchas gracias! Sergio - World Pickleball Connect'),
    },
    'FR': {
        'form_title': 'Prix - Donnees de paiement',
        'form_intro': 'Pour virer ton prix nous avons encore besoin de tes coordonnees bancaires et fiscales.',
        'player': 'Joueur', 'results': 'Resultats',
        'sec_personal': 'Donnees personnelles', 'sec_bank': 'Coordonnees bancaires',
        'birth_date': 'Date de naissance',
        'address_street': 'Rue et numero',
        'address_zip_city': 'Code postal et ville',
        'address_country': 'Pays',
        'tax_country': 'Pays de residence fiscale',
        'tax_id': 'Numero fiscal / Identifiant fiscal',
        'account_holder': 'Titulaire du compte',
        'account_holder_help': 'Exactement comme enregistre a ta banque',
        'iban': 'IBAN', 'iban_help': 'Les espaces sont supprimes automatiquement',
        'bic': 'BIC / SWIFT', 'bank_name': 'Nom de la banque',
        'acct_type': 'Type de compte bancaire',
        'acct_sepa': 'Compte bancaire en Europe (IBAN)',
        'acct_other': "Compte bancaire hors d'Europe (p.ex. USA)",
        'account_number': 'Numero de compte',
        'routing_number': 'Routing number / ABA',
        'routing_help': 'Requis uniquement pour les comptes americains',
        'swift': 'SWIFT / BIC',
        'bank_address': 'Adresse de la banque',
        'bank_address_help': 'Rue, ville et pays de ta banque',
        'other_note': "Pour les virements internationaux nous avons aussi besoin de l'adresse complete de ta banque.",
        'select': 'Choisir',
        'submit': 'Envoyer les donnees', 'save_changes': 'Enregistrer les modifications',
        'iban_valid': 'IBAN valide', 'iban_invalid': 'IBAN invalide - a verifier',
        'err_required': 'Merci de remplir tous les champs.',
        'err_iban': "L'IBAN est invalide. Merci de verifier ta saisie.",
        'err_birth_date': 'Merci de saisir une date de naissance valide.',
        'success_title': 'Merci beaucoup !',
        'success_msg': 'Nous avons bien recu tes donnees. Ton prix sera vire dans les prochains jours.',
        'success_edit': "Tant que le paiement n'a pas ete effectue tu peux corriger tes donnees avec le meme lien.",
        'edit_hint': 'Tes donnees sont enregistrees. Tu peux encore les corriger ici.',
        'locked_title': 'Paiement effectue',
        'locked_msg': "Ton prix a deja ete vire, tes donnees ne peuvent donc plus etre modifiees. Pour toute question contacte-nous directement.",
        'privacy_note': 'Tes donnees sont utilisees uniquement pour le versement du prix.',
        'wa_message': ('Salut {first_name}, felicitations encore pour ton podium au WPC Italy a Alba ! '
                       'Pour le virement de ton prix, merci de remplir ce court formulaire : {link} '
                       'Merci beaucoup ! Sergio - World Pickleball Connect'),
    },
    'IT': {
        'form_title': 'Premio - Dati di pagamento',
        'form_intro': 'Per bonificare il tuo premio ci servono ancora i tuoi dati bancari e fiscali.',
        'player': 'Giocatore', 'results': 'Risultati',
        'sec_personal': 'Dati personali', 'sec_bank': 'Dati bancari',
        'birth_date': 'Data di nascita',
        'address_street': 'Via e numero civico',
        'address_zip_city': 'CAP e citta',
        'address_country': 'Paese',
        'tax_country': 'Paese di residenza fiscale',
        'tax_id': 'Codice fiscale / Partita IVA',
        'account_holder': 'Intestatario del conto',
        'account_holder_help': 'Esattamente come registrato presso la tua banca',
        'iban': 'IBAN', 'iban_help': 'Gli spazi vengono rimossi automaticamente',
        'bic': 'BIC / SWIFT', 'bank_name': 'Nome della banca',
        'acct_type': 'Tipo di conto bancario',
        'acct_sepa': 'Conto bancario in Europa (IBAN)',
        'acct_other': "Conto bancario fuori dall'Europa (es. USA)",
        'account_number': 'Numero di conto',
        'routing_number': 'Routing number / ABA',
        'routing_help': 'Necessario solo per conti statunitensi',
        'swift': 'SWIFT / BIC',
        'bank_address': 'Indirizzo della banca',
        'bank_address_help': 'Via, citta e paese della tua banca',
        'other_note': "Per i bonifici internazionali ci serve anche l'indirizzo completo della tua banca.",
        'select': 'Seleziona',
        'submit': 'Invia i dati', 'save_changes': 'Salva le modifiche',
        'iban_valid': 'IBAN valido', 'iban_invalid': 'IBAN non valido - controlla',
        'err_required': 'Per favore compila tutti i campi.',
        'err_iban': "L'IBAN non e valido. Per favore controlla il dato inserito.",
        'err_birth_date': 'Per favore inserisci una data di nascita valida.',
        'success_title': 'Grazie mille!',
        'success_msg': 'Abbiamo ricevuto i tuoi dati. Il premio sara bonificato nei prossimi giorni.',
        'success_edit': 'Finche il pagamento non e stato effettuato puoi correggere i tuoi dati con lo stesso link.',
        'edit_hint': 'I tuoi dati sono salvati. Puoi ancora correggerli qui.',
        'locked_title': 'Pagamento effettuato',
        'locked_msg': 'Il tuo premio e gia stato bonificato, quindi i tuoi dati non possono piu essere modificati. Per qualsiasi domanda contattaci direttamente.',
        'privacy_note': 'I tuoi dati vengono utilizzati esclusivamente per il pagamento del premio.',
        'wa_message': ('Ciao {first_name}, congratulazioni ancora per il tuo podio al WPC Italy ad Alba! '
                       'Per il bonifico del tuo premio compila per favore questo breve modulo: {link} '
                       'Grazie mille! Sergio - World Pickleball Connect'),
    },
}

# Required regardless of account type.
COMMON_REQUIRED = [
    'birth_date', 'address_street', 'address_zip_city', 'address_country',
    'tax_country', 'tax_id', 'account_holder', 'bank_name',
]
SEPA_REQUIRED = ['iban', 'bic']
# routing_number is US-specific, so it stays optional.
OTHER_REQUIRED = ['account_number', 'bic', 'bank_address']
OTHER_OPTIONAL = ['routing_number']

# Every field the form can post, in one list.
ALL_FIELDS = COMMON_REQUIRED + SEPA_REQUIRED + OTHER_REQUIRED + OTHER_OPTIONAL


def required_for(account_type):
    """Only the fields actually visible for this account type are required."""
    extra = OTHER_REQUIRED if account_type == 'OTHER' else SEPA_REQUIRED
    return COMMON_REQUIRED + extra


@prize.context_processor
def _inject_today():
    """`today` caps the birth_date picker so no future date can be chosen."""
    return {'today': datetime.utcnow().date().isoformat()}


def _t(lang):
    return TRANSLATIONS.get((lang or 'EN').upper(), TRANSLATIONS['EN'])


def _lang_for(payment):
    """Language for a player page: ?lang= wins, else the stored preference."""
    requested = (request.args.get('lang') or '').upper()
    if requested in TRANSLATIONS:
        return requested
    stored = (payment.preferred_language or 'EN').upper()
    return stored if stored in TRANSLATIONS else 'EN'


# ---- IBAN ------------------------------------------------------------------
def normalize_iban(value):
    """Strip spaces and upper-case. Does not validate."""
    return re.sub(r'\s+', '', (value or '')).upper()


def validate_iban(value):
    """Validate an IBAN via the mod-97 checksum (ISO 13616).

    Mirrors the client-side check in prize_form.html; the browser is only a
    convenience, this is the check that counts.
    """
    iban = normalize_iban(value)
    if not re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}', iban):
        return False
    # Move the first four characters to the end, then map letters to digits.
    rearranged = iban[4:] + iban[:4]
    digits = ''.join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def _normalize_phone(phone):
    """Digits-only phone for wa.me, or None if unusable."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('00'):
        digits = digits[2:]
    return digits if len(digits) >= 8 else None


def _form_url(payment):
    return url_for('prize.player_form', token=payment.token, _external=True)


def _progress():
    """Counts for the header/progress bar, computed in one pass."""
    rows = PrizePayment.query.all()
    return {
        'total': len(rows) or TOTAL_PLAYERS,
        'contacted': sum(1 for r in rows if r.contacted_at),
        'submitted': sum(1 for r in rows if r.submitted_at),
        'paid': sum(1 for r in rows if r.paid_at),
        # Non-SEPA accounts can't go into a SEPA batch - they are wired by hand.
        'non_sepa': sum(1 for r in rows if r.has_bank_data and not r.is_sepa),
    }


# ============================================================================
# 1. PLAYER FORM
# ============================================================================

@prize.route('/<token>', methods=['GET', 'POST'])
def player_form(token):
    payment = PrizePayment.query.filter_by(token=token).first()
    if not payment:
        abort(404)

    lang = _lang_for(payment)
    t = _t(lang)

    # Already paid out -> read-only notice, no further edits.
    if payment.is_locked:
        return render_template('prize_form.html', p=payment, t=t, lang=lang,
                               languages=LANGUAGES, countries=PRIZE_COUNTRIES,
                               locked=True, form_data={}, error=None)

    if request.method == 'POST':
        account_type = 'OTHER' if request.form.get('account_type') == 'OTHER' else 'SEPA'
        data = {f: (request.form.get(f) or '').strip() for f in ALL_FIELDS}
        data['account_type'] = account_type
        data['iban'] = normalize_iban(data['iban'])
        data['bic'] = re.sub(r'\s+', '', data['bic']).upper()
        data['account_number'] = re.sub(r'\s+', '', data['account_number'])
        data['routing_number'] = re.sub(r'\s+', '', data['routing_number'])

        required = required_for(account_type)
        error = None
        if not all(data[f] for f in required):
            error = t['err_required']
        elif account_type == 'SEPA' and not validate_iban(data['iban']):
            # No checksum standard for non-SEPA accounts, so only IBANs are checked.
            error = t['err_iban']

        birth_date = None
        if not error:
            try:
                birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                error = t['err_birth_date']
            else:
                # The picker caps this too, but the POST can bypass the picker.
                if birth_date >= datetime.utcnow().date():
                    error = t['err_birth_date']

        if error:
            return render_template('prize_form.html', p=payment, t=t, lang=lang,
                                   languages=LANGUAGES, countries=PRIZE_COUNTRIES,
                                   locked=False, form_data=data, error=error), 400

        payment.account_type = account_type
        for field in required + (OTHER_OPTIONAL if account_type == 'OTHER' else []):
            if field != 'birth_date':
                setattr(payment, field, data[field])
        # Blank the fields of the other account type so the partner never sees
        # stale details left over from an earlier submission.
        for field in (OTHER_REQUIRED + OTHER_OPTIONAL if account_type == 'SEPA' else SEPA_REQUIRED):
            if field not in required:
                setattr(payment, field, None)
        payment.birth_date = birth_date
        payment.submitted_at = datetime.utcnow()
        db.session.commit()

        return redirect(url_for('prize.player_success', token=token, lang=lang))

    return render_template('prize_form.html', p=payment, t=t, lang=lang,
                           languages=LANGUAGES, countries=PRIZE_COUNTRIES,
                           locked=False, form_data={}, error=None)


@prize.route('/<token>/success')
def player_success(token):
    payment = PrizePayment.query.filter_by(token=token).first()
    if not payment:
        abort(404)
    lang = _lang_for(payment)
    return render_template('prize_success.html', p=payment, t=_t(lang), lang=lang,
                           languages=LANGUAGES)


# ============================================================================
# 2. PARTNER VIEW
# ============================================================================

def partner_required(f):
    """Gate a partner route on the partner session, else send them to login."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('prize_partner'):
            return redirect(url_for('prize.partner_login'))
        return f(*args, **kwargs)
    return wrapper


@prize.route('/partner/login', methods=['GET', 'POST'])
def partner_login():
    expected = os.environ.get('PRIZE_PARTNER_PASSWORD', '')
    error = None

    if request.method == 'POST':
        supplied = request.form.get('access_code') or ''
        # An unset password must never mean "everyone gets in".
        if not expected:
            current_app.logger.error(
                'PRIZE_PARTNER_PASSWORD is not set - partner view unavailable')
            error = 'Invalid access code'
        elif hmac.compare_digest(supplied, expected):
            session['prize_partner'] = True
            return redirect(url_for('prize.partner_view'))
        else:
            error = 'Invalid access code'

        time.sleep(1)  # blunt the brute-force rate
        return render_template('prize_partner_login.html', error=error), 401

    if session.get('prize_partner'):
        return redirect(url_for('prize.partner_view'))
    return render_template('prize_partner_login.html', error=None)


@prize.route('/partner/logout')
def partner_logout():
    session.pop('prize_partner', None)
    return redirect(url_for('prize.partner_login'))


@prize.route('/partner')
@partner_required
def partner_view():
    payments = PrizePayment.query.order_by(PrizePayment.gross_amount.desc()).all()
    return render_template('prize_partner.html', payments=payments,
                           progress=_progress(), tournament=TOURNAMENT_NAME)


@prize.route('/partner/paid/<int:payment_id>', methods=['POST'])
@partner_required
def partner_mark_paid(payment_id):
    payment = PrizePayment.query.get_or_404(payment_id)
    _toggle_paid(payment, request.form.get('paid') == '1', 'partner')
    return redirect(url_for('prize.partner_view'))


def _toggle_paid(payment, paid, actor):
    if paid:
        if not payment.paid_at:
            payment.paid_at = datetime.utcnow()
            payment.paid_by = actor
    else:
        payment.paid_at = None
        payment.paid_by = None
    db.session.commit()


@prize.route('/partner/export')
@partner_required
def partner_export():
    return _build_export()


# Excel layout: (header, width, value fn). SEPA and non-SEPA share one table,
# so the columns that don't apply to a row are simply left empty.
EXPORT_COLUMNS = [
    ('Recipient',          26, lambda p: p.account_holder),
    ('Account type',       12, lambda p: 'SEPA' if p.is_sepa else 'Non-SEPA'),
    ('IBAN',               34, lambda p: p.iban if p.is_sepa else None),
    ('BIC / SWIFT',        14, lambda p: p.bic),
    ('Account number',     22, lambda p: None if p.is_sepa else p.account_number),
    ('Routing / ABA',      16, lambda p: None if p.is_sepa else p.routing_number),
    ('Bank',               24, lambda p: p.bank_name),
    ('Bank address',       34, lambda p: None if p.is_sepa else p.bank_address),
    ('Street',             26, lambda p: p.address_street),
    ('ZIP / City',         24, lambda p: p.address_zip_city),
    ('Country',            16, lambda p: p.address_country),
    ('Gross',              11, lambda p: float(p.gross)),
    ('Withholding tax 20%', 18, lambda p: float(p.withholding_tax)),
    ('Net payout',         12, lambda p: float(p.net_amount)),
    ('Payment reference',  36, lambda p: p.payment_reference),
    ('Status',             10, lambda p: 'Paid' if p.paid_at else 'Open'),
]
# 1-based column indices of the three money columns, and their totals labels.
_MONEY_COLS = [i for i, (h, _w, _f) in enumerate(EXPORT_COLUMNS, start=1)
               if h in ('Gross', 'Withholding tax 20%', 'Net payout')]


def _build_export():
    """Excel payout list - only rows with complete data, plus a totals row."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    payments = [p for p in PrizePayment.query
                .order_by(PrizePayment.gross_amount.desc()).all() if p.has_bank_data]

    wb = Workbook()
    ws = wb.active
    ws.title = 'Prize Money'

    ws.append([h for h, _w, _f in EXPORT_COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', wrap_text=True)

    for p in payments:
        ws.append([fn(p) for _h, _w, fn in EXPORT_COLUMNS])

    # Totals row: label sits left of Gross, sums line up under their columns.
    total_row = ws.max_row + 1
    label_col = _MONEY_COLS[0] - 1
    ws.cell(row=total_row, column=label_col, value='Total').font = Font(bold=True)
    for col, attr in zip(_MONEY_COLS, ('gross', 'withholding_tax', 'net_amount')):
        cell = ws.cell(row=total_row, column=col,
                       value=float(sum((getattr(p, attr) for p in payments), Decimal('0'))))
        cell.font = Font(bold=True)

    for col in _MONEY_COLS:
        for cell in ws[get_column_letter(col)][1:]:
            cell.number_format = '#,##0.00'

    for i, (_h, width, _f) in enumerate(EXPORT_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = 'A2'

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(
        stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='wpc_alba_2026_prize_money.xlsx',
    )


# ============================================================================
# 3. ADMIN VIEW
# ============================================================================

@prize.route('/admin')
@login_required
def admin_view():
    payments = PrizePayment.query.order_by(PrizePayment.gross_amount.desc()).all()

    rows = []
    for p in payments:
        lang = (p.preferred_language or 'EN').upper()
        if lang not in TRANSLATIONS:
            lang = 'EN'
        message = TRANSLATIONS[lang]['wa_message'].format(
            first_name=p.first_name, link=_form_url(p))
        digits = _normalize_phone(p.phone)
        rows.append({
            'p': p,
            'form_url': _form_url(p),
            'wa_url': f'https://wa.me/{digits}?text={quote(message)}' if digits else None,
        })

    return render_template('prize_admin.html', rows=rows, progress=_progress(),
                           tournament=TOURNAMENT_NAME)


@prize.route('/admin/contacted/<int:payment_id>', methods=['POST'])
@login_required
def admin_mark_contacted(payment_id):
    payment = PrizePayment.query.get_or_404(payment_id)
    if not payment.contacted_at:
        payment.contacted_at = datetime.utcnow()
        db.session.commit()
    return '', 204


@prize.route('/admin/paid/<int:payment_id>', methods=['POST'])
@login_required
def admin_mark_paid(payment_id):
    payment = PrizePayment.query.get_or_404(payment_id)
    _toggle_paid(payment, request.form.get('paid') == '1', 'admin')
    return redirect(url_for('prize.admin_view'))


@prize.route('/admin/export')
@login_required
def admin_export():
    return _build_export()
