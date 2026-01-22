from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Event, Player, Message
from datetime import datetime
from utils.whatsapp import send_whatsapp_message, get_message_template

events = Blueprint('events', __name__)

@events.route('/')
def event_list():
    """List all events with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 50)  # Max 50 per page

    pagination = Event.query.order_by(Event.start_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('event_list.html',
                          events=pagination.items,
                          pagination=pagination)

@events.route('/<int:event_id>')
def event_detail(event_id):
    """Show event details"""
    event = Event.query.get_or_404(event_id)
    invited_players = event.invited_players
    available_players = Player.query.filter(~Player.id.in_([p.id for p in invited_players])).all()
    return render_template('event_detail.html', 
                         event=event, 
                         invited_players=invited_players,
                         available_players=available_players)

@events.route('/create', methods=['GET', 'POST'])
def create_event():
    """Create a new event"""
    if request.method == 'POST':
        event = Event(
            name=request.form['name'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None,
            location=request.form['location'],
            description=request.form.get('description')
        )
        
        try:
            db.session.add(event)
            db.session.commit()
            flash(f'Event "{event.name}" created successfully!', 'success')
            return redirect(url_for('events.event_detail', event_id=event.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
    
    return render_template('event_form.html', event=None)

@events.route('/<int:event_id>/edit', methods=['GET', 'POST'])
def edit_event(event_id):
    """Edit an event"""
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        event.name = request.form['name']
        event.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        event.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None
        event.location = request.form['location']
        event.description = request.form.get('description')
        
        try:
            db.session.commit()
            flash(f'Event "{event.name}" updated successfully!', 'success')
            return redirect(url_for('events.event_detail', event_id=event.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating event: {str(e)}', 'danger')
    
    return render_template('event_form.html', event=event)

@events.route('/<int:event_id>/delete', methods=['POST'])
def delete_event(event_id):
    """Delete an event"""
    event = Event.query.get_or_404(event_id)
    
    try:
        db.session.delete(event)
        db.session.commit()
        flash(f'Event "{event.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting event: {str(e)}', 'danger')
    
    return redirect(url_for('events.event_list'))

@events.route('/<int:event_id>/add-players', methods=['POST'])
def add_players_to_event(event_id):
    """Add players to an event"""
    event = Event.query.get_or_404(event_id)
    player_ids = request.form.getlist('player_ids')
    
    if not player_ids:
        flash('No players selected.', 'warning')
        return redirect(url_for('events.event_detail', event_id=event_id))
    
    added_count = 0
    for player_id in player_ids:
        player = Player.query.get(int(player_id))
        if player and player not in event.invited_players:
            event.invited_players.append(player)
            added_count += 1
    
    try:
        db.session.commit()
        flash(f'{added_count} player(s) invited to {event.name}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error inviting players: {str(e)}', 'danger')
    
    return redirect(url_for('events.event_detail', event_id=event_id))

@events.route('/<int:event_id>/remove-player/<int:player_id>', methods=['POST'])
def remove_player_from_event(event_id, player_id):
    """Remove a player from an event"""
    event = Event.query.get_or_404(event_id)
    player = Player.query.get_or_404(player_id)
    
    if player in event.invited_players:
        event.invited_players.remove(player)
        try:
            db.session.commit()
            flash(f'{player.first_name} {player.last_name} removed from {event.name}!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error removing player: {str(e)}', 'danger')
    
    return redirect(url_for('events.event_detail', event_id=event_id))

@events.route('/<int:event_id>/send-invitations', methods=['POST'])
def send_event_invitations(event_id):
    """Send WhatsApp invitations to invited players"""
    event = Event.query.get_or_404(event_id)
    message_type = request.form.get('message_type', 'invitation')
    test_mode = request.form.get('test_mode') == 'on'
    
    print(f"\n🚀 Starting to send {message_type} messages...")
    print(f"📊 Event: {event.name}")
    print(f"👥 Invited players: {len(event.invited_players)}")
    print(f"🧪 Test mode: {test_mode}")
    
    sent_count = 0
    for player in event.invited_players:
        # Format dates
        start_date_formatted = event.start_date.strftime('%d.%m.%Y')
        end_date_formatted = event.end_date.strftime('%d.%m.%Y') if event.end_date else None
        
        print(f"\n📤 Preparing message for {player.first_name} {player.last_name}")
        print(f"   Language: {player.preferred_language}")
        print(f"   Phone: {player.phone}")
        
        # Get message in player's preferred language
        message = get_message_template(
            message_type,
            player.preferred_language,
            event_name=event.name,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            location=event.location,
            description=event.description or ""
        )
        
        result = send_whatsapp_message(player.phone, message, test_mode=test_mode)
        
        if result['status'] in ['sent', 'test_mode']:
            # Log message
            msg = Message(
                event_id=event.id,
                player_id=player.id,
                message_type=message_type,
                content=message,
                status='sent' if not test_mode else 'test'
            )
            db.session.add(msg)
            sent_count += 1
            print(f"   ✅ Message queued for {player.first_name}")
        else:
            print(f"   ❌ Failed to send to {player.first_name}")
    
    try:
        db.session.commit()
        mode_text = " (TEST MODE)" if test_mode else ""
        flash(f'{sent_count} invitation(s) sent{mode_text}!', 'success')
        print(f"\n✅ Successfully sent {sent_count} messages{mode_text}!")
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending invitations: {str(e)}', 'danger')
        print(f"\n❌ Error: {str(e)}")
    
    return redirect(url_for('events.event_detail', event_id=event_id))