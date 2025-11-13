from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Player, Event
from datetime import datetime, date

admin = Blueprint('admin', __name__)

@admin.route('/events/<int:event_id>/edit-advanced', methods=['GET', 'POST'])
def edit_event_advanced(event_id):
    """Extended event editing with more fields"""
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        event.name = request.form['name']
        event.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        event.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None
        event.location = request.form['location']
        event.description = request.form.get('description')
        
        try:
            db.session.commit()
            flash(f'Event "{event.name}" updated!', 'success')
            return redirect(url_for('events.event_detail', event_id=event.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('admin/edit_event.html', event=event)
@admin.route('/players/import', methods=['GET', 'POST'])
def import_players():
    """Import players from CSV/Excel"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        flash('Import function coming soon! CSV/Excel upload ready!', 'info')
        return redirect(url_for('players.player_list'))
    
    return render_template('admin/import_players.html')

@admin.route('/players/download-example-csv')
def download_example_csv():
    """Download example CSV file"""
    from flask import make_response
    
    csv_content = """first_name,last_name,phone,email,skill_level,city,country,preferred_language
Max,Mustermann,+491234567890,max@example.com,3.5,Berlin,Germany,DE
Sarah,Schmidt,+491234567891,sarah@example.com,4.0,München,Germany,DE
John,Smith,+441234567890,john@example.com,3.0,London,UK,EN"""
    
    response = make_response(csv_content)
    response.headers['Content-Disposition'] = 'attachment; filename=players_example.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

@admin.route('/events/<int:event_id>/invite', methods=['GET'])
def invite_players(event_id):
    """Show player invitation interface"""
    event = Event.query.get_or_404(event_id)
    invited_count = len(event.invited_players)
    
    # Get available players (not yet invited)
    invited_player_ids = [p.id for p in event.invited_players]
    available_players = Player.query.filter(~Player.id.in_(invited_player_ids)).order_by(Player.last_name).all()
    
    return render_template('admin/invite_players.html', 
                         event=event, 
                         invited_count=invited_count,
                         available_players=available_players)

@admin.route('/events/<int:event_id>/send-invitations', methods=['GET'])
def send_invitations_page(event_id):
    """Show send invitations interface"""
    event = Event.query.get_or_404(event_id)
    invited_players = event.invited_players
    
    return render_template('admin/send_invitations.html', 
                         event=event, 
                         invited_players=invited_players)

@admin.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    """Public subscription page"""
    if request.method == 'POST':
        player = Player(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            phone=request.form['phone'],
            email=request.form.get('email'),
            skill_level=request.form['skill_level'],
            city=request.form.get('city'),
            country=request.form.get('country'),
            preferred_language=request.form['preferred_language']
        )
        
        try:
            db.session.add(player)
            db.session.commit()
            return redirect(url_for('admin.subscribe_success', player_id=player.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('admin/subscribe.html')

@admin.route('/subscribe/success/<int:player_id>')
def subscribe_success(player_id):
    """Subscription success page"""
    player = Player.query.get_or_404(player_id)
    upcoming_events = Event.query.filter(Event.start_date >= date.today()).order_by(Event.start_date).limit(5).all()
    
    return render_template('admin/subscribe_success.html', 
                         player=player,
                         upcoming_events=upcoming_events)