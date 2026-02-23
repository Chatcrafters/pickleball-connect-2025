"""
Court Manager Scoring System
- Court Managers submit scores via mobile-friendly token-based URLs (no login)
- Tournament Directors see live dashboard with auto-refresh
- Integrates with existing Event model
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from models import db, Event, Player
from datetime import datetime
import secrets

scoring = Blueprint('scoring', __name__, url_prefix='/scoring')


# ============================================================================
# DATABASE MODELS (will be added to models.py)
# ============================================================================

class Court(db.Model):
    """A court at a tournament event"""
    __tablename__ = 'court'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    court_number = db.Column(db.Integer, nullable=False)
    court_name = db.Column(db.String(50), nullable=True)  # e.g. "Center Court"
    
    # Court Manager access token (no login needed)
    manager_token = db.Column(db.String(64), unique=True, nullable=False)
    manager_name = db.Column(db.String(100), nullable=True)  # Name of assigned court manager
    
    # Status
    status = db.Column(db.String(20), default='available')  # available, in_play, paused
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    event = db.relationship('Event', backref='courts')
    matches = db.relationship('Match', back_populates='court', lazy='dynamic')
    
    def __repr__(self):
        return f'<Court {self.court_number} @ Event {self.event_id}>'
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(16)
    
    def get_manager_url(self, base_url='https://pickleballconnect.eu'):
        return f"{base_url}/scoring/court/{self.manager_token}"


class Match(db.Model):
    """A single match (one set) between two teams/players"""
    __tablename__ = 'game_match'  # "match" is a reserved keyword in PostgreSQL!
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=True)
    
    # Match identification
    match_number = db.Column(db.Integer, nullable=True)  # Sequential match number
    round_name = db.Column(db.String(50), nullable=True)  # e.g. "Round Robin", "Quarter Final"
    category = db.Column(db.String(50), nullable=True)  # e.g. "Mixed Doubles +19", "Men's Singles"
    
    # Team/Player names (flexible - works with or without player IDs)
    team1_name = db.Column(db.String(200), nullable=False)
    team2_name = db.Column(db.String(200), nullable=False)
    
    # Optional player references
    team1_player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    team1_player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    team2_player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    team2_player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    
    # Score (single set)
    score_team1 = db.Column(db.Integer, nullable=True)
    score_team2 = db.Column(db.Integer, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='scheduled')  # scheduled, in_play, completed, cancelled
    
    # Timestamps
    scheduled_time = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    score_submitted_at = db.Column(db.DateTime, nullable=True)
    scoresheet_verified = db.Column(db.Boolean, default=False)  # Paper scoresheet confirmed
    
    # Who submitted the score
    submitted_by_court_id = db.Column(db.Integer, nullable=True)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    event = db.relationship('Event', backref='matches')
    court = db.relationship('Court', back_populates='matches')
    
    def __repr__(self):
        return f'<Match {self.match_number}: {self.team1_name} vs {self.team2_name}>'
    
    def get_winner(self):
        if self.score_team1 is not None and self.score_team2 is not None:
            if self.score_team1 > self.score_team2:
                return self.team1_name
            elif self.score_team2 > self.score_team1:
                return self.team2_name
        return None
    
    def get_score_display(self):
        if self.score_team1 is not None and self.score_team2 is not None:
            return f"{self.score_team1} - {self.score_team2}"
        return "-- : --"


# ============================================================================
# TOURNAMENT DIRECTOR: SETUP & MANAGEMENT
# ============================================================================

@scoring.route('/setup/<int:event_id>')
def setup_event(event_id):
    """Setup courts and matches for an event"""
    event = Event.query.get_or_404(event_id)
    courts = Court.query.filter_by(event_id=event_id).order_by(Court.court_number).all()
    matches = Match.query.filter_by(event_id=event_id).order_by(Match.match_number).all()
    
    return render_template('scoring/setup.html', event=event, courts=courts, matches=matches)


@scoring.route('/setup/<int:event_id>/create-courts', methods=['POST'])
def create_courts(event_id):
    """Create courts for an event"""
    event = Event.query.get_or_404(event_id)
    num_courts = int(request.form.get('num_courts', 9))
    
    # Delete existing courts first (if requested)
    if request.form.get('replace_existing'):
        Court.query.filter_by(event_id=event_id).delete()
    
    for i in range(1, num_courts + 1):
        court = Court(
            event_id=event_id,
            court_number=i,
            manager_token=Court.generate_token(),
            manager_name=request.form.get(f'manager_name_{i}', '')
        )
        db.session.add(court)
    
    try:
        db.session.commit()
        flash(f'{num_courts} Courts erstellt!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.setup_event', event_id=event_id))


@scoring.route('/setup/<int:event_id>/add-match', methods=['POST'])
def add_match(event_id):
    """Add a match to the event"""
    event = Event.query.get_or_404(event_id)
    
    # Get next match number
    last_match = Match.query.filter_by(event_id=event_id).order_by(Match.match_number.desc()).first()
    next_number = (last_match.match_number + 1) if last_match and last_match.match_number else 1
    
    match = Match(
        event_id=event_id,
        match_number=int(request.form.get('match_number', next_number)),
        round_name=request.form.get('round_name', ''),
        category=request.form.get('category', ''),
        team1_name=request.form['team1_name'],
        team2_name=request.form['team2_name'],
        court_id=int(request.form['court_id']) if request.form.get('court_id') else None,
        scheduled_time=datetime.strptime(request.form['scheduled_time'], '%Y-%m-%dT%H:%M') if request.form.get('scheduled_time') else None,
        status='scheduled'
    )
    
    try:
        db.session.add(match)
        db.session.commit()
        flash(f'Match #{match.match_number} erstellt!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.setup_event', event_id=event_id))


@scoring.route('/setup/<int:event_id>/import-matches', methods=['POST'])
def import_matches(event_id):
    """Bulk import matches from text input"""
    event = Event.query.get_or_404(event_id)
    matches_text = request.form.get('matches_text', '')
    category = request.form.get('category', '')
    round_name = request.form.get('round_name', '')
    
    # Get next match number
    last_match = Match.query.filter_by(event_id=event_id).order_by(Match.match_number.desc()).first()
    next_number = (last_match.match_number + 1) if last_match and last_match.match_number else 1
    
    count = 0
    for line in matches_text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Expected format: "Team A vs Team B" or "Team A - Team B"
        parts = None
        for sep in [' vs ', ' vs. ', ' - ', ' gegen ']:
            if sep in line:
                parts = line.split(sep, 1)
                break
        
        if parts and len(parts) == 2:
            match = Match(
                event_id=event_id,
                match_number=next_number + count,
                round_name=round_name,
                category=category,
                team1_name=parts[0].strip(),
                team2_name=parts[1].strip(),
                status='scheduled'
            )
            db.session.add(match)
            count += 1
    
    try:
        db.session.commit()
        flash(f'{count} Matches importiert!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.setup_event', event_id=event_id))


@scoring.route('/match/<int:match_id>/assign-court', methods=['POST'])
def assign_court(match_id):
    """Assign a match to a court"""
    match = Match.query.get_or_404(match_id)
    court_id = request.form.get('court_id')
    
    match.court_id = int(court_id) if court_id else None
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.setup_event', event_id=match.event_id))


@scoring.route('/match/<int:match_id>/delete', methods=['POST'])
def delete_match(match_id):
    """Delete a match"""
    match = Match.query.get_or_404(match_id)
    event_id = match.event_id
    
    try:
        db.session.delete(match)
        db.session.commit()
        flash('Match geloescht!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.setup_event', event_id=event_id))


# ============================================================================
# TOURNAMENT DIRECTOR: LIVE DASHBOARD
# ============================================================================

@scoring.route('/live/<int:event_id>')
def live_dashboard(event_id):
    """Live scoring dashboard for tournament directors"""
    event = Event.query.get_or_404(event_id)
    courts = Court.query.filter_by(event_id=event_id).order_by(Court.court_number).all()
    
    return render_template('scoring/live_dashboard.html', event=event, courts=courts)


@scoring.route('/api/live/<int:event_id>')
def api_live_data(event_id):
    """API endpoint for live dashboard updates (AJAX polling)"""
    event = Event.query.get_or_404(event_id)
    courts = Court.query.filter_by(event_id=event_id).order_by(Court.court_number).all()
    
    courts_data = []
    for court in courts:
        # Get current/latest match on this court
        current_match = Match.query.filter_by(
            court_id=court.id, status='in_play'
        ).first()
        
        latest_completed = Match.query.filter_by(
            court_id=court.id, status='completed'
        ).order_by(Match.completed_at.desc()).first()
        
        # Next scheduled match
        next_match = Match.query.filter_by(
            court_id=court.id, status='scheduled'
        ).order_by(Match.match_number).first()
        
        court_info = {
            'id': court.id,
            'number': court.court_number,
            'name': court.court_name or f'Court {court.court_number}',
            'manager': court.manager_name or 'Nicht zugewiesen',
            'status': court.status,
            'current_match': None,
            'latest_result': None,
            'next_match': None
        }
        
        if current_match:
            court_info['current_match'] = {
                'id': current_match.id,
                'number': current_match.match_number,
                'team1': current_match.team1_name,
                'team2': current_match.team2_name,
                'category': current_match.category,
                'started_at': current_match.started_at.strftime('%H:%M') if current_match.started_at else None
            }
        
        if latest_completed:
            court_info['latest_result'] = {
                'id': latest_completed.id,
                'number': latest_completed.match_number,
                'team1': latest_completed.team1_name,
                'team2': latest_completed.team2_name,
                'score1': latest_completed.score_team1,
                'score2': latest_completed.score_team2,
                'category': latest_completed.category,
                'completed_at': latest_completed.completed_at.strftime('%H:%M') if latest_completed.completed_at else None,
                'verified': latest_completed.scoresheet_verified
            }
        
        if next_match:
            court_info['next_match'] = {
                'id': next_match.id,
                'number': next_match.match_number,
                'team1': next_match.team1_name,
                'team2': next_match.team2_name,
                'category': next_match.category
            }
        
        courts_data.append(court_info)
    
    # Recent scores (last 20)
    recent = Match.query.filter_by(
        event_id=event_id, status='completed'
    ).order_by(Match.completed_at.desc()).limit(20).all()
    
    recent_scores = [{
        'id': m.id,
        'number': m.match_number,
        'team1': m.team1_name,
        'team2': m.team2_name,
        'score1': m.score_team1,
        'score2': m.score_team2,
        'category': m.category,
        'court': m.court.court_number if m.court else None,
        'completed_at': m.completed_at.strftime('%H:%M') if m.completed_at else None,
        'verified': m.scoresheet_verified
    } for m in recent]
    
    # Stats
    total_matches = Match.query.filter_by(event_id=event_id).count()
    completed_matches = Match.query.filter_by(event_id=event_id, status='completed').count()
    in_play = Match.query.filter_by(event_id=event_id, status='in_play').count()
    unverified = Match.query.filter_by(event_id=event_id, status='completed', scoresheet_verified=False).count()
    
    return jsonify({
        'courts': courts_data,
        'recent_scores': recent_scores,
        'stats': {
            'total': total_matches,
            'completed': completed_matches,
            'in_play': in_play,
            'scheduled': total_matches - completed_matches - in_play,
            'unverified': unverified
        },
        'timestamp': datetime.utcnow().strftime('%H:%M:%S')
    })


@scoring.route('/match/<int:match_id>/verify', methods=['POST'])
def verify_match(match_id):
    """Verify a match score (scoresheet confirmed)"""
    match = Match.query.get_or_404(match_id)
    match.scoresheet_verified = True
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# COURT MANAGER: MOBILE SCORING INTERFACE (TOKEN-BASED)
# ============================================================================

@scoring.route('/court/<token>')
def court_manager(token):
    """Court Manager scoring page (mobile-friendly, no login)"""
    court = Court.query.filter_by(manager_token=token).first_or_404()
    event = court.event
    
    # Get matches assigned to this court
    current_match = Match.query.filter_by(court_id=court.id, status='in_play').first()
    scheduled_matches = Match.query.filter_by(
        court_id=court.id, status='scheduled'
    ).order_by(Match.match_number).all()
    completed_matches = Match.query.filter_by(
        court_id=court.id, status='completed'
    ).order_by(Match.completed_at.desc()).limit(5).all()
    
    # Also get unassigned matches for this event
    unassigned_matches = Match.query.filter_by(
        event_id=event.id, court_id=None, status='scheduled'
    ).order_by(Match.match_number).all()
    
    return render_template('scoring/court_manager.html',
                         court=court,
                         event=event,
                         current_match=current_match,
                         scheduled_matches=scheduled_matches,
                         completed_matches=completed_matches,
                         unassigned_matches=unassigned_matches,
                         token=token)


@scoring.route('/court/<token>/start-match/<int:match_id>', methods=['POST'])
def start_match(token, match_id):
    """Court Manager starts a match"""
    court = Court.query.filter_by(manager_token=token).first_or_404()
    match = Match.query.get_or_404(match_id)
    
    # Assign court if not already assigned
    if not match.court_id:
        match.court_id = court.id
    
    match.status = 'in_play'
    match.started_at = datetime.utcnow()
    court.status = 'in_play'
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.court_manager', token=token))


@scoring.route('/court/<token>/submit-score/<int:match_id>', methods=['POST'])
def submit_score(token, match_id):
    """Court Manager submits the score for a match"""
    court = Court.query.filter_by(manager_token=token).first_or_404()
    match = Match.query.get_or_404(match_id)
    
    score1 = request.form.get('score_team1')
    score2 = request.form.get('score_team2')
    
    if score1 is not None and score2 is not None:
        match.score_team1 = int(score1)
        match.score_team2 = int(score2)
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        match.score_submitted_at = datetime.utcnow()
        match.submitted_by_court_id = court.id
        match.notes = request.form.get('notes', '')
        
        court.status = 'available'
        
        try:
            db.session.commit()
            flash(f'Score eingereicht: {match.team1_name} {score1} - {score2} {match.team2_name}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    else:
        flash('Bitte beide Scores eingeben!', 'warning')
    
    return redirect(url_for('scoring.court_manager', token=token))


@scoring.route('/court/<token>/claim-match/<int:match_id>', methods=['POST'])
def claim_match(token, match_id):
    """Court Manager claims an unassigned match for their court"""
    court = Court.query.filter_by(manager_token=token).first_or_404()
    match = Match.query.get_or_404(match_id)
    
    match.court_id = court.id
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('scoring.court_manager', token=token))


# ============================================================================
# COURT MANAGER LINKS (for Tournament Director)
# ============================================================================

@scoring.route('/links/<int:event_id>')
def court_links(event_id):
    """Show all court manager links (for printing/sharing)"""
    event = Event.query.get_or_404(event_id)
    courts = Court.query.filter_by(event_id=event_id).order_by(Court.court_number).all()
    
    return render_template('scoring/court_links.html', event=event, courts=courts)
