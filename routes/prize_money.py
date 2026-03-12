import requests
"""
Prize Money Blueprint v2 â€” WPC + PCL separated
WPC PCL MÃ¡laga 2026
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json, hashlib, os, csv, io

prize_money = Blueprint('prize_money', __name__, template_folder='../templates')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'players_data.json')
SUBMISSIONS_FILE = os.path.join(BASE_DIR, 'submissions.json')
PM_USERS_FILE = os.path.join(BASE_DIR, 'pm_users.json')
BUCKET = 'prize-money-docs'

# â”€â”€â”€ Supabase REST â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_supabase_headers():
    key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY', '')
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }

def supabase_url():
    return os.environ.get('SUPABASE_URL', '').rstrip('/')

def get_supabase():
    """Returns a simple dict-based client for REST calls"""
    return {'url': supabase_url(), 'headers': get_supabase_headers()}

def ensure_bucket():
    pass  # Bucket already exists

def upload_doc(player_id, file_bytes, filename, content_type, page=1):
    try:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
        path = f"{player_id}/id_document_p{page}.{ext}"
        base = supabase_url()
        headers = get_supabase_headers()
        headers['Content-Type'] = content_type
        headers['x-upsert'] = 'true'
        url = f"{base}/storage/v1/object/{BUCKET}/{path}"
        resp = requests.post(url, data=file_bytes, headers=headers)
        if resp.status_code in (200, 201):
            return path
        # Try PUT for upsert
        resp = requests.put(url, data=file_bytes, headers=headers)
        if resp.status_code in (200, 201):
            return path
        print(f'Upload error: {resp.status_code} {resp.text}')
        return None
    except Exception as e:
        print(f'Upload error: {e}')
        return None

def get_doc_url(path):
    try:
        base = supabase_url()
        headers = get_supabase_headers()
        url = f"{base}/storage/v1/object/sign/{BUCKET}/{path}"
        resp = requests.post(url, json={'expiresIn': 3600}, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            signed = data.get('signedURL') or data.get('signedUrl') or data.get('signed_url')
            if signed:
                if signed.startswith('/'):
                    return f"{base}/storage/v1{signed}"
                return signed
        print(f'Doc URL error: {resp.status_code} {resp.text}')
        return None
    except Exception as e:
        print(f'Doc URL error: {e}')
        return None

# â”€â”€â”€ Countries â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
EU_COUNTRIES = ["Austria","Belgium","Bulgaria","Croatia","Cyprus","Czech Republic",
    "Denmark","Estonia","Finland","France","Germany","Greece","Hungary","Ireland",
    "Italy","Latvia","Lithuania","Luxembourg","Malta","Netherlands","Poland",
    "Portugal","Romania","Slovakia","Slovenia","Spain","Sweden"]
EEA_COUNTRIES = ["Iceland","Liechtenstein","Norway"]
ALL_COUNTRIES = sorted([
    "Afghanistan","Albania","Algeria","Andorra","Angola","Argentina","Armenia",
    "Australia","Austria","Azerbaijan","Bahrain","Bangladesh","Belarus","Belgium",
    "Bolivia","Bosnia and Herzegovina","Brazil","Bulgaria","Canada","Chile","China",
    "Colombia","Costa Rica","Croatia","Cuba","Cyprus","Czech Republic","Denmark",
    "Ecuador","Egypt","Estonia","Ethiopia","Finland","France","Georgia","Germany",
    "Ghana","Greece","Guatemala","Honduras","Hungary","Iceland","India","Indonesia",
    "Iran","Iraq","Ireland","Israel","Italy","Japan","Jordan","Kazakhstan","Kenya",
    "Kuwait","Latvia","Lebanon","Liechtenstein","Lithuania","Luxembourg","Malaysia",
    "Malta","Mexico","Moldova","Morocco","Netherlands","New Zealand","Nigeria","Norway",
    "Pakistan","Palestine","Panama","Paraguay","Peru","Philippines","Poland","Portugal",
    "Qatar","Romania","Russia","Saudi Arabia","Serbia","Singapore","Slovakia","Slovenia",
    "South Africa","South Korea","Spain","Sweden","Switzerland","Taiwan","Thailand",
    "Tunisia","Turkey","Ukraine","United Arab Emirates","United Kingdom","United States",
    "Uruguay","Venezuela","Vietnam","Zimbabwe"
])

def get_tax_info(country):
    if country == "Spain":
        return {"rate": 19, "type": "IRPF (Spain)"}
    elif country in EU_COUNTRIES or country in EEA_COUNTRIES:
        return {"rate": 19, "type": "IRNR (EU/EEA)"}
    else:
        return {"rate": 24, "type": "IRNR (Non-EU)"}

# â”€â”€â”€ Auth helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_pm_role():
    if session.get('admin_id') or session.get('user_id'):
        return 'both'
    return session.get('pm_role')

def load_pm_users():
    # Hardcoded users - no filesystem needed (works on Vercel)
    return {
        'wpc_admin': {'password': 'wpc2026malaga', 'role': 'wpc'},
        'pcl_admin': {'password': 'pcl2026malaga', 'role': 'pcl'},
        'gestor': {'password': 'gestor2026', 'role': 'gestor'},
    }

def load_players():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_token(player_id):
    secret = os.environ.get('SECRET_KEY', 'PickleballConnect2024Madrid')
    return hashlib.sha256(f"{player_id}-{secret}".encode()).hexdigest()[:24]

def get_combined_player(token):
    players = load_players()
    target = next((p for p in players if generate_token(p['id']) == token), None)
    if not target:
        return None
    name = target['name'].strip().lower()
    wpc_prizes = [p for p in players if p['name'].strip().lower() == name and p['type'] == 'WPC']
    pcl_prizes = [p for p in players if p['name'].strip().lower() == name and p['type'] == 'PCL']
    return {
        'id': target['id'],
        'name': target['name'],
        'email': target['email'],
        'token': token,
        'wpc_prizes': wpc_prizes,
        'pcl_prizes': pcl_prizes,
        'wpc_total': sum(p['total'] for p in wpc_prizes),
        'pcl_total': sum(p['total'] for p in pcl_prizes),
        'has_wpc': len(wpc_prizes) > 0,
        'has_pcl': len(pcl_prizes) > 0,
    }

def load_submissions():
    try:
        base = supabase_url()
        if not base:
            raise Exception('SUPABASE_URL not set')
        headers = get_supabase_headers()
        resp = requests.get(f"{base}/rest/v1/prize_money_submissions?select=*", headers=headers)
        if resp.status_code == 200:
            return {row['player_id']: row['data'] for row in resp.json()}
        print(f'Warning: load_submissions HTTP {resp.status_code}')
        return {}
    except Exception as e:
        print(f'Warning: could not load submissions from Supabase: {e}')
        return {}

def save_submission(player_id, data):
    record = {**data, 'submitted_at': datetime.now().isoformat()}
    try:
        base = supabase_url()
        if not base:
            raise Exception('SUPABASE_URL not set')
        headers = get_supabase_headers()
        headers['Prefer'] = 'resolution=merge-duplicates'
        payload = {
            'player_id': player_id,
            'data': record,
            'submitted_at': record['submitted_at'],
        }
        resp = requests.post(f"{base}/rest/v1/prize_money_submissions", json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            print(f'Warning: save_submission HTTP {resp.status_code} {resp.text}')
    except Exception as e:
        print(f'Warning: could not save to Supabase: {e}')

# â”€â”€â”€ PM Login â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/login', methods=['GET', 'POST'])
def pm_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        users = load_pm_users()
        if username in users and users[username]['password'] == password:
            session['pm_role'] = users[username]['role']
            session['pm_username'] = username
            role = users[username]['role']
            if role == 'gestor':
                return redirect('/prize-money/gestor')
            next_url = request.args.get('next', f'/prize-money/admin/{role}')
            return redirect(next_url)
        error = 'Invalid username or password'
    return render_template('prize_money/pm_login.html', error=error)

@prize_money.route('/prize-money/logout')
def pm_logout():
    session.pop('pm_role', None)
    session.pop('pm_username', None)
    return redirect('/prize-money/login')

# â”€â”€â”€ Player Form â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/form/<token>')
def player_form(token):
    player = get_combined_player(token)
    if not player:
        return render_template('prize_money/invalid_token.html'), 404
    submissions = load_submissions()
    already_submitted = player['id'] in submissions
    template = 'prize_money/form_wpc.html' if player.get('has_wpc') else 'prize_money/form_pcl.html'
    return render_template(template,
        player=player, token=token,
        already_submitted=already_submitted,
        submission=submissions.get(player['id']),
        countries=ALL_COUNTRIES,
    )

# â”€â”€â”€ Document Upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/upload/<token>', methods=['POST'])
def upload_document(token):
    player = get_combined_player(token)
    if not player:
        return jsonify({'error': 'Invalid token'}), 404
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400
    allowed = {'pdf','jpg','jpeg','png','heic'}
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in allowed:
        return jsonify({'error': 'File type not allowed. Use PDF, JPG or PNG.'}), 400
    file_bytes = f.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        return jsonify({'error': 'File too large (max 10MB)'}), 400
    ensure_bucket()
    page_num = request.form.get('page', '1')
    path = upload_doc(player['id'], file_bytes, f.filename, f.content_type, page_num)
    if not path:
        return jsonify({'error': 'Upload failed. Please try again.'}), 500
    # Save doc_path immediately to Supabase (upsert partial record)
    try:
        key = 'doc_path' if page_num == '1' else 'doc_path_p2'
        base = supabase_url()
        headers = get_supabase_headers()
        headers['Prefer'] = 'resolution=merge-duplicates'
        # Load existing data first to merge
        resp = requests.get(
            f"{base}/rest/v1/prize_money_submissions?player_id=eq.{player['id']}&select=data",
            headers=headers
        )
        existing_data = {}
        if resp.status_code == 200 and resp.json():
            existing_data = resp.json()[0].get('data', {})
        existing_data[key] = path
        existing_data['doc_uploaded_at'] = datetime.now().isoformat()
        payload = {
            'player_id': player['id'],
            'data': existing_data,
            'submitted_at': existing_data.get('submitted_at', datetime.now().isoformat()),
        }
        requests.post(
            f"{base}/rest/v1/prize_money_submissions",
            json=payload, headers=headers
        )
    except Exception as e:
        print(f'Warning: could not save doc_path to Supabase: {e}')
    return jsonify({'success': True, 'path': path})

# â”€â”€â”€ Submit Form â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/submit/<token>', methods=['POST'])
def submit_form(token):
    player = get_combined_player(token)
    if not player:
        return jsonify({'error': 'Invalid token'}), 404
    data = request.get_json()
    for field in ['recipient_type', 'country', 'iban', 'full_name', 'doc_type']:
        if not data.get(field):
            return jsonify({'error': f'Missing: {field}'}), 400
    if data.get('recipient_type') == 'autonomo' and not data.get('cif'):
        return jsonify({'error': 'CIF required'}), 400

    tax = get_tax_info(data['country'])
    wpc_tax = round(player['wpc_total'] * tax['rate'] / 100, 2)
    wpc_net = round(player['wpc_total'] - wpc_tax, 2)

    # Get existing doc_path if uploaded
    submissions = load_submissions()
    existing = submissions.get(player['id'], {})
    doc_path = existing.get('doc_path', '')
    doc_path_p2 = existing.get('doc_path_p2', '')

    save_submission(player['id'], {
        'player_name': player['name'],
        'form_type': data.get('form_type', 'WPC'),
        'wpc_total_gross': player['wpc_total'],
        'wpc_prizes': ' | '.join(p['prizes'] for p in player['wpc_prizes']),
        'wpc_tax_rate': tax['rate'],
        'wpc_tax_type': tax['type'],
        'wpc_tax_amount': wpc_tax,
        'wpc_net_amount': wpc_net,
        'pcl_total_gross': player['pcl_total'],
        'pcl_prizes': ' | '.join(p['prizes'] for p in player['pcl_prizes']),
        'pcl_net_amount': player['pcl_total'],
        'full_name': data['full_name'],
        'recipient_type': data['recipient_type'],
        'country': data['country'],
        'iban': data['iban'].replace(' ', '').upper(),
        'doc_type': data['doc_type'],
        'doc_number': data.get('doc_number', ''),
        'cif': data.get('cif', ''),
        'company_name': data.get('company_name', ''),
        'doc_path': doc_path,
        'doc_path_p2': doc_path_p2,
        'status': 'SUBMITTED',
    })
    return jsonify({'success': True})

# â”€â”€â”€ Admin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def require_role(required_role):
    role = get_pm_role()
    if not role:
        return False
    return role == 'both' or role == required_role

def build_admin_data(prize_type):
    players = load_players()
    submissions = load_submissions()
    filtered = [p for p in players if p['type'] == prize_type]
    seen, enriched = set(), []
    for p in filtered:
        key = p['name'].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        sub = submissions.get(p['id'])
        enriched.append({**p,
            'token': generate_token(p['id']),
            'submitted': sub is not None and sub.get('status') == 'SUBMITTED',
            'submission': sub,
            'url': f"/prize-money/form/{generate_token(p['id'])}"
        })
    total = sum(p['total'] for p in filtered if p['name'].strip().lower() in {e['name'].strip().lower() for e in enriched})
    done = sum(1 for e in enriched if e['submitted'])
    return enriched, done, len(enriched), total

@prize_money.route('/prize-money/admin/wpc')
def admin_wpc():
    if not require_role('wpc'):
        return redirect(f'/prize-money/login?next=/prize-money/admin/wpc')
    players, done, total, pool = build_admin_data('WPC')
    return render_template('prize_money/admin_wpc.html',
        players=players, done=done, total=total, pool=pool,
        username=session.get('pm_username') or 'admin')

@prize_money.route('/prize-money/admin/pcl')
def admin_pcl():
    if not require_role('pcl'):
        return redirect(f'/prize-money/login?next=/prize-money/admin/pcl')
    players, done, total, pool = build_admin_data('PCL')
    return render_template('prize_money/admin_pcl.html',
        players=players, done=done, total=total, pool=pool,
        username=session.get('pm_username') or 'admin')

# â”€â”€â”€ Gestor (tax advisor) view â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/gestor')
def gestor_view():
    role = get_pm_role()
    if role not in ('gestor', 'both'):
        return redirect('/prize-money/login?next=/prize-money/gestor')
    submissions = load_submissions()
    players = load_players()
    records = []
    for pid, sub in submissions.items():
        if sub.get('status') != 'SUBMITTED':
            continue
        # Get signed URL for document
        doc_url = None
        if sub.get('doc_path'):
            doc_url = get_doc_url(sub['doc_path'])
        doc_url_p2 = None
        if sub.get('doc_path_p2'):
            doc_url_p2 = get_doc_url(sub['doc_path_p2'])
        records.append({**sub, 'player_id': pid, 'doc_url': doc_url, 'doc_url_p2': doc_url_p2})
    records.sort(key=lambda r: r.get('submitted_at', ''), reverse=True)
    return render_template('prize_money/gestor.html', records=records)

@prize_money.route('/prize-money/gestor/doc/<player_id>')
def gestor_doc(player_id):
    role = get_pm_role()
    if role not in ('gestor', 'both'):
        return redirect('/prize-money/login')
    submissions = load_submissions()
    sub = submissions.get(player_id)
    if not sub or not sub.get('doc_path'):
        return 'Document not found', 404
    url = get_doc_url(sub['doc_path'])
    if not url:
        return 'Could not generate download link', 500
    return redirect(url)

# â”€â”€â”€ Export CSV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/admin/export/<prize_type>')
def export_csv(prize_type):
    role = get_pm_role()
    if not role:
        return redirect('/prize-money/login')
    submissions = load_submissions()
    players = load_players()
    output = io.StringIO()
    if prize_type == 'WPC':
        fields = ['Name','Prizes','Gross â‚¬','Tax Type','Tax %','Tax â‚¬','Net â‚¬',
                  'Full Name','Recipient','Country','Doc Type','Doc No','CIF','IBAN','Submitted','Status']
        w = csv.DictWriter(output, fieldnames=fields)
        w.writeheader()
        seen = set()
        for p in players:
            if p['type'] != 'WPC':
                continue
            key = p['name'].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            sub = submissions.get(p['id'], {})
            tax = get_tax_info(sub.get('country', '')) if sub.get('country') else {'rate': '', 'type': ''}
            gross = p['total']
            tax_amt = round(gross * tax['rate'] / 100, 2) if tax['rate'] else ''
            net = round(gross - tax_amt, 2) if tax_amt != '' else ''
            w.writerow({'Name': p['name'], 'Prizes': p['prizes'], 'Gross â‚¬': gross,
                'Tax Type': sub.get('wpc_tax_type',''), 'Tax %': sub.get('wpc_tax_rate',''),
                'Tax â‚¬': sub.get('wpc_tax_amount',''), 'Net â‚¬': sub.get('wpc_net_amount',''),
                'Full Name': sub.get('full_name',''), 'Recipient': sub.get('recipient_type',''),
                'Country': sub.get('country',''), 'Doc Type': sub.get('doc_type',''),
                'Doc No': sub.get('doc_number',''), 'CIF': sub.get('cif',''),
                'IBAN': sub.get('iban',''),
                'Submitted': sub.get('submitted_at','')[:10] if sub.get('submitted_at') else '',
                'Status': sub.get('status','PENDING')})
    else:
        fields = ['Name','Prizes','Gross â‚¬','Full Name','Recipient','Country',
                  'Doc Type','Doc No','CIF','IBAN','Submitted','Status']
        w = csv.DictWriter(output, fieldnames=fields)
        w.writeheader()
        seen = set()
        for p in players:
            if p['type'] != 'PCL':
                continue
            key = p['name'].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            sub = submissions.get(p['id'], {})
            w.writerow({'Name': p['name'], 'Prizes': p['prizes'], 'Gross â‚¬': p['total'],
                'Full Name': sub.get('full_name',''), 'Recipient': sub.get('recipient_type',''),
                'Country': sub.get('country',''), 'Doc Type': sub.get('doc_type',''),
                'Doc No': sub.get('doc_number',''), 'CIF': sub.get('cif',''),
                'IBAN': sub.get('iban',''),
                'Submitted': sub.get('submitted_at','')[:10] if sub.get('submitted_at') else '',
                'Status': sub.get('status','PENDING')})

    output.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'prize_money_{prize_type}_{ts}.csv')

# â”€â”€â”€ Copy links API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@prize_money.route('/prize-money/api/links')
def api_links():
    role = get_pm_role()
    if not role:
        return jsonify({'error': 'Unauthorized'}), 401
    players = load_players()
    base_url = request.host_url.rstrip('/')
    submissions = load_submissions()
    out = []
    seen = set()
    for p in players:
        key = p['name'].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        sub = submissions.get(p['id'])
        if sub and sub.get('status') == 'SUBMITTED':
            continue
        out.append({'name': p['name'], 'type': p['type'],
                    'total': p['total'], 'url': f"{base_url}/prize-money/form/{generate_token(p['id'])}"})
    return jsonify(out)
