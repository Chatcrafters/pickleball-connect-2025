from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets

db = SQLAlchemy()

# ============================================================================
# EXISTING MODELS
# ============================================================================

# Enhanced association table for many-to-many relationship between Events and Players
event_players = db.Table('event_players',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('response_status', db.String(20), default='pending'),
    db.Column('response_date', db.DateTime, nullable=True),
    db.Column('notes', db.Text, nullable=True)
)

class Player(db.Model):
    """Base player model - for all players in the system"""
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Indexed for WhatsApp lookups
    email = db.Column(db.String(120), unique=True, nullable=True)
    skill_level = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    preferred_language = db.Column(db.String(10), default='EN')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Coaching fields
    coaching_notes = db.Column(db.Text, nullable=True)
    last_coaching_contact = db.Column(db.DateTime, nullable=True)

    # Weakness tracking
    weaknesses = db.Column(db.Text, nullable=True)
    strengths = db.Column(db.Text, nullable=True)

    # Profile update token
    update_token = db.Column(db.String(64), unique=True, nullable=True, index=True)  # Indexed for token lookups
    
    # Relationships
    invited_events = db.relationship('Event', secondary=event_players, back_populates='invited_players')
    pcl_registrations = db.relationship('PCLRegistration', back_populates='player', lazy='dynamic')
    
    def __repr__(self):
        return f'<Player {self.first_name} {self.last_name}>'
    
    def generate_update_token(self):
        """Generate a unique token for profile updates"""
        self.update_token = secrets.token_urlsafe(32)
        return self.update_token
    
    def get_update_url(self, base_url='https://pickleballconnect.eu'):
        """Get the update URL for this player"""
        if not self.update_token:
            self.generate_update_token()
        return f"{base_url}/player/update/{self.update_token}"
    
    def get_response_for_event(self, event_id):
        """Get player's response status for a specific event"""
        result = db.session.execute(
            db.select(event_players).where(
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
    
    def get_weaknesses_list(self):
        """Return weaknesses as a list"""
        if self.weaknesses:
            return [w.strip() for w in self.weaknesses.split(',')]
        return []
    
    def get_strengths_list(self):
        """Return strengths as a list"""
        if self.strengths:
            return [s.strip() for s in self.strengths.split(',')]
        return []


class Event(db.Model):
    """Base event model - for tournaments, workshops, clinics"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False, index=True)  # Indexed for date filtering
    end_date = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Event type
    event_type = db.Column(db.String(50), default='tournament')
    
    # Relationships
    invited_players = db.relationship('Player', secondary=event_players, back_populates='invited_events')
    messages = db.relationship('Message', back_populates='event', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Event {self.name}>'
    
    def get_response_stats(self):
        """Get statistics about player responses"""
        results = db.session.execute(
            db.select(event_players.c.response_status, db.func.count()).where(
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
        results = db.session.execute(
            db.select(Player, event_players.c.response_date, event_players.c.notes).join(
                event_players, Player.id == event_players.c.player_id
            ).where(
                event_players.c.event_id == self.id,
                event_players.c.response_status == status
            )
        ).all()
        
        return [{'player': r[0], 'response_date': r[1], 'notes': r[2]} for r in results]


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    message_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    event = db.relationship('Event', back_populates='messages')
    player = db.relationship('Player')
    
    def __repr__(self):
        return f'<Message {self.id} - {self.message_type}>'


class PlayerResponse(db.Model):
    """Track individual WhatsApp responses from players"""
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


# ============================================================================
# PCL MODELS
# ============================================================================

class PCLTournament(db.Model):
    """PCL Tournament (e.g., PCL Malaga 2026)"""
    __tablename__ = 'pcl_tournament'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Registration deadline
    registration_deadline = db.Column(db.DateTime, nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='open')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teams = db.relationship('PCLTeam', back_populates='tournament', lazy='dynamic')
    
    def __repr__(self):
        return f'<PCLTournament {self.name}>'
    
    def get_stats(self):
        """Get tournament statistics"""
        teams = self.teams.all()
        total_players = sum(team.registrations.count() for team in teams)
        complete_players = sum(
            team.registrations.filter_by(status='complete').count() 
            for team in teams
        )
        return {
            'total_teams': len(teams),
            'total_players': total_players,
            'complete_players': complete_players,
            'completion_rate': round(complete_players / total_players * 100, 1) if total_players > 0 else 0
        }


class PCLTeam(db.Model):
    """National team for PCL (e.g., Germany +19, Spain +50)"""
    __tablename__ = 'pcl_team'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('pcl_tournament.id'), nullable=False)
    
    # Team info
    country_code = db.Column(db.String(3), nullable=False)
    country_name = db.Column(db.String(100), nullable=False)
    country_flag = db.Column(db.String(10), nullable=True)
    
    # Age category
    age_category = db.Column(db.String(10), nullable=False)
    
    # Team limits
    min_men = db.Column(db.Integer, default=2)
    max_men = db.Column(db.Integer, default=4)
    min_women = db.Column(db.Integer, default=2)
    max_women = db.Column(db.Integer, default=4)
    
    # Secret token for captain access
    captain_token = db.Column(db.String(64), unique=True, nullable=False, index=True)  # Indexed for token lookups

    # Status
    status = db.Column(db.String(20), default='incomplete')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament = db.relationship('PCLTournament', back_populates='teams')
    registrations = db.relationship('PCLRegistration', back_populates='team', lazy='dynamic')
    
    def __repr__(self):
        return f'<PCLTeam {self.country_code} {self.age_category}>'
    
    @staticmethod
    def generate_token():
        """Generate a unique captain token"""
        return secrets.token_urlsafe(32)
    
    def get_captain_url(self):
        """Get the secret URL for captain access"""
        return f"/pcl/team/{self.captain_token}"
    
    def get_registration_url(self):
        """Get the URL for player registration"""
        return f"/pcl/register/{self.captain_token}"
    
    def get_stats(self):
        """Get team registration statistics"""
        # Use direct query to avoid lazy loading issues
        registrations = PCLRegistration.query.filter_by(team_id=self.id).all()
        men = [r for r in registrations if r.gender == 'male']
        women = [r for r in registrations if r.gender == 'female']
        captains = [r for r in registrations if r.is_captain]
        
        men_complete = len([r for r in men if r.status == 'complete'])
        women_complete = len([r for r in women if r.status == 'complete'])
        
        return {
            'total': len(registrations),
            'men': len(men),
            'women': len(women),
            'captains': len(captains),
            'men_complete': men_complete,
            'women_complete': women_complete,
            'men_with_photo': len([r for r in men if r.photo_filename]),
            'women_with_photo': len([r for r in women if r.photo_filename]),
            'is_complete': (
                len(men) >= self.min_men and 
                len(women) >= self.min_women and
                men_complete >= self.min_men and
                women_complete >= self.min_women
            )
        }


class PCLRegistration(db.Model):
    """Player registration for PCL - contains all PCL-specific data"""
    __tablename__ = 'pcl_registration'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('pcl_team.id'), nullable=False, index=True)  # Indexed for team queries
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    
    # Personal info (required)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)  # Made optional for quick add
    phone = db.Column(db.String(20), nullable=True)
    
    # Demographics
    gender = db.Column(db.String(10), nullable=False)
    birth_year = db.Column(db.Integer, nullable=True)
    
    # Role
    is_captain = db.Column(db.Boolean, default=False)
    
    # Shirt info (can be filled later)
    shirt_name = db.Column(db.String(50), nullable=True)
    shirt_size = db.Column(db.String(10), nullable=True)
    
    # Profile (can be filled later)
    photo_filename = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    # Social Media (optional)
    instagram = db.Column(db.String(100), nullable=True)
    tiktok = db.Column(db.String(100), nullable=True)
    youtube = db.Column(db.String(200), nullable=True)
    twitter = db.Column(db.String(100), nullable=True)
    
    # Optional extras
    video_url = db.Column(db.String(500), nullable=True)
    dupr_rating = db.Column(db.String(10), nullable=True)
    additional_photos = db.Column(db.Text, nullable=True)  # JSON array of photo URLs

    # WhatsApp tracking
    whatsapp_sent_at = db.Column(db.DateTime, nullable=True)

    # Registration status
    status = db.Column(db.String(20), default='incomplete', index=True)  # Indexed for status filtering

    # ========== NEW: Profile completion token ==========
    profile_token = db.Column(db.String(64), unique=True, nullable=True, index=True)  # Indexed for token lookups

    # Nach profile_token hinzufÃ¼gen:
    checked_in = db.Column(db.Boolean, default=False)
    checked_in_at = db.Column(db.DateTime, nullable=True)

    # ========== GDPR / CHECK-IN CONSENT ==========
    privacy_accepted = db.Column(db.Boolean, default=False)
    privacy_accepted_at = db.Column(db.DateTime, nullable=True)
    whatsapp_optin = db.Column(db.Boolean, default=False)
    marketing_optin = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Language preference
    preferred_language = db.Column(db.String(10), default='EN')
    
    # Relationships
    team = db.relationship('PCLTeam', back_populates='registrations')
    player = db.relationship('Player', back_populates='pcl_registrations')
    
    def __repr__(self):
        return f'<PCLRegistration {self.first_name} {self.last_name}>'
    
    # ========== NEW: Token methods ==========
    def generate_profile_token(self):
        """Generate a unique token for profile completion"""
        self.profile_token = secrets.token_urlsafe(32)
        return self.profile_token
    
    def get_profile_url(self, base_url='https://pickleballconnect.eu'):
        """Get the profile completion URL"""
        if not self.profile_token:
            self.generate_profile_token()
        return f"{base_url}/pcl/complete/{self.profile_token}"
    
    def check_completeness(self):
        """Check if registration is complete and update status"""
        required_fields = [
            self.first_name,
            self.last_name,
            self.gender,
            self.shirt_name,
            self.shirt_size,
            self.photo_filename,
            self.bio
        ]
        
        if all(required_fields):
            self.status = 'complete'
        else:
            self.status = 'incomplete'
        
        return self.status == 'complete'
    
    def get_missing_fields(self):
        """Get list of missing required fields"""
        missing = []
        if not self.photo_filename:
            missing.append('photo')
        if not self.bio:
            missing.append('bio')
        if not self.shirt_name:
            missing.append('shirt_name')
        if not self.shirt_size:
            missing.append('shirt_size')
        return missing
    
    def get_missing_fields_translated(self, lang='EN'):
        """Get translated list of missing fields"""
        translations = {
            'EN': {'photo': 'Photo', 'bio': 'Bio', 'shirt_name': 'Shirt Name', 'shirt_size': 'Shirt Size'},
            'DE': {'photo': 'Foto', 'bio': 'Bio', 'shirt_name': 'Shirt-Name', 'shirt_size': 'Shirt-GrÃƒÂ¶ÃƒÅ¸e'},
            'ES': {'photo': 'Foto', 'bio': 'Bio', 'shirt_name': 'Nombre camiseta', 'shirt_size': 'Talla'},
            'FR': {'photo': 'Photo', 'bio': 'Bio', 'shirt_name': 'Nom maillot', 'shirt_size': 'Taille'}
        }
        t = translations.get(lang, translations['EN'])
        return [t.get(f, f) for f in self.get_missing_fields()]
    
    def get_display_name(self):
        """Get formatted display name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_social_links(self):
        """Get dictionary of social media links"""
        links = {}
        if self.instagram:
            handle = self.instagram.replace('@', '')
            links['instagram'] = f"https://instagram.com/{handle}"
        if self.tiktok:
            handle = self.tiktok.replace('@', '')
            links['tiktok'] = f"https://tiktok.com/@{handle}"
        if self.youtube:
            links['youtube'] = self.youtube
        if self.twitter:
            handle = self.twitter.replace('@', '')
            links['twitter'] = f"https://x.com/{handle}"
        return links


# ============================================================================
# COACHING MODELS
# ============================================================================

class Workshop(db.Model):
    """Workshop/Clinic for coaching"""
    __tablename__ = 'workshop'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    workshop_type = db.Column(db.String(50), default='workshop')
    topic = db.Column(db.String(200), nullable=True)
    
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    participants = db.relationship('WorkshopParticipant', back_populates='workshop', lazy='dynamic')
    
    def __repr__(self):
        return f'<Workshop {self.name}>'


class WorkshopParticipant(db.Model):
    """Link between workshop and player with coaching notes"""
    __tablename__ = 'workshop_participant'
    
    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    workshop = db.relationship('Workshop', back_populates='participants')
    player = db.relationship('Player')
    
    def __repr__(self):
        return f'<WorkshopParticipant {self.player_id} @ {self.workshop_id}>'


class VideoLibrary(db.Model):
    """Training videos linked to weakness categories"""
    __tablename__ = 'video_library'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    youtube_url = db.Column(db.String(500), nullable=False)
    
    category = db.Column(db.String(50), nullable=False)
    
    description = db.Column(db.Text, nullable=True)
    
    language = db.Column(db.String(10), default='EN')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Video {self.title}>'


# ============================================================================
# SPONSOR MODELS
# ============================================================================

class Sponsor(db.Model):
    """Sponsor for events and tournaments"""
    __tablename__ = 'sponsor'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    logo_url = db.Column(db.String(500), nullable=True)
    website_url = db.Column(db.String(500), nullable=True)
    tier = db.Column(db.String(20), nullable=False, default='partner')  # title/gold/silver/bronze/partner

    # Tracking
    tracking_url = db.Column(db.String(500), nullable=True)
    tracking_code = db.Column(db.String(100), nullable=True)

    # WhatsApp texts per language
    whatsapp_text_en = db.Column(db.Text, nullable=True)
    whatsapp_text_de = db.Column(db.Text, nullable=True)
    whatsapp_text_es = db.Column(db.Text, nullable=True)
    whatsapp_text_fr = db.Column(db.Text, nullable=True)

    # Boarding pass
    show_on_boarding_pass = db.Column(db.Boolean, default=False)
    boarding_pass_text = db.Column(db.String(200), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)

    # Revenue
    revenue_model = db.Column(db.String(20), nullable=True)  # flat_fee/cpc/cpa/commission/barter
    revenue_amount = db.Column(db.Float, nullable=True)

    # Contact
    contact_person = db.Column(db.String(200), nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    placements = db.relationship('EventSponsor', back_populates='sponsor', lazy='dynamic')

    def __repr__(self):
        return f'<Sponsor {self.name}>'

    @property
    def tier_badge_class(self):
        classes = {
            'title': 'bg-warning text-dark',
            'gold': 'bg-warning text-dark',
            'silver': 'bg-secondary',
            'bronze': 'bg-bronze',
            'partner': 'bg-info text-dark',
        }
        return classes.get(self.tier, 'bg-secondary')

    @property
    def tier_label(self):
        labels = {
            'title': 'Title Sponsor',
            'gold': 'Gold',
            'silver': 'Silver',
            'bronze': 'Bronze',
            'partner': 'Partner',
        }
        return labels.get(self.tier, self.tier)

    def get_whatsapp_text(self, lang='EN'):
        lang = lang.upper()
        texts = {
            'EN': self.whatsapp_text_en,
            'DE': self.whatsapp_text_de,
            'ES': self.whatsapp_text_es,
            'FR': self.whatsapp_text_fr,
        }
        return texts.get(lang) or self.whatsapp_text_en or ''

    def get_tracking_link(self):
        if self.tracking_url:
            url = self.tracking_url
            if self.tracking_code:
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}utm_source=pickleball_connect&utm_campaign={self.tracking_code}"
            return url
        return self.website_url or ''


class EventSponsor(db.Model):
    """Junction table linking sponsors to events/tournaments"""
    __tablename__ = 'event_sponsor'

    id = db.Column(db.Integer, primary_key=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsor.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    pcl_tournament_id = db.Column(db.Integer, db.ForeignKey('pcl_tournament.id'), nullable=True)

    # Display settings
    show_in_whatsapp = db.Column(db.Boolean, default=True)
    show_on_boarding_pass = db.Column(db.Boolean, default=True)
    show_on_event_page = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    tier_override = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    sponsor = db.relationship('Sponsor', back_populates='placements')
    event = db.relationship('Event', backref='sponsor_placements')
    pcl_tournament = db.relationship('PCLTournament', backref='sponsor_placements')

    def __repr__(self):
        return f'<EventSponsor {self.sponsor_id} -> Event {self.event_id or self.pcl_tournament_id}>'

    @property
    def effective_tier(self):
        return self.tier_override or self.sponsor.tier


def get_whatsapp_sponsor_block(event_id=None, pcl_tournament_id=None, language='EN'):
    """Return formatted sponsor text block for WhatsApp messages."""
    query = EventSponsor.query.filter_by(is_active=True, show_in_whatsapp=True)
    if event_id:
        query = query.filter_by(event_id=event_id)
    elif pcl_tournament_id:
        query = query.filter_by(pcl_tournament_id=pcl_tournament_id)
    else:
        return ''

    placements = query.join(Sponsor).filter(Sponsor.is_active == True).order_by(
        EventSponsor.display_order
    ).all()

    if not placements:
        return ''

    lines = []
    for p in placements:
        text = p.sponsor.get_whatsapp_text(language)
        if text:
            lines.append(text)

    if not lines:
        return ''

    headers = {
        'EN': 'Supported by',
        'DE': 'Unterstuetzt von',
        'ES': 'Patrocinado por',
        'FR': 'Soutenu par',
    }
    header = headers.get(language.upper(), headers['EN'])
    block = f"\n\n---\n{header}:\n" + "\n".join(lines)
    return block


def get_boarding_pass_sponsors(event_id=None, pcl_tournament_id=None):
    """Return list of sponsor dicts for boarding pass display."""
    query = EventSponsor.query.filter_by(is_active=True, show_on_boarding_pass=True)
    if event_id:
        query = query.filter_by(event_id=event_id)
    elif pcl_tournament_id:
        query = query.filter_by(pcl_tournament_id=pcl_tournament_id)
    else:
        return []

    placements = query.join(Sponsor).filter(
        Sponsor.is_active == True,
        Sponsor.show_on_boarding_pass == True
    ).order_by(EventSponsor.display_order).all()

    result = []
    for p in placements:
        result.append({
            'name': p.sponsor.name,
            'logo_url': p.sponsor.logo_url,
            'website_url': p.sponsor.get_tracking_link(),
            'tier': p.effective_tier,
            'text': p.sponsor.boarding_pass_text or p.sponsor.name,
        })
    return result


# ============================================================================
# CONSTANTS
# ============================================================================

WEAKNESS_CATEGORIES = [
    ('dink_control', 'Dink Control'),
    ('third_shot_drop', 'Third Shot Drop'),
    ('serve', 'Serve / Aufschlag'),
    ('return', 'Return'),
    ('backhand', 'Backhand / RÃƒÂ¼ckhand'),
    ('forehand', 'Forehand / Vorhand'),
    ('volley', 'Volley'),
    ('footwork', 'Footwork'),
    ('court_positioning', 'Court Positioning'),
    ('shot_selection', 'Shot Selection'),
    ('mental', 'Mental / Consistency'),
]

SHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']

COUNTRY_FLAGS = {
    # Western Europe
    'GER': 'Ã°Å¸â€¡Â©Ã°Å¸â€¡Âª',
    'FRA': 'Ã°Å¸â€¡Â«Ã°Å¸â€¡Â·',
    'NED': 'Ã°Å¸â€¡Â³Ã°Å¸â€¡Â±',
    'BEL': 'Ã°Å¸â€¡Â§Ã°Å¸â€¡Âª',
    'LUX': 'Ã°Å¸â€¡Â±Ã°Å¸â€¡Âº',
    'AUT': 'Ã°Å¸â€¡Â¦Ã°Å¸â€¡Â¹',
    'SUI': 'Ã°Å¸â€¡Â¨Ã°Å¸â€¡Â­',
    
    # Southern Europe
    'ESP': 'Ã°Å¸â€¡ÂªÃ°Å¸â€¡Â¸',
    'POR': 'Ã°Å¸â€¡ÂµÃ°Å¸â€¡Â¹',
    'ITA': 'Ã°Å¸â€¡Â®Ã°Å¸â€¡Â¹',
    'GRE': 'Ã°Å¸â€¡Â¬Ã°Å¸â€¡Â·',
    'MLT': 'Ã°Å¸â€¡Â²Ã°Å¸â€¡Â¹',
    'CYP': 'Ã°Å¸â€¡Â¨Ã°Å¸â€¡Â¾',
    'AND': 'Ã°Å¸â€¡Â¦Ã°Å¸â€¡Â©',
    'MON': 'Ã°Å¸â€¡Â²Ã°Å¸â€¡Â¨',
    'SMR': 'Ã°Å¸â€¡Â¸Ã°Å¸â€¡Â²',
    'VAT': 'Ã°Å¸â€¡Â»Ã°Å¸â€¡Â¦',
    
    # Northern Europe
    'ENG': 'Ã°Å¸ÂÂ´Ã³Â ÂÂ§Ã³Â ÂÂ¢Ã³Â ÂÂ¥Ã³Â ÂÂ®Ã³Â ÂÂ§Ã³Â ÂÂ¿',
    'SCO': 'Ã°Å¸ÂÂ´Ã³Â ÂÂ§Ã³Â ÂÂ¢Ã³Â ÂÂ³Ã³Â ÂÂ£Ã³Â ÂÂ´Ã³Â ÂÂ¿',
    'WAL': 'Ã°Å¸ÂÂ´Ã³Â ÂÂ§Ã³Â ÂÂ¢Ã³Â ÂÂ·Ã³Â ÂÂ¬Ã³Â ÂÂ³Ã³Â ÂÂ¿',
    'NIR': 'Ã°Å¸â€¡Â¬Ã°Å¸â€¡Â§',
    'GBR': 'Ã°Å¸â€¡Â¬Ã°Å¸â€¡Â§',
    'IRL': 'Ã°Å¸â€¡Â®Ã°Å¸â€¡Âª',
    'SWE': 'Ã°Å¸â€¡Â¸Ã°Å¸â€¡Âª',
    'NOR': 'Ã°Å¸â€¡Â³Ã°Å¸â€¡Â´',
    'DEN': 'Ã°Å¸â€¡Â©Ã°Å¸â€¡Â°',
    'FIN': 'Ã°Å¸â€¡Â«Ã°Å¸â€¡Â®',
    'ISL': 'Ã°Å¸â€¡Â®Ã°Å¸â€¡Â¸',
    
    # Central Europe
    'POL': 'Ã°Å¸â€¡ÂµÃ°Å¸â€¡Â±',
    'CZE': 'Ã°Å¸â€¡Â¨Ã°Å¸â€¡Â¿',
    'SVK': 'Ã°Å¸â€¡Â¸Ã°Å¸â€¡Â°',
    'HUN': 'Ã°Å¸â€¡Â­Ã°Å¸â€¡Âº',
    'SLO': 'Ã°Å¸â€¡Â¸Ã°Å¸â€¡Â®',
    'CRO': 'Ã°Å¸â€¡Â­Ã°Å¸â€¡Â·',
    
    # Eastern Europe
    'RUS': 'Ã°Å¸â€¡Â·Ã°Å¸â€¡Âº',
    'UKR': 'Ã°Å¸â€¡ÂºÃ°Å¸â€¡Â¦',
    'BLR': 'Ã°Å¸â€¡Â§Ã°Å¸â€¡Â¾',
    'MDA': 'Ã°Å¸â€¡Â²Ã°Å¸â€¡Â©',
    'ROM': 'Ã°Å¸â€¡Â·Ã°Å¸â€¡Â´',
    'BUL': 'Ã°Å¸â€¡Â§Ã°Å¸â€¡Â¬',
    
    # Baltic States
    'EST': 'Ã°Å¸â€¡ÂªÃ°Å¸â€¡Âª',
    'LAT': 'Ã°Å¸â€¡Â±Ã°Å¸â€¡Â»',
    'LTU': 'Ã°Å¸â€¡Â±Ã°Å¸â€¡Â¹',
    
    # Balkans
    'SRB': 'Ã°Å¸â€¡Â·Ã°Å¸â€¡Â¸',
    'MNE': 'Ã°Å¸â€¡Â²Ã°Å¸â€¡Âª',
    'BIH': 'Ã°Å¸â€¡Â§Ã°Å¸â€¡Â¦',
    'MKD': 'Ã°Å¸â€¡Â²Ã°Å¸â€¡Â°',
    'ALB': 'Ã°Å¸â€¡Â¦Ã°Å¸â€¡Â±',
    'KOS': 'Ã°Å¸â€¡Â½Ã°Å¸â€¡Â°',
    
    # Other
    'TUR': 'Ã°Å¸â€¡Â¹Ã°Å¸â€¡Â·',
    'GEO': 'Ã°Å¸â€¡Â¬Ã°Å¸â€¡Âª',
    'ARM': 'Ã°Å¸â€¡Â¦Ã°Å¸â€¡Â²',
    'AZE': 'Ã°Å¸â€¡Â¦Ã°Å¸â€¡Â¿',
    
    # Special
    'ASIA': 'Ã°Å¸Å’Â',
    'EUR': 'Ã°Å¸â€¡ÂªÃ°Å¸â€¡Âº',
    'WORLD': 'Ã°Å¸Å’Â',
}


# ============================================================================
# CHECK-IN SYSTEM MODELS
# ============================================================================


class TournamentCheckinSettings(db.Model):
    """Tournament-specific check-in settings including liability waiver"""
    __tablename__ = 'tournament_checkin_settings'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    liability_waiver_text = db.Column(db.Text, nullable=True)
    liability_waiver_lang = db.Column(db.String(5), default='en')
    liability_waiver_version = db.Column(db.String(20), default='v1')
    welcome_pack_items = db.Column(db.JSON, default=lambda: {"tshirt": True})
    checkin_open = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tournament = db.relationship('Event', backref='checkin_settings_rel')


class TournamentParticipant(db.Model):
    """Participants imported from external systems (Pickleball Global CSV)"""
    __tablename__ = 'tournament_participant'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    external_id = db.Column(db.String(50), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    division = db.Column(db.String(100), nullable=True)
    partner_name = db.Column(db.String(200), nullable=True)
    dupr_rating = db.Column(db.String(10), nullable=True)
    checkin_token = db.Column(db.String(64), unique=True, nullable=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    import_source = db.Column(db.String(50), default='pickleball_global')

    tournament = db.relationship('Event', backref='tournament_participants')
    checkin = db.relationship('TournamentCheckin', back_populates='participant', uselist=False)

    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'external_id', name='unique_participant_per_tournament'),
    )

    def generate_checkin_token(self):
        self.checkin_token = secrets.token_urlsafe(32)
        return self.checkin_token

    def get_checkin_url(self, base_url='https://pickleballconnect.eu'):
        if not self.checkin_token:
            self.generate_checkin_token()
        return f"{base_url}/checkin/self/{self.checkin_token}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_checked_in(self):
        return self.checkin is not None


class TournamentCheckin(db.Model):
    """Check-in records with insurance data and welcome pack tracking"""
    __tablename__ = 'tournament_checkin'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('tournament_participant.id'), nullable=False)
    emergency_contact_name = db.Column(db.String(200), nullable=True)
    emergency_contact_phone = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    liability_accepted = db.Column(db.Boolean, nullable=False, default=False)
    liability_accepted_at = db.Column(db.DateTime, nullable=True)
    liability_waiver_version = db.Column(db.String(20), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)
    whatsapp_optin = db.Column(db.Boolean, default=False)
    preferred_language = db.Column(db.String(5), default='en')
    tshirt_size = db.Column(db.String(10), nullable=True)
    welcome_pack_received = db.Column(db.Boolean, default=False)
    welcome_pack_received_at = db.Column(db.DateTime, nullable=True)
    welcome_pack_notes = db.Column(db.Text, nullable=True)
    checked_in_at = db.Column(db.DateTime, default=datetime.utcnow)
    checked_in_by = db.Column(db.String(100), nullable=True)
    checkin_method = db.Column(db.String(20), default='qr_self')
    device_id = db.Column(db.String(100), nullable=True)
    synced_to_server = db.Column(db.Boolean, default=True)
    synced_at = db.Column(db.DateTime, nullable=True)
    offline_created_at = db.Column(db.DateTime, nullable=True)

    tournament = db.relationship('Event')
    participant = db.relationship('TournamentParticipant', back_populates='checkin')

    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'participant_id', name='unique_checkin_per_participant'),
    )


