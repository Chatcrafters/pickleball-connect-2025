from flask import Blueprint, render_template
from models import db, Player, Event, Message
from datetime import date

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Dashboard/Home page"""
    # Get statistics
    total_players = Player.query.count()
    total_events = Event.query.count()
    total_messages = Message.query.count()
    
    # Get upcoming events
    upcoming_events = Event.query.filter(Event.start_date >= date.today()).order_by(Event.start_date).limit(5).all()
    
    # Get recent players
    recent_players = Player.query.order_by(Player.created_at.desc()).limit(5).all()
    
    return render_template('index.html',
                         total_players=total_players,
                         total_events=total_events,
                         total_messages=total_messages,
                         upcoming_events=upcoming_events,
                         recent_players=recent_players)

@main.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')