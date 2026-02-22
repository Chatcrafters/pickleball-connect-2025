"""
WPC Player Import Script
Imports players from Pickleball Global CSV export
"""
import csv
import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, WPCPlayer, WPCRegistration

wpc_import = Blueprint('wpc_import', __name__)


def parse_name(full_name):
    """Split full name into first and last name"""
    parts = full_name.strip().split(' ', 1)
    first_name = parts[0] if parts else ''
    last_name = parts[1] if len(parts) > 1 else ''
    return first_name, last_name


def parse_date(date_str):
    """Parse date from CSV format (e.g., 'Jan-01-2002')"""
    if not date_str or date_str == '-':
        return None
    try:
        return datetime.strptime(date_str, '%b-%d-%Y').date()
    except:
        return None


def parse_age_category(division_name):
    """Extract age category from division name"""
    if '19+' in division_name:
        return '19+'
    elif '35+' in division_name:
        return '35+'
    elif '50+' in division_name:
        return '50+'
    return None


def parse_skill_level(rating):
    """Parse skill level from rating string"""
    if not rating:
        return None
    # e.g., "Elite (5.0)" -> "Elite"
    return rating.split('(')[0].strip() if '(' in rating else rating


def clean_phone(phone):
    """Clean phone number"""
    if not phone or phone.strip() == '-':
        return None
    return phone.strip()


def import_from_csv(csv_path):
    """Import players from Pickleball Global CSV"""
    players_data = {}
    registrations_data = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            pgid = row.get('PGID', '').strip()
            if not pgid:
                continue
            
            # Parse player data (only once per PGID)
            if pgid not in players_data:
                first_name, last_name = parse_name(row.get('PLAYER NAME', ''))
                
                players_data[pgid] = {
                    'pgid': pgid,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': row.get('EMAIL ID', '').strip() or None,
                    'phone': clean_phone(row.get('PHONE', '')),
                    'country': row.get('COUNTRY', '').strip() or None,
                    'dupr_id': row.get('DUPR', '').strip() or None,
                    'dupr_rating': row.get('RATING', '').strip() or None,
                    'gender': row.get('GENDER', '').strip() or None,
                    'date_of_birth': parse_date(row.get('DOB', '')),
                    'address': row.get('ADDRESS', '').strip() or None,
                }
            
            # Parse registration data
            division_name = row.get('DIVISION NAME', '')
            registrations_data.append({
                'pgid': pgid,
                'division_type': row.get('DIVISION TYPE', '').strip(),
                'division_name': division_name,
                'age_category': parse_age_category(division_name),
                'skill_level': parse_skill_level(row.get('RATING', '')),
                'partner_name': row.get('PARTNER', '').strip() or None,
            })
    
    return players_data, registrations_data


def import_to_database(players_data, registrations_data):
    """Import parsed data into database"""
    stats = {
        'players_created': 0,
        'players_updated': 0,
        'registrations_created': 0,
        'errors': []
    }
    
    player_id_map = {}  # pgid -> player.id
    
    # Import players
    for pgid, data in players_data.items():
        try:
            player = WPCPlayer.query.filter_by(pgid=pgid).first()
            
            if player:
                # Update existing player
                for key, value in data.items():
                    if key != 'pgid' and value is not None:
                        setattr(player, key, value)
                stats['players_updated'] += 1
            else:
                # Create new player
                player = WPCPlayer(**data)
                player.generate_checkin_token()
                db.session.add(player)
                stats['players_created'] += 1
            
            db.session.flush()  # Get player.id
            player_id_map[pgid] = player.id
            
        except Exception as e:
            stats['errors'].append(f"Player {pgid}: {str(e)}")
    
    # Import registrations
    for reg_data in registrations_data:
        try:
            pgid = reg_data.pop('pgid')
            player_id = player_id_map.get(pgid)
            
            if not player_id:
                continue
            
            # Check if registration already exists
            existing = WPCRegistration.query.filter_by(
                player_id=player_id,
                division_type=reg_data['division_type'],
                division_name=reg_data['division_name']
            ).first()
            
            if not existing:
                reg = WPCRegistration(player_id=player_id, **reg_data)
                db.session.add(reg)
                stats['registrations_created'] += 1
                
        except Exception as e:
            stats['errors'].append(f"Registration: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Commit error: {str(e)}")
    
    return stats


# ============================================================================
# ADMIN ROUTES FOR IMPORT
# ============================================================================

@wpc_import.route('/admin/wpc/import', methods=['GET', 'POST'])
def import_page():
    """WPC Import page"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'danger')
            return redirect(request.url)
        
        try:
            # Save temporarily
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
                content = file.read().decode('utf-8-sig')
                tmp.write(content)
                tmp_path = tmp.name
            
            # Parse and import
            players_data, registrations_data = import_from_csv(tmp_path)
            stats = import_to_database(players_data, registrations_data)
            
            # Cleanup
            os.unlink(tmp_path)
            
            flash(f"Import complete! Players: {stats['players_created']} new, {stats['players_updated']} updated. Registrations: {stats['registrations_created']}", 'success')
            
            if stats['errors']:
                flash(f"Errors: {len(stats['errors'])}", 'warning')
            
        except Exception as e:
            flash(f'Import error: {str(e)}', 'danger')
        
        return redirect(url_for('wpc_import.import_page'))
    
    # GET - show import page
    total_players = WPCPlayer.query.count()
    total_registrations = WPCRegistration.query.count()
    with_phone = WPCPlayer.query.filter(WPCPlayer.phone.isnot(None), WPCPlayer.phone != '-', WPCPlayer.phone != '').count()
    checked_in = WPCPlayer.query.filter_by(checked_in=True).count()
    
    return render_template('wpc/import.html',
                         total_players=total_players,
                         total_registrations=total_registrations,
                         with_phone=with_phone,
                         checked_in=checked_in)
