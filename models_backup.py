from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association table for event registrations
event_players = db.Table('event_registration',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id')),
    db.Column('response_status', db.String(20), default='pending'),
    db.Column('response_date', db.DateTime, nullable=True),
    db.Column('notes', db.Text, nullable=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    extend_existing=True
)

class Player(db.Model):
    __tablename__ = 'player'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    skill_level = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    preferred_language = db.Column(db.String(10), default='EN')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    invited_events = db.relationship('Event', secondary='event_registration', 
                                    back_populates='invited_players',
                                    overlaps="registrations")
    
    # Backward compatibility property
    @property
    def phone(self):
        return self.phone_number
    
    @phone.setter
    def phone(self, value):
        self.phone_number = value
    
    def __repr__(self):
        return f'<Player {self.first_name} {self.last_name}>'
    
    def get_response_for_event(self, event_id):
        """Get player's response status for a specific event"""
        from sqlalchemy import select
        result = db.session.execute(
            select(event_players).where(
                event_players.c.player_id == self.id,
                event_players.c.event_id == event_id
            )
        ).first()
        
        if result:
            return {
                'status': result.response_status,
                'date': result.response_date,
                'notes': result.notes
            }
        return None

class Event(db.Model):
    __tablename__ = 'event'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    invited_players = db.relationship('Player', secondary='event_registration',
                                     back_populates='invited_events',
                                     overlaps="registrations")
    messages = db.relationship('Message', back_populates='event', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Event {self.name}>'
    
    def get_response_stats(self):
        """Get statistics about player responses"""
        from sqlalchemy import select, func
        results = db.session.execute(
            select(
                event_players.c.response_status, 
                func.count()
            ).where(
                event_players.c.event_id == self.id
            ).group_by(event_players.c.response_status)
        ).all()
        
        stats = {
            'pending': 0,
            'interested': 0,
            'more_info': 0,
            'not_interested': 0,
            'confirmed': 0
        }
        
        for status, count in results:
            if status in stats:
                stats[status] = count
        
        return stats
    
    def get_players_by_response(self, status):
        """Get all players with a specific response status"""
        from sqlalchemy import select
        results = db.session.execute(
            select(
                Player, 
                event_players.c.response_date, 
                event_players.c.notes
            ).join(
                event_players, Player.id == event_players.c.player_id
            ).where(
                event_players.c.event_id == self.id,
                event_players.c.response_status == status
            )
        ).all()
        
        return [{'player': r[0], 'response_date': r[1], 'notes': r[2]} for r in results]

class Message(db.Model):
    __tablename__ = 'message'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    content = db.Column(db.Text, nullable=True)
    direction = db.Column(db.String, nullable=True)  # Deine zusätzliche Spalte
    status = db.Column(db.String, nullable=True)
    message_type = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Deine zusätzliche Spalte
    sent_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    event = db.relationship('Event', back_populates='messages')
    player = db.relationship('Player')
    
    def __repr__(self):
        return f'<Message {self.id} - {self.message_type}>'

class PlayerResponse(db.Model):
    """Track individual WhatsApp responses from players"""
    __tablename__ = 'player_response'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    response_type = db.Column(db.String(20), nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    
    # Relationships
    player = db.relationship('Player')
    event = db.relationship('Event')
    
    def __repr__(self):
        return f'<PlayerResponse {self.id} - {self.response_type}>'