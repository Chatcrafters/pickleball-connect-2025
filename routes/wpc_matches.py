"""
WPC Match Import and Display
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
from models import db, WPCPlayer
import re

wpc_matches = Blueprint('wpc_matches', __name__, url_prefix='/wpc')


# ============================================================================
# WPC MATCH MODEL (add to models.py)
# ============================================================================
"""
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
"""

# Import WPCMatch from models after adding it
from models import WPCMatch


def parse_schedule_text(text, match_date):
    """Parse schedule text and return list of match dicts"""
    matches = []
    lines = text.strip().split('\n')
    
    current_division = None
    current_flight = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and headers
        if not line or line.startswith('Search:') or line.startswith('Division') or line == 'Scores':
            i += 1
            continue
        
        # Check for division line (e.g., "MD50+ 5.0", "MS19+ 5.0", "WD35+ 4.5")
        if re.match(r'^[MW][SD]\d+\+\s+\d+\.\d+$', line):
            current_division = line
            i += 1
            continue
        
        # Check for flight line
        if line.startswith('Flight -'):
            current_flight = line
            i += 1
            continue
        
        # Check for match line (starts with "Match" or contains match info)
        # Format: "Match 1	Court 1	08:00	Team1	Team2	--"
        if 'Court' in line and ('\t' in line or '  ' in line):
            # Parse match line
            parts = re.split(r'\t+', line)
            if len(parts) >= 6:
                match_info = parts[0]  # "Match 1" or "Semi Final 1*1"
                court = parts[1]  # "Court 1"
                time_str = parts[2]  # "08:00"
                team1 = parts[3]  # "Name1&Name2" or "Name1"
                team2 = parts[4]  # "Name1&Name2" or "Name1"
                score = parts[5] if len(parts) > 5 else "--"
                
                # Parse time
                try:
                    match_time = datetime.strptime(time_str, '%H:%M').time()
                except:
                    i += 1
                    continue
                
                # Parse teams
                is_doubles = '&' in team1 or '&' in team2
                
                if is_doubles:
                    team1_players = team1.split('&')
                    team2_players = team2.split('&')
                    player1 = team1_players[0].strip() if len(team1_players) > 0 else None
                    player2 = team1_players[1].strip() if len(team1_players) > 1 else None
                    opponent1 = team2_players[0].strip() if len(team2_players) > 0 else None
                    opponent2 = team2_players[1].strip() if len(team2_players) > 1 else None
                else:
                    player1 = team1.strip()
                    player2 = None
                    opponent1 = team2.strip()
                    opponent2 = None
                
                # Skip TBD matches
                if player1 == 'TBD' or opponent1 == 'TBD':
                    i += 1
                    continue
                
                # Skip BYE matches
                if 'BYE' in (player1 or '') or 'BYE' in (opponent1 or ''):
                    i += 1
                    continue
                
                match = {
                    'match_date': match_date,
                    'match_time': match_time,
                    'court': court.replace('Court ', ''),
                    'division': current_division,
                    'flight': current_flight,
                    'match_number': match_info,
                    'player1_name': player1,
                    'player2_name': player2,
                    'opponent1_name': opponent1,
                    'opponent2_name': opponent2,
                    'score': score if score != '--' else None,
                    'is_doubles': is_doubles
                }
                matches.append(match)
        
        i += 1
    
    return matches


def import_matches_to_db(matches):
    """Import parsed matches to database"""
    count = 0
    for m in matches:
        # Check if match already exists
        existing = WPCMatch.query.filter_by(
            match_date=m['match_date'],
            match_time=m['match_time'],
            court=m['court'],
            player1_name=m['player1_name']
        ).first()
        
        if not existing:
            match = WPCMatch(**m)
            db.session.add(match)
            count += 1
    
    db.session.commit()
    return count


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@wpc_matches.route('/admin/matches')
def admin_matches():
    """View all matches"""
    date_filter = request.args.get('date')
    
    query = WPCMatch.query
    
    if date_filter:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter_by(match_date=filter_date)
    
    matches = query.order_by(WPCMatch.match_date, WPCMatch.match_time).all()
    
    # Get unique dates
    dates = db.session.query(WPCMatch.match_date).distinct().order_by(WPCMatch.match_date).all()
    dates = [d[0] for d in dates]
    
    return render_template('wpc/admin_matches.html', matches=matches, dates=dates, current_date=date_filter)


@wpc_matches.route('/admin/matches/import', methods=['GET', 'POST'])
def import_matches():
    """Import matches from text"""
    if request.method == 'POST':
        schedule_text = request.form.get('schedule_text', '')
        date_str = request.form.get('match_date', '')
        
        if not schedule_text or not date_str:
            flash('Please provide schedule text and date', 'danger')
            return redirect(url_for('wpc_matches.import_matches'))
        
        try:
            match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            matches = parse_schedule_text(schedule_text, match_date)
            count = import_matches_to_db(matches)
            flash(f'Successfully imported {count} matches for {date_str}!', 'success')
        except Exception as e:
            flash(f'Import error: {str(e)}', 'danger')
        
        return redirect(url_for('wpc_matches.import_matches'))
    
    # GET - show form
    total_matches = WPCMatch.query.count()
    dates = db.session.query(WPCMatch.match_date, db.func.count(WPCMatch.id)).group_by(WPCMatch.match_date).all()
    
    return render_template('wpc/import_matches.html', total_matches=total_matches, dates=dates)


@wpc_matches.route('/admin/matches/clear', methods=['POST'])
def clear_matches():
    """Clear all matches for a date"""
    date_str = request.form.get('date')
    if date_str:
        match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        WPCMatch.query.filter_by(match_date=match_date).delete()
        db.session.commit()
        flash(f'Cleared matches for {date_str}', 'success')
    return redirect(url_for('wpc_matches.import_matches'))


# ============================================================================
# PLAYER SCHEDULE API
# ============================================================================

@wpc_matches.route('/api/player/<int:player_id>/schedule')
def player_schedule_api(player_id):
    """Get player's match schedule"""
    player = WPCPlayer.query.get_or_404(player_id)
    
    # Find matches where player is involved
    name = f"{player.first_name} {player.last_name}"
    
    matches = WPCMatch.query.filter(
        db.or_(
            WPCMatch.player1_name.ilike(f'%{player.first_name}%'),
            WPCMatch.player2_name.ilike(f'%{player.first_name}%'),
            WPCMatch.opponent1_name.ilike(f'%{player.first_name}%'),
            WPCMatch.opponent2_name.ilike(f'%{player.first_name}%')
        )
    ).order_by(WPCMatch.match_date, WPCMatch.match_time).all()
    
    # Filter to exact matches
    player_matches = []
    for m in matches:
        names = [m.player1_name, m.player2_name, m.opponent1_name, m.opponent2_name]
        for n in names:
            if n and player.first_name.lower() in n.lower() and player.last_name.lower() in n.lower():
                player_matches.append(m)
                break
    
    return jsonify({
        'player': player.get_full_name(),
        'matches': [{
            'date': m.match_date.strftime('%Y-%m-%d'),
            'time': m.match_time.strftime('%H:%M'),
            'court': m.court,
            'division': m.division,
            'is_doubles': m.is_doubles,
            'partner': get_partner(m, player),
            'opponents': get_opponents(m, player)
        } for m in player_matches]
    })


def get_partner(match, player):
    """Get player's partner in a match"""
    if not match.is_doubles:
        return None
    
    names = [match.player1_name, match.player2_name]
    for n in names:
        if n and player.first_name.lower() in n.lower():
            # Return the other name
            other = match.player2_name if n == match.player1_name else match.player1_name
            return other
    
    names = [match.opponent1_name, match.opponent2_name]
    for n in names:
        if n and player.first_name.lower() in n.lower():
            other = match.opponent2_name if n == match.opponent1_name else match.opponent1_name
            return other
    
    return None


def get_opponents(match, player):
    """Get opponents in a match"""
    names = [match.player1_name, match.player2_name]
    is_team1 = False
    for n in names:
        if n and player.first_name.lower() in n.lower():
            is_team1 = True
            break
    
    if is_team1:
        if match.is_doubles:
            return f"{match.opponent1_name} & {match.opponent2_name}"
        return match.opponent1_name
    else:
        if match.is_doubles:
            return f"{match.player1_name} & {match.player2_name}"
        return match.player1_name
