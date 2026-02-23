"""Court Manager Scoring System v2 - Smart Import + Multi-Court Manager"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Event
from datetime import datetime
import secrets

scoring = Blueprint('scoring', __name__, url_prefix='/scoring')


class Tournament(db.Model):
    __tablename__ = 'tournament'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    format = db.Column(db.String(50), nullable=True)
    number_of_courts = db.Column(db.Integer, nullable=True)
    schedule_published = db.Column(db.Boolean, default=False)
    event = db.relationship('Event')
    courts = db.relationship('Court', back_populates='tournament', lazy='dynamic')
    matches = db.relationship('Match', back_populates='tournament', lazy='dynamic')
    @property
    def name(self):
        return self.event.name if self.event else f'Tournament #{self.id}'

class Court(db.Model):
    __tablename__ = 'court'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    court_number = db.Column(db.Integer, nullable=False)
    court_name = db.Column(db.String(50), nullable=True)
    manager_token = db.Column(db.String(64), unique=True, nullable=False)
    manager_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tournament = db.relationship('Tournament', back_populates='courts')
    matches = db.relationship('Match', back_populates='court', lazy='dynamic')
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(16)
    def get_manager_url(self, base_url='https://pickleballconnect.eu'):
        return f"{base_url}/scoring/court/{self.manager_token}"

class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    group_id = db.Column(db.Integer, nullable=True)
    court_number = db.Column(db.Integer, nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    player1_id = db.Column(db.Integer, nullable=True)
    player2_id = db.Column(db.Integer, nullable=True)
    player3_id = db.Column(db.Integer, nullable=True)
    player4_id = db.Column(db.Integer, nullable=True)
    team1_score = db.Column(db.Integer, nullable=True)
    team2_score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), default='scheduled')
    round_name = db.Column(db.String(50), nullable=True)
    match_number = db.Column(db.String(50), nullable=True)
    notified = db.Column(db.Boolean, default=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=True)
    team1_name = db.Column(db.String(200), nullable=True)
    team2_name = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    score_submitted_at = db.Column(db.DateTime, nullable=True)
    scoresheet_verified = db.Column(db.Boolean, default=False)
    submitted_by_court_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    court = db.relationship('Court', back_populates='matches')
    tournament = db.relationship('Tournament', back_populates='matches')
    def get_team1_display(self):
        if self.team1_name: return self.team1_name
        if self.player1_id and self.player2_id: return f"Spieler {self.player1_id} / {self.player2_id}"
        elif self.player1_id: return f"Spieler {self.player1_id}"
        return "Team 1"
    def get_team2_display(self):
        if self.team2_name: return self.team2_name
        if self.player3_id and self.player4_id: return f"Spieler {self.player3_id} / {self.player4_id}"
        elif self.player3_id: return f"Spieler {self.player3_id}"
        return "Team 2"
    def get_score_display(self):
        if self.team1_score is not None and self.team2_score is not None:
            return f"{self.team1_score} - {self.team2_score}"
        return "-- : --"

def get_tournament_or_404(tid):
    t = Tournament.query.get(tid)
    if not t:
        from flask import abort
        abort(404)
    return t

def parse_schedule(raw_text, base_date=''):
    """Parse pickleball.global schedule format"""
    lines = raw_text.strip().split('\n')
    matches = []
    current_cat = ''
    current_round = ''
    counter = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('Division') or line == 'Scores':
            i += 1
            continue
        parts = [p.strip() for p in line.split('\t')]
        has_court = any('Court' in p for p in parts)
        has_time = any(len(p) == 5 and ':' in p and p.replace(':','').isdigit() for p in parts)
        if has_court and has_time:
            team1 = team2 = 'TBD'
            court_num = None
            sched_time = None
            for p in parts:
                p = p.strip()
                if not p or p == '--': continue
                if p.startswith('Court '):
                    try: court_num = int(p.replace('Court ',''))
                    except: pass
                elif len(p)==5 and ':' in p and p.replace(':','').isdigit():
                    if base_date:
                        try: sched_time = datetime.strptime(f'{base_date} {p}', '%Y-%m-%d %H:%M')
                        except: pass
                elif '&' in p:
                    if team1 == 'TBD': team1 = p
                    else: team2 = p
                elif p.startswith('Match ') or 'Semi' in p or 'Final' in p or 'Third' in p:
                    if 'Semi' in p or 'Final' in p or 'Third' in p: current_round = p
                elif any(x in p for x in ['MD','WD','MX','MS','WS']) and '&' not in p and 'Flight' not in p:
                    current_cat = p
                elif 'Flight' in p:
                    current_round = p
            counter += 1
            matches.append({'num': str(counter), 'cat': current_cat, 'rnd': current_round, 'team1': team1, 'team2': team2, 'court': court_num, 'time': sched_time})
        else:
            for p in parts:
                p = p.strip()
                if not p or p == '--': continue
                if any(x in p for x in ['MD','WD','MX','MS','WS']) and '&' not in p and 'Flight' not in p and 'Match' not in p:
                    current_cat = p
                if 'Flight' in p: current_round = p
                if any(kw in p for kw in ['Semi Final','Finals','Third Place','Final']) and 'Flight' not in p:
                    current_round = p
        i += 1
    return matches


@scoring.route('/setup/<int:tournament_id>')
def setup_tournament(tournament_id):
    tournament = get_tournament_or_404(tournament_id)
    courts = Court.query.filter_by(tournament_id=tournament_id).order_by(Court.court_number).all()
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.scheduled_time, Match.match_number).all()
    return render_template('scoring/setup.html', tournament=tournament, courts=courts, matches=matches)

@scoring.route('/setup/<int:tournament_id>/create-courts', methods=['POST'])
def create_courts(tournament_id):
    get_tournament_or_404(tournament_id)
    num_courts = int(request.form.get('num_courts', 9))
    if request.form.get('replace_existing'):
        Court.query.filter_by(tournament_id=tournament_id).delete()
    for i in range(1, num_courts + 1):
        db.session.add(Court(tournament_id=tournament_id, court_number=i, manager_token=Court.generate_token()))
    try:
        db.session.commit()
        flash(f'{num_courts} Courts erstellt!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))

@scoring.route('/setup/<int:tournament_id>/assign-manager', methods=['POST'])
def assign_manager(tournament_id):
    get_tournament_or_404(tournament_id)
    manager_name = request.form.get('manager_name', '').strip()
    court_ids = request.form.getlist('court_ids')
    if not manager_name or not court_ids:
        flash('Name und mindestens einen Court auswaehlen!', 'warning')
        return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))
    count = 0
    for cid in court_ids:
        court = Court.query.get(int(cid))
        if court and court.tournament_id == tournament_id:
            court.manager_name = manager_name
            count += 1
    try:
        db.session.commit()
        flash(f'{manager_name} -> {count} Courts zugewiesen!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))

@scoring.route('/setup/<int:tournament_id>/smart-import', methods=['POST'])
def smart_import(tournament_id):
    get_tournament_or_404(tournament_id)
    raw_text = request.form.get('schedule_text', '')
    base_date = request.form.get('base_date', '')
    if not raw_text.strip():
        flash('Kein Spielplan eingefuegt!', 'warning')
        return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))
    parsed = parse_schedule(raw_text, base_date)
    count = 0
    for m in parsed:
        match = Match(tournament_id=tournament_id, match_number=m['num'], category=m['cat'], round_name=m['rnd'], team1_name=m['team1'], team2_name=m['team2'], court_number=m['court'], scheduled_time=m['time'], status='scheduled')
        if m['court']:
            court = Court.query.filter_by(tournament_id=tournament_id, court_number=m['court']).first()
            if court: match.court_id = court.id
        db.session.add(match)
        count += 1
    try:
        db.session.commit()
        flash(f'{count} Matches importiert!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))

@scoring.route('/setup/<int:tournament_id>/clear-matches', methods=['POST'])
def clear_matches(tournament_id):
    get_tournament_or_404(tournament_id)
    count = Match.query.filter_by(tournament_id=tournament_id).delete()
    try:
        db.session.commit()
        flash(f'{count} Matches geloescht!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))

@scoring.route('/match/<int:match_id>/delete', methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    tid = match.tournament_id
    try:
        db.session.delete(match)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for('scoring.setup_tournament', tournament_id=tid))

@scoring.route('/match/<int:match_id>/assign-court', methods=['POST'])
def assign_court(match_id):
    match = Match.query.get_or_404(match_id)
    court_id = request.form.get('court_id')
    if court_id:
        c = Court.query.get(int(court_id))
        match.court_id = c.id
        match.court_number = c.court_number
    else:
        match.court_id = None
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for('scoring.setup_tournament', tournament_id=match.tournament_id))

@scoring.route('/setup/<int:tournament_id>/add-match', methods=['POST'])
def add_match(tournament_id):
    get_tournament_or_404(tournament_id)
    last = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.id.desc()).first()
    next_num = str(int(last.match_number) + 1) if last and last.match_number and last.match_number.isdigit() else '1'
    match = Match(tournament_id=tournament_id, match_number=request.form.get('match_number', next_num), round_name=request.form.get('round_name',''), category=request.form.get('category',''), team1_name=request.form['team1_name'], team2_name=request.form['team2_name'], court_id=int(request.form['court_id']) if request.form.get('court_id') else None, scheduled_time=datetime.strptime(request.form['scheduled_time'], '%Y-%m-%dT%H:%M') if request.form.get('scheduled_time') else None, status='scheduled')
    if match.court_id:
        c = Court.query.get(match.court_id)
        if c: match.court_number = c.court_number
    try:
        db.session.add(match)
        db.session.commit()
        flash(f'Match #{match.match_number} erstellt!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    return redirect(url_for('scoring.setup_tournament', tournament_id=tournament_id))



@scoring.route('/live/<int:tournament_id>')
def live_dashboard(tournament_id):
    tournament = get_tournament_or_404(tournament_id)
    courts = Court.query.filter_by(tournament_id=tournament_id).order_by(Court.court_number).all()
    return render_template('scoring/live_dashboard.html', tournament=tournament, courts=courts)

@scoring.route('/api/live/<int:tournament_id>')
def api_live_data(tournament_id):
    courts = Court.query.filter_by(tournament_id=tournament_id).order_by(Court.court_number).all()
    courts_data = []
    for court in courts:
        cur = Match.query.filter_by(court_id=court.id, status='in_play').first()
        lat = Match.query.filter_by(court_id=court.id, status='completed').order_by(Match.completed_at.desc()).first()
        nxt = Match.query.filter_by(court_id=court.id, status='scheduled').order_by(Match.match_number).first()
        ci = {'id': court.id, 'number': court.court_number, 'name': court.court_name or f'Court {court.court_number}', 'manager': court.manager_name or '-', 'status': court.status, 'current_match': None, 'latest_result': None, 'next_match': None}
        if cur:
            ci['current_match'] = {'id': cur.id, 'number': cur.match_number, 'team1': cur.get_team1_display(), 'team2': cur.get_team2_display(), 'category': cur.category, 'started_at': cur.started_at.strftime('%H:%M') if cur.started_at else None}
        if lat:
            ci['latest_result'] = {'id': lat.id, 'number': lat.match_number, 'team1': lat.get_team1_display(), 'team2': lat.get_team2_display(), 'score1': lat.team1_score, 'score2': lat.team2_score, 'category': lat.category, 'completed_at': lat.completed_at.strftime('%H:%M') if lat.completed_at else None, 'verified': lat.scoresheet_verified}
        if nxt:
            ci['next_match'] = {'id': nxt.id, 'number': nxt.match_number, 'team1': nxt.get_team1_display(), 'team2': nxt.get_team2_display(), 'category': nxt.category}
        courts_data.append(ci)
    recent = Match.query.filter_by(tournament_id=tournament_id, status='completed').order_by(Match.completed_at.desc()).limit(20).all()
    recent_scores = [{'id': m.id, 'number': m.match_number, 'team1': m.get_team1_display(), 'team2': m.get_team2_display(), 'score1': m.team1_score, 'score2': m.team2_score, 'category': m.category, 'court': m.court.court_number if m.court else m.court_number, 'completed_at': m.completed_at.strftime('%H:%M') if m.completed_at else None, 'verified': m.scoresheet_verified} for m in recent]
    total = Match.query.filter_by(tournament_id=tournament_id).count()
    completed = Match.query.filter_by(tournament_id=tournament_id, status='completed').count()
    in_play = Match.query.filter_by(tournament_id=tournament_id, status='in_play').count()
    unverified = Match.query.filter_by(tournament_id=tournament_id, status='completed', scoresheet_verified=False).count()
    return jsonify({'courts': courts_data, 'recent_scores': recent_scores, 'stats': {'total': total, 'completed': completed, 'in_play': in_play, 'scheduled': total - completed - in_play, 'unverified': unverified}, 'timestamp': datetime.utcnow().strftime('%H:%M:%S')})

@scoring.route('/match/<int:match_id>/verify', methods=['POST'])
def verify_match(match_id):
    match = Match.query.get_or_404(match_id)
    match.scoresheet_verified = True
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@scoring.route('/court/<token>')
def court_manager(token):
    court = Court.query.filter_by(manager_token=token).first_or_404()
    tournament = get_tournament_or_404(court.tournament_id)
    current_match = Match.query.filter_by(court_id=court.id, status='in_play').first()
    scheduled = Match.query.filter_by(court_id=court.id, status='scheduled').order_by(Match.match_number).all()
    completed = Match.query.filter_by(court_id=court.id, status='completed').order_by(Match.completed_at.desc()).limit(5).all()
    unassigned = Match.query.filter_by(tournament_id=court.tournament_id, court_id=None, status='scheduled').order_by(Match.match_number).all()
    return render_template('scoring/court_manager.html', court=court, tournament=tournament, current_match=current_match, scheduled_matches=scheduled, completed_matches=completed, unassigned_matches=unassigned, token=token)

@scoring.route('/court/<token>/start-match/<int:match_id>', methods=['POST'])
def start_match(token, match_id):
    court = Court.query.filter_by(manager_token=token).first_or_404()
    match = Match.query.get_or_404(match_id)
    if not match.court_id:
        match.court_id = court.id
        match.court_number = court.court_number
    match.status = 'in_play'
    match.started_at = datetime.utcnow()
    court.status = 'in_play'
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for('scoring.court_manager', token=token))

@scoring.route('/court/<token>/submit-score/<int:match_id>', methods=['POST'])
def submit_score(token, match_id):
    court = Court.query.filter_by(manager_token=token).first_or_404()
    match = Match.query.get_or_404(match_id)
    score1 = request.form.get('score_team1')
    score2 = request.form.get('score_team2')
    if score1 is not None and score2 is not None:
        match.team1_score = int(score1)
        match.team2_score = int(score2)
        match.status = 'completed'
        match.completed_at = datetime.utcnow()
        match.score_submitted_at = datetime.utcnow()
        match.submitted_by_court_id = court.id
        match.notes = request.form.get('notes', '')
        court.status = 'available'
        try:
            db.session.commit()
            flash(f'Score: {match.get_team1_display()} {score1}-{score2} {match.get_team2_display()}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    else:
        flash('Bitte beide Scores eingeben!', 'warning')
    return redirect(url_for('scoring.court_manager', token=token))

@scoring.route('/court/<token>/claim-match/<int:match_id>', methods=['POST'])
def claim_match(token, match_id):
    court = Court.query.filter_by(manager_token=token).first_or_404()
    match = Match.query.get_or_404(match_id)
    match.court_id = court.id
    match.court_number = court.court_number
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for('scoring.court_manager', token=token))

@scoring.route('/links/<int:tournament_id>')
def court_links(tournament_id):
    tournament = get_tournament_or_404(tournament_id)
    courts = Court.query.filter_by(tournament_id=tournament_id).order_by(Court.court_number).all()
    return render_template('scoring/court_links.html', tournament=tournament, courts=courts)
