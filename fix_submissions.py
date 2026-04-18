"""
Fix existing submissions: set correct form_type and prize amounts
based on players_data.json
"""
import json, os, hashlib, requests
from datetime import datetime

BASE_DIR = r'H:\Meine Ablage\Projekte\pickleball_connect_2025'
DATA_FILE = os.path.join(BASE_DIR, 'players_data.json')

# Load .env manually
env_path = os.path.join(BASE_DIR, '.env')
env = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

SUPABASE_URL = env.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = env.get('SUPABASE_SERVICE_KEY') or env.get('SUPABASE_KEY', '')
SECRET_KEY = env.get('SECRET_KEY', 'PickleballConnect2024Madrid')

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
}

def generate_token(player_id):
    return hashlib.sha256(f"{player_id}-{SECRET_KEY}".encode()).hexdigest()[:24]

def get_tax_info(country):
    EU = ["Austria","Belgium","Bulgaria","Croatia","Cyprus","Czech Republic",
          "Denmark","Estonia","Finland","France","Germany","Greece","Hungary",
          "Ireland","Italy","Latvia","Lithuania","Luxembourg","Malta","Netherlands",
          "Poland","Portugal","Romania","Slovakia","Slovenia","Spain","Sweden"]
    EEA = ["Iceland","Liechtenstein","Norway"]
    if country == "Spain":
        return {"rate": 19, "type": "IRPF (Spain)"}
    elif country in EU or country in EEA:
        return {"rate": 19, "type": "IRNR (EU/EEA)"}
    else:
        return {"rate": 24, "type": "IRNR (Non-EU)"}

# Load players
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    players = json.load(f)

# Load all submissions
resp = requests.get(f"{SUPABASE_URL}/rest/v1/prize_money_submissions?select=*", headers=headers)
submissions = resp.json()
print(f"Found {len(submissions)} submissions")

fixed = 0
for row in submissions:
    pid = row['player_id']
    data = row.get('data') or {}
    
    # Find player by id
    target = next((p for p in players if p['id'] == pid), None)
    if not target:
        print(f"  SKIP {pid}: not found in players_data.json")
        continue
    
    name = target['name'].strip().lower()
    wpc_prizes = [p for p in players if p['name'].strip().lower() == name and p['type'] == 'WPC']
    pcl_prizes = [p for p in players if p['name'].strip().lower() == name and p['type'] == 'PCL']
    
    wpc_total = sum(p['total'] for p in wpc_prizes)
    pcl_total = sum(p['total'] for p in pcl_prizes)
    has_wpc = wpc_total > 0
    has_pcl = pcl_total > 0
    
    country = data.get('country', 'Spain')
    tax = get_tax_info(country)
    
    # Determine correct form_type
    if has_wpc and has_pcl:
        correct_type = 'BOTH'
    elif has_pcl:
        correct_type = 'PCL'
    else:
        correct_type = 'WPC'
    
    wpc_tax = round(wpc_total * tax['rate'] / 100, 2)
    wpc_net = round(wpc_total - wpc_tax, 2)
    
    old_type = data.get('form_type', 'WPC')
    
    # Update data
    data['form_type'] = correct_type
    data['wpc_total_gross'] = wpc_total
    data['wpc_prizes'] = ' | '.join(p['prizes'] for p in wpc_prizes)
    data['wpc_tax_rate'] = tax['rate']
    data['wpc_tax_type'] = tax['type']
    data['wpc_tax_amount'] = wpc_tax
    data['wpc_net_amount'] = wpc_net
    data['pcl_total_gross'] = pcl_total
    data['pcl_prizes'] = ' | '.join(p['prizes'] for p in pcl_prizes)
    data['pcl_net_amount'] = pcl_total
    
    # Save back to Supabase
    patch_headers = {**headers, 'Prefer': 'resolution=merge-duplicates'}
    payload = {'player_id': pid, 'data': data, 'submitted_at': row.get('submitted_at')}
    r = requests.post(f"{SUPABASE_URL}/rest/v1/prize_money_submissions", json=payload, headers=patch_headers)
    
    if r.status_code in (200, 201):
        print(f"  OK  {target['name']}: {old_type} -> {correct_type} | WPC={wpc_total} PCL={pcl_total}")
        fixed += 1
    else:
        print(f"  ERR {target['name']}: {r.status_code} {r.text}")

print(f"\nDone: {fixed}/{len(submissions)} submissions fixed")
