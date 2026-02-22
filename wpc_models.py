
# ============================================================================
# WPC MODELS (World Pickleball Championship)
# ============================================================================

class WPCPlayer(db.Model):
    """WPC Player - unique players from Pickleball Global"""
    __tablename__ = 'wpc_player'
    
    id = db.Column(db.Integer, primary_key=True)
    pgid = db.Column(db.String(20), unique=True, nullable=False)  # Pickleball Global ID
    
    # Personal info
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # DUPR
    dupr_id = db.Column(db.String(20), nullable=True)
    dupr_rating = db.Column(db.String(50), nullable=True)
    
    # Demographics
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Check-in
    checkin_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    checked_in = db.Column(db.Boolean, default=False)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    
    # GDPR Consent
    privacy_accepted = db.Column(db.Boolean, default=False)
    privacy_accepted_at = db.Column(db.DateTime, nullable=True)
    whatsapp_optin = db.Column(db.Boolean, default=False)
    marketing_optin = db.Column(db.Boolean, default=False)
    preferred_language = db.Column(db.String(5), default='EN')
    
    # Welcome Pack
    welcome_pack_received = db.Column(db.Boolean, default=False)
    welcome_pack_received_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    registrations = db.relationship('WPCRegistration', back_populates='player', lazy='dynamic')
    
    def __repr__(self):
        return f'<WPCPlayer {self.first_name} {self.last_name}>'
    
    def generate_checkin_token(self):
        """Generate unique check-in token"""
        self.checkin_token = secrets.token_urlsafe(32)
        return self.checkin_token
    
    def get_checkin_url(self, base_url='https://pickleballconnect.eu'):
        """Get check-in URL"""
        if not self.checkin_token:
            self.generate_checkin_token()
        return f"{base_url}/wpc/checkin/{self.checkin_token}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_phone(self):
        return bool(self.phone and self.phone.strip() and self.phone.strip() != '-')


class WPCRegistration(db.Model):
    """WPC Registration - player in a division/category"""
    __tablename__ = 'wpc_registration'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('wpc_player.id'), nullable=False)
    
    # Division info
    division_type = db.Column(db.String(50), nullable=True)  # MENS DOUBLES, MIXED DOUBLES, etc.
    division_name = db.Column(db.String(255), nullable=True)  # Full division name
    age_category = db.Column(db.String(20), nullable=True)  # 19+, 35+, 50+
    skill_level = db.Column(db.String(50), nullable=True)  # Advanced, Elite, etc.
    partner_name = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    player = db.relationship('WPCPlayer', back_populates='registrations')
    
    def __repr__(self):
        return f'<WPCRegistration {self.player_id} - {self.division_type}>'