class CheckinSyncQueue(db.Model):
    """Queue for offline check-ins waiting to be synced"""
    __tablename__ = 'checkin_sync_queue'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=False)
    tournament_id = db.Column(db.Integer, nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    created_offline_at = db.Column(db.DateTime, nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    sync_error = db.Column(db.Text, nullable=True)


# ============================================================================
# WPC MODELS (World Pickleball Championship)
# ============================================================================

class WPCPlayer(db.Model):
    __tablename__ = 'wpc_player'
    
    id = db.Column(db.Integer, primary_key=True)
    pgid = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    dupr_id = db.Column(db.String(20), nullable=True)
    dupr_rating = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    address = db.Column(db.Text, nullable=True)
    checkin_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    checked_in = db.Column(db.Boolean, default=False)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    privacy_accepted = db.Column(db.Boolean, default=False)
    privacy_accepted_at = db.Column(db.DateTime, nullable=True)
    whatsapp_optin = db.Column(db.Boolean, default=False)
    marketing_optin = db.Column(db.Boolean, default=False)
    preferred_language = db.Column(db.String(5), default='EN')
    welcome_pack_received = db.Column(db.Boolean, default=False)
    welcome_pack_received_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    registrations = db.relationship('WPCRegistration', back_populates='player', lazy='dynamic')
    
    def generate_checkin_token(self):
        self.checkin_token = secrets.token_urlsafe(32)
        return self.checkin_token
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_phone(self):
        return bool(self.phone and self.phone.strip() and self.phone.strip() != '-')


class WPCRegistration(db.Model):
    __tablename__ = 'wpc_registration'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('wpc_player.id'), nullable=False)
    division_type = db.Column(db.String(50), nullable=True)
    division_name = db.Column(db.String(255), nullable=True)
    age_category = db.Column(db.String(20), nullable=True)
    skill_level = db.Column(db.String(50), nullable=True)
    partner_name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    player = db.relationship('WPCPlayer', back_populates='registrations')

class WPCMatch(db.Model):
    __tablename__ = 'wpc_match'
    
    id = db.Column(db.Integer, primary_key=True)
    match_date = db.Column(db.Date, nullable=False)
    match_time = db.Column(db.Time, nullable=False)
    court = db.Column(db.String(20))
    division = db.Column(db.String(100))
    flight = db.Column(db.String(50))
    match_number = db.Column(db.String(50))
    player1_name = db.Column(db.String(200))
    player2_name = db.Column(db.String(200))
    opponent1_name = db.Column(db.String(200))
    opponent2_name = db.Column(db.String(200))
    score = db.Column(db.String(50))
    is_doubles = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================================
# USER MODEL (Directors & Admins only)
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='director')
    
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    organization = db.Column(db.String(200))
    
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split('@')[0]
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)