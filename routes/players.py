from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Player
from utils.whatsapp import send_profile_completion_link

players = Blueprint('players', __name__)

@players.route('/')
def player_list():
    """List all players"""
    players = Player.query.order_by(Player.last_name).all()
    return render_template('player_list.html', players=players)

@players.route('/<int:player_id>')
def player_detail(player_id):
    """Show player details"""
    player = Player.query.get_or_404(player_id)
    return render_template('player_detail.html', player=player)

@players.route('/add', methods=['GET', 'POST'])
def add_player():
    """Add a new player"""
    if request.method == 'POST':
        player = Player(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            phone=request.form['phone'],
            email=request.form.get('email'),
            skill_level=request.form.get('skill_level'),
            city=request.form.get('city'),
            country=request.form.get('country'),
            preferred_language=request.form.get('preferred_language', 'EN')
        )
        
        # Generate update token for new player
        player.generate_update_token()
        
        try:
            db.session.add(player)
            db.session.commit()
            flash(f'Player {player.first_name} {player.last_name} added successfully!', 'success')
            return redirect(url_for('players.player_detail', player_id=player.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding player: {str(e)}', 'danger')
    
    return render_template('player_form.html', player=None)

@players.route('/<int:player_id>/edit', methods=['GET', 'POST'])
def edit_player(player_id):
    """Edit a player"""
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        player.first_name = request.form['first_name']
        player.last_name = request.form['last_name']
        player.phone = request.form['phone']
        player.email = request.form.get('email')
        player.skill_level = request.form.get('skill_level')
        player.city = request.form.get('city')
        player.country = request.form.get('country')
        player.preferred_language = request.form.get('preferred_language', 'EN')
        
        try:
            db.session.commit()
            flash(f'Player {player.first_name} {player.last_name} updated successfully!', 'success')
            return redirect(url_for('players.player_detail', player_id=player.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating player: {str(e)}', 'danger')
    
    return render_template('player_form.html', player=player)

@players.route('/<int:player_id>/delete', methods=['POST'])
def delete_player(player_id):
    """Delete a player"""
    player = Player.query.get_or_404(player_id)
    
    try:
        db.session.delete(player)
        db.session.commit()
        flash(f'Player {player.first_name} {player.last_name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting player: {str(e)}', 'danger')
    
    return redirect(url_for('players.player_list'))

@players.route('/update/<token>', methods=['GET', 'POST'])
def update_profile(token):
    """Allow players to update their own profile via unique token"""
    player = Player.query.filter_by(update_token=token).first_or_404()
    
    if request.method == 'POST':
        # Players can only update certain fields
        player.email = request.form.get('email')
        player.skill_level = request.form.get('skill_level')
        player.city = request.form.get('city')
        player.country = request.form.get('country')
        player.preferred_language = request.form.get('preferred_language', player.preferred_language)
        
        try:
            db.session.commit()
            flash('Profil erfolgreich aktualisiert! / Profile updated successfully!', 'success')
            return redirect(url_for('players.update_profile', token=token))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern / Error: {str(e)}', 'danger')
    
    return render_template('player_update_public.html', player=player)

@players.route('/<int:player_id>/send-profile-link', methods=['POST'])
def send_profile_link(player_id):
    """Send profile completion link to a single player via WhatsApp"""
    player = Player.query.get_or_404(player_id)
    
    # Generate token if not exists
    if not player.update_token:
        player.generate_update_token()
        db.session.commit()
    
    # Send WhatsApp message
    result = send_profile_completion_link(player, test_mode=False)
    
    if result['status'] == 'sent':
        flash(f'Profil-Link erfolgreich an {player.first_name} {player.last_name} gesendet!', 'success')
    else:
        flash(f'Fehler beim Senden: {result.get("error", "Unbekannter Fehler")}', 'danger')
    
    # Redirect back to previous page or player detail
    return redirect(request.referrer or url_for('players.player_detail', player_id=player_id))

@players.route('/send-bulk-profile-links', methods=['POST'])
def send_bulk_profile_links():
    """Send profile completion links to multiple players via WhatsApp"""
    player_ids = request.form.getlist('player_ids')
    
    if not player_ids:
        flash('Keine Spieler ausgewählt!', 'warning')
        return redirect(url_for('players.player_list'))
    
    sent_count = 0
    error_count = 0
    
    for player_id in player_ids:
        player = Player.query.get(int(player_id))
        if not player:
            continue
        
        # Generate token if not exists
        if not player.update_token:
            player.generate_update_token()
        
        # Send WhatsApp message
        result = send_profile_completion_link(player, test_mode=False)
        
        if result['status'] == 'sent':
            sent_count += 1
        else:
            error_count += 1
    
    # Commit all token generations
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {str(e)}', 'danger')
        return redirect(url_for('players.player_list'))
    
    # Show summary
    if sent_count > 0:
        flash(f'✅ {sent_count} Profil-Link(s) erfolgreich versendet!', 'success')
    if error_count > 0:
        flash(f'⚠️ {error_count} Nachricht(en) konnten nicht versendet werden.', 'warning')
    
    return redirect(url_for('players.player_list'))

@players.route('/<int:player_id>/generate-token', methods=['POST'])
def generate_token(player_id):
    """Generate update token for a player who doesn't have one"""
    player = Player.query.get_or_404(player_id)
    
    if player.update_token:
        flash(f'Spieler {player.first_name} {player.last_name} hat bereits einen Token!', 'info')
    else:
        player.generate_update_token()
        try:
            db.session.commit()
            flash(f'Token erfolgreich generiert für {player.first_name} {player.last_name}!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Generieren: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('players.player_detail', player_id=player_id))