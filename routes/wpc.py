"""
WPC Routes - Check-in, Dashboard, Welcome Pack
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timezone
from urllib.parse import quote
import re
from models import db, WPCPlayer, WPCRegistration, Sponsor

wpc = Blueprint('wpc', __name__, url_prefix='/wpc')


# ============================================================================
# PLAYER CHECK-IN
# ============================================================================

@wpc.route('/checkin/<token>', methods=['GET', 'POST'])
def player_checkin(token):
    """Player check-in page"""
    player = WPCPlayer.query.filter_by(checkin_token=token).first_or_404()
    
    # Get player's registrations
    registrations = player.registrations.all()
    
    if request.method == 'POST':
        # Already checked in?
        if player.checked_in:
            return redirect(url_for('wpc.boarding_pass', token=token))
        
        # Get form data
        phone = request.form.get('phone', '').strip()
        privacy_accepted = request.form.get('privacy_accepted') == 'on'
        whatsapp_optin = request.form.get('whatsapp_optin') == 'on'
        marketing_optin = request.form.get('marketing_optin') == 'on'
        language = request.form.get('language', 'EN').upper()
        
        # Validate
        if not phone:
            flash('Phone number is required', 'danger')
            return redirect(url_for('wpc.player_checkin', token=token))
        
        if not privacy_accepted:
            flash('You must accept the Privacy Policy', 'danger')
            return redirect(url_for('wpc.player_checkin', token=token))
        
        # Save data
        player.phone = phone
        player.privacy_accepted = True
        player.privacy_accepted_at = datetime.utcnow()
        player.whatsapp_optin = whatsapp_optin
        player.marketing_optin = marketing_optin
        player.preferred_language = language
        player.checked_in = True
        player.checked_in_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return redirect(url_for('wpc.boarding_pass', token=token))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('wpc.player_checkin', token=token))
    
    # GET - show form or pass
    return render_template('wpc/checkin.html',
                         player=player,
                         registrations=registrations)


@wpc.route('/pass/<token>')
def boarding_pass(token):
    """Show boarding pass with match schedule"""
    from models import WPCMatch
    from collections import defaultdict
    
    player = WPCPlayer.query.filter_by(checkin_token=token).first_or_404()
    registrations = player.registrations.all()
    
    # Find player's matches
    first_name = player.first_name.lower()
    last_name = player.last_name.lower()
    
    all_matches = WPCMatch.query.order_by(WPCMatch.match_date, WPCMatch.match_time).all()
    
    player_matches = []
    for m in all_matches:
        names = [
            (m.player1_name or '').lower(),
            (m.player2_name or '').lower(),
            (m.opponent1_name or '').lower(),
            (m.opponent2_name or '').lower()
        ]
        
        for name in names:
            if first_name in name and last_name in name:
                is_team1 = first_name in (m.player1_name or '').lower() or first_name in (m.player2_name or '').lower()
                
                if is_team1:
                    partner = m.player2_name if m.player2_name and first_name not in (m.player2_name or '').lower() else (m.player1_name if first_name not in (m.player1_name or '').lower() else None)
                    opponents = f"{m.opponent1_name}" + (f" & {m.opponent2_name}" if m.opponent2_name else "")
                else:
                    partner = m.opponent2_name if m.opponent2_name and first_name not in (m.opponent2_name or '').lower() else (m.opponent1_name if first_name not in (m.opponent1_name or '').lower() else None)
                    opponents = f"{m.player1_name}" + (f" & {m.player2_name}" if m.player2_name else "")
                
                player_matches.append({
                    'date': m.match_date,
                    'time': m.match_time,
                    'court': m.court,
                    'division': m.division,
                    'partner': partner if m.is_doubles else None,
                    'opponents': opponents,
                    'is_doubles': m.is_doubles
                })
                break
    
    matches_by_date = defaultdict(list)
    for match in player_matches:
        matches_by_date[match['date']].append(match)

    # Rotating sponsor based on player ID
    sponsor = None
    sponsors_list = Sponsor.query.filter_by(is_active=True, show_on_boarding_pass=True).order_by(Sponsor.id).all()
    if sponsors_list:
        s = sponsors_list[player.id % len(sponsors_list)]
        sponsor = {
            'logo_url': s.logo_url,
            'website_url': s.get_tracking_link(),
            'text': s.boarding_pass_text or s.name,
        }

    return render_template('wpc/boarding_pass.html',
                         player=player,
                         registrations=registrations,
                         matches_by_date=dict(matches_by_date),
                         total_matches=len(player_matches),
                         sponsor=sponsor)
                         

# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@wpc.route('/admin')
def admin_dashboard():
    """WPC Admin Dashboard"""
    total_players = WPCPlayer.query.count()
    checked_in = WPCPlayer.query.filter_by(checked_in=True).count()
    with_phone = WPCPlayer.query.filter(
        WPCPlayer.phone.isnot(None), 
        WPCPlayer.phone != '-', 
        WPCPlayer.phone != ''
    ).count()
    welcome_packs = WPCPlayer.query.filter_by(welcome_pack_received=True).count()
    
    # Recent check-ins
    recent = WPCPlayer.query.filter_by(checked_in=True).order_by(
        WPCPlayer.checked_in_at.desc()
    ).limit(10).all()
    
    return render_template('wpc/admin_dashboard.html',
                         stats={
                             'total': total_players,
                             'checked_in': checked_in,
                             'pending': total_players - checked_in,
                             'with_phone': with_phone,
                             'without_phone': total_players - with_phone,
                             'welcome_packs': welcome_packs
                         },
                         recent=recent)


@wpc.route('/admin/players')
def admin_players():
    """List all WPC players"""
    search = request.args.get('q', '').strip()
    filter_status = request.args.get('status', 'all')
    
    query = WPCPlayer.query
    
    if search:
        query = query.filter(
            db.or_(
                WPCPlayer.first_name.ilike(f'%{search}%'),
                WPCPlayer.last_name.ilike(f'%{search}%'),
                WPCPlayer.email.ilike(f'%{search}%')
            )
        )
    
    if filter_status == 'checked_in':
        query = query.filter_by(checked_in=True)
    elif filter_status == 'pending':
        query = query.filter_by(checked_in=False)
    elif filter_status == 'no_phone':
        query = query.filter(db.or_(WPCPlayer.phone.is_(None), WPCPlayer.phone == '-', WPCPlayer.phone == ''))
    
    players = query.order_by(WPCPlayer.last_name).all()
    
    return render_template('wpc/admin_players.html', players=players, search=search, filter_status=filter_status)


@wpc.route('/admin/search')
def admin_search():
    """AJAX search for players"""
    query = request.args.get('q', '').strip().lower()
    
    if len(query) < 2:
        return jsonify({'players': []})
    
    players = WPCPlayer.query.filter(
        db.or_(
            WPCPlayer.first_name.ilike(f'%{query}%'),
            WPCPlayer.last_name.ilike(f'%{query}%'),
            WPCPlayer.email.ilike(f'%{query}%')
        )
    ).limit(15).all()
    
    return jsonify({
        'players': [{
            'id': p.id,
            'name': p.get_full_name(),
            'country': p.country,
            'email': p.email,
            'phone': p.phone,
            'checked_in': p.checked_in,
            'checked_in_at': p.checked_in_at.strftime('%H:%M') if p.checked_in_at else None,
            'welcome_pack': p.welcome_pack_received,
            'token': p.checkin_token
        } for p in players]
    })


# ============================================================================
# STAFF CHECK-IN STATION
# ============================================================================

@wpc.route('/admin/checkin')
def staff_checkin():
    """Staff check-in station"""
    players = WPCPlayer.query.order_by(WPCPlayer.last_name).all()
    
    total = len(players)
    checked_in = len([p for p in players if p.checked_in])
    welcome_packs = len([p for p in players if p.welcome_pack_received])
    
    return render_template('wpc/staff_checkin.html',
                         players=players,
                         stats={
                             'total': total,
                             'checked_in': checked_in,
                             'pending': total - checked_in,
                             'welcome_packs': welcome_packs
                         })


@wpc.route('/admin/checkin/<int:player_id>', methods=['POST'])
def staff_do_checkin(player_id):
    """Staff performs check-in"""
    player = WPCPlayer.query.get_or_404(player_id)
    
    # Get phone from form if provided
    phone = request.form.get('phone', '').strip()
    if phone:
        player.phone = phone
    
    if not player.checked_in:
        player.checked_in = True
        player.checked_in_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'{player.get_full_name()} checked in!',
                'checked_in_at': player.checked_in_at.strftime('%H:%M')
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({
        'success': True,
        'message': 'Already checked in',
        'checked_in_at': player.checked_in_at.strftime('%H:%M') if player.checked_in_at else None
    })


@wpc.route('/admin/welcome-pack/<int:player_id>', methods=['POST'])
def give_welcome_pack(player_id):
    """Mark welcome pack as given"""
    player = WPCPlayer.query.get_or_404(player_id)
    
    if not player.welcome_pack_received:
        player.welcome_pack_received = True
        player.welcome_pack_received_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Welcome pack given to {player.get_full_name()}!'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': True, 'message': 'Already received'})


# ============================================================================
# API: STATS
# ============================================================================

@wpc.route('/api/stats')
def api_stats():
    """Live stats for dashboard"""
    total = WPCPlayer.query.count()
    checked_in = WPCPlayer.query.filter_by(checked_in=True).count()
    welcome_packs = WPCPlayer.query.filter_by(welcome_pack_received=True).count()
    
    recent = WPCPlayer.query.filter_by(checked_in=True).order_by(
        WPCPlayer.checked_in_at.desc()
    ).limit(5).all()
    
    return jsonify({
        'total': total,
        'checked_in': checked_in,
        'pending': total - checked_in,
        'welcome_packs': welcome_packs,
        'percentage': round(checked_in / total * 100, 1) if total > 0 else 0,
        'recent': [{
            'name': p.get_full_name(),
            'country': p.country,
            'time': p.checked_in_at.strftime('%H:%M') if p.checked_in_at else None
        } for p in recent]
    })


# ============================================================================
# TERMS PAGE
# ============================================================================

@wpc.route('/terms')
def terms():
    """Privacy Policy and Terms"""
    return render_template('wpc/terms.html')


# ============================================================================
# POOL INVITATION TOOL (admin: invite WPC players to the Player Pool)
# ============================================================================

POOL_INVITE_TRANSLATIONS = {
    'EN': {
        'pool_invite_overview_title': 'Pool Invitation Tool',
        'pool_invite_wave_title': 'Sending wave: {country}',
        'pool_invite_open_whatsapp': 'Open WhatsApp for {name}',
        'pool_invite_mark_sent': 'Mark sent and next',
        'pool_invite_skip_wrong': 'Skip - wrong number',
        'pool_invite_skip_optout': 'Skip - opted out',
        'pool_invite_progress': 'Player {x} of {y}',
        'pool_invite_wave_complete': 'Wave complete - {sent} sent, {skipped} skipped',
        'pool_invite_no_marketing_warning': 'Player did not opt-in to marketing or WhatsApp. Compliance risk.',
        'pool_invite_include_no_optin': 'Include players without explicit opt-in (compliance risk)',
    },
    'DE': {
        'pool_invite_overview_title': 'Pool-Einladungs-Tool',
        'pool_invite_wave_title': 'Welle senden: {country}',
        'pool_invite_open_whatsapp': 'WhatsApp oeffnen fuer {name}',
        'pool_invite_mark_sent': 'Gesendet markieren und weiter',
        'pool_invite_skip_wrong': 'Ueberspringen - falsche Nummer',
        'pool_invite_skip_optout': 'Ueberspringen - abgemeldet',
        'pool_invite_progress': 'Spieler {x} von {y}',
        'pool_invite_wave_complete': 'Welle fertig - {sent} gesendet, {skipped} uebersprungen',
        'pool_invite_no_marketing_warning': 'Spieler hat kein Marketing- oder WhatsApp-Opt-in. Compliance-Risiko.',
        'pool_invite_include_no_optin': 'Spieler ohne ausdrueckliches Opt-in einbeziehen (Compliance-Risiko)',
    },
    'ES': {
        'pool_invite_overview_title': 'Herramienta de Invitacion al Pool',
        'pool_invite_wave_title': 'Enviando ola: {country}',
        'pool_invite_open_whatsapp': 'Abrir WhatsApp para {name}',
        'pool_invite_mark_sent': 'Marcar enviado y siguiente',
        'pool_invite_skip_wrong': 'Omitir - numero incorrecto',
        'pool_invite_skip_optout': 'Omitir - se dio de baja',
        'pool_invite_progress': 'Jugador {x} de {y}',
        'pool_invite_wave_complete': 'Ola completa - {sent} enviados, {skipped} omitidos',
        'pool_invite_no_marketing_warning': 'El jugador no acepto marketing ni WhatsApp. Riesgo de cumplimiento.',
        'pool_invite_include_no_optin': 'Incluir jugadores sin opt-in explicito (riesgo de cumplimiento)',
    },
    'FR': {
        'pool_invite_overview_title': 'Outil d Invitation au Pool',
        'pool_invite_wave_title': 'Envoi de la vague: {country}',
        'pool_invite_open_whatsapp': 'Ouvrir WhatsApp pour {name}',
        'pool_invite_mark_sent': 'Marquer envoye et suivant',
        'pool_invite_skip_wrong': 'Passer - mauvais numero',
        'pool_invite_skip_optout': 'Passer - desabonne',
        'pool_invite_progress': 'Joueur {x} sur {y}',
        'pool_invite_wave_complete': 'Vague terminee - {sent} envoyes, {skipped} passes',
        'pool_invite_no_marketing_warning': 'Le joueur n a pas accepte le marketing ni WhatsApp. Risque de conformite.',
        'pool_invite_include_no_optin': 'Inclure les joueurs sans opt-in explicite (risque de conformite)',
    },
}


def _pool_invite_t(lang):
    return POOL_INVITE_TRANSLATIONS.get((lang or 'EN').upper(), POOL_INVITE_TRANSLATIONS['EN'])


def _invite_lang():
    lang = (request.args.get('lang') or 'EN').upper()
    return lang if lang in POOL_INVITE_TRANSLATIONS else 'EN'


def normalize_phone(phone):
    """Return digits-only phone for wa.me, or None if unparseable.

    Strips spaces, hyphens, parentheses; keeps digits (wa.me adds + itself).
    """
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    digits = digits.lstrip('0') if digits.startswith('00') else digits  # 0044 -> 44
    if len(digits) < 8:
        return None
    return digits


def _invitable_query(country=None, only_checkedin=False, include_no_optin=False):
    """Players eligible for a pool invite.

    Default: whatsapp_optin = true AND marketing_optin = true AND a valid phone.
    With include_no_optin, BOTH opt-in requirements are relaxed (phone only) -
    a compliance risk surfaced in the UI.
    """
    q = WPCPlayer.query.filter(
        WPCPlayer.phone.isnot(None),
        WPCPlayer.phone != '',
    )
    if not include_no_optin:
        q = q.filter(
            WPCPlayer.whatsapp_optin.is_(True),
            WPCPlayer.marketing_optin.is_(True),
        )
    if only_checkedin:
        q = q.filter(WPCPlayer.checked_in.is_(True))
    if country:
        q = q.filter(WPCPlayer.country == country)
    return q


def _pool_url():
    return request.host_url.rstrip('/') + '/pool'


def _invite_message(player):
    """Hardcoded English invitation message with first_name + pool URL interpolated."""
    first = player.first_name or 'there'
    return (
        f"Hi {first}! This is Sergio from the WPC / PCL team - great to have met you at "
        f"WPC European Open in Malaga.\n\n"
        f"We are building a permanent Player Pool so captains and organizers can reach you "
        f"for upcoming tournaments (WPC Bali, WPC China, WPC Turkey and PCL events).\n\n"
        f"Join the pool here (2 minutes): {_pool_url()}\n\n"
        f"You will get tournament updates and early-bird access. Thank you!\n"
        f"Sergio Ruiz Caro"
    )


def _player_payload(player):
    """Card data + wa.me link for one player (used by wave page and JSON endpoints)."""
    digits = normalize_phone(player.phone)
    message = _invite_message(player)
    return {
        'id': player.id,
        'name': player.get_full_name(),
        'first_name': player.first_name,
        'initials': ((player.first_name or ' ')[0] + (player.last_name or ' ')[0]).upper().strip() or '?',
        'dupr': player.dupr_rating or '-',
        'checked_in': bool(player.checked_in),
        'marketing_optin': bool(player.marketing_optin),
        'phone': player.phone,
        'phone_digits': digits,
        'message': message,
        'wa_url': (f"https://wa.me/{digits}?text={quote(message)}") if digits else None,
    }


def _next_in_wave(country, only_checkedin, include_no_optin):
    """Find the next un-invited player with a valid phone; auto-fail invalid phones."""
    q = _invitable_query(country, only_checkedin, include_no_optin) \
        .filter(WPCPlayer.pool_invite_sent_at.is_(None)) \
        .order_by(WPCPlayer.country, WPCPlayer.last_name)
    next_player = None
    dirty = False
    for p in q.all():
        if normalize_phone(p.phone):
            next_player = p
            break
        # Unparseable phone -> mark failed so the queue advances past it
        p.pool_invite_sent_at = datetime.now(timezone.utc)
        p.pool_invite_status = 'failed'
        dirty = True
    if dirty:
        db.session.commit()
    return next_player


def _wave_progress(country, only_checkedin, include_no_optin):
    """(done, total, sent, skipped) for valid-phone invitable players in this country."""
    players = _invitable_query(country, only_checkedin, include_no_optin).all()
    total = done = sent = skipped = 0
    for p in players:
        if not normalize_phone(p.phone):
            continue
        total += 1
        if p.pool_invite_sent_at is not None:
            done += 1
            if p.pool_invite_status == 'sent':
                sent += 1
            else:
                skipped += 1
    return done, total, sent, skipped


@wpc.route('/admin/pool-invite')
def pool_invite_overview():
    """Per-country overview with invite stats and filters."""
    lang = _invite_lang()
    t = _pool_invite_t(lang)
    only_checkedin = request.args.get('only_checkedin') == '1'
    include_no_optin = request.args.get('include_no_optin') == '1'

    players = _invitable_query(only_checkedin=only_checkedin,
                               include_no_optin=include_no_optin).all()
    countries = {}
    for p in players:
        if not normalize_phone(p.phone):
            continue
        d = countries.setdefault(p.country or 'Unknown', {'total': 0, 'sent': 0})
        d['total'] += 1
        if p.pool_invite_sent_at is not None:
            d['sent'] += 1

    rows = [{'country': c, 'total': d['total'], 'sent': d['sent'],
             'remaining': d['total'] - d['sent']} for c, d in countries.items()]
    rows.sort(key=lambda r: r['country'])
    totals = {
        'total': sum(r['total'] for r in rows),
        'sent': sum(r['sent'] for r in rows),
        'remaining': sum(r['remaining'] for r in rows),
    }
    return render_template('wpc/pool_invite_overview.html',
                           rows=rows, totals=totals, t=t, current_lang=lang,
                           only_checkedin=only_checkedin, include_no_optin=include_no_optin)


@wpc.route('/admin/pool-invite/wave')
def pool_invite_wave():
    """Sequential single-player sender for one country."""
    lang = _invite_lang()
    t = _pool_invite_t(lang)
    country = request.args.get('country') or ''
    only_checkedin = request.args.get('only_checkedin') == '1'
    include_no_optin = request.args.get('include_no_optin') == '1'

    next_player = _next_in_wave(country, only_checkedin, include_no_optin)
    done, total, sent, skipped = _wave_progress(country, only_checkedin, include_no_optin)
    payload = _player_payload(next_player) if next_player else None

    return render_template('wpc/pool_invite_wave.html',
                           t=t, current_lang=lang, country=country,
                           player=payload, done=done, total=total, sent=sent, skipped=skipped,
                           only_checkedin=only_checkedin, include_no_optin=include_no_optin)


def _mark_and_next(default_status):
    """Shared body for mark-sent / mark-failed JSON endpoints."""
    data = request.get_json(silent=True) or request.form
    player_id = data.get('player_id')
    status = data.get('status') or default_status
    if status not in ('sent', 'failed', 'skipped', 'opted_out'):
        status = default_status
    country = data.get('country') or ''
    only_checkedin = str(data.get('only_checkedin')) in ('1', 'true', 'True')
    include_no_optin = str(data.get('include_no_optin')) in ('1', 'true', 'True')

    player = WPCPlayer.query.get(player_id) if player_id else None
    if player is not None:
        player.pool_invite_sent_at = datetime.now(timezone.utc)
        player.pool_invite_status = status
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'ok': False, 'error': str(e)}), 500

    next_player = _next_in_wave(country, only_checkedin, include_no_optin)
    done, total, sent, skipped = _wave_progress(country, only_checkedin, include_no_optin)
    if next_player is None:
        return jsonify({'ok': True, 'complete': True, 'sent': sent, 'skipped': skipped})
    return jsonify({'ok': True, 'complete': False, 'player': _player_payload(next_player),
                    'done': done, 'total': total, 'sent': sent, 'skipped': skipped})


@wpc.route('/admin/pool-invite/mark-sent', methods=['POST'])
def pool_invite_mark_sent():
    return _mark_and_next('sent')


@wpc.route('/admin/pool-invite/mark-failed', methods=['POST'])
def pool_invite_mark_failed():
    return _mark_and_next('failed')

