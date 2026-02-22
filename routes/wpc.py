"""
WPC Routes - Check-in, Dashboard, Welcome Pack
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from models import db, WPCPlayer, WPCRegistration

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
    """Show boarding pass after check-in"""
    player = WPCPlayer.query.filter_by(checkin_token=token).first_or_404()
    registrations = player.registrations.all()
    
    return render_template('wpc/boarding_pass.html',
                         player=player,
                         registrations=registrations)


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
