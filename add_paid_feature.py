content = open('routes/prize_money.py', encoding='utf-8').read()

# 1. Add mark_paid route before the export route
new_route = """
# ─── Mark as Paid ────────────────────────────────────────────────────────────
@prize_money.route('/prize-money/gestor/mark-paid/<player_id>', methods=['POST'])
def mark_paid(player_id):
    role = get_pm_role()
    if role not in ('gestor', 'both'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        base = supabase_url()
        headers = get_supabase_headers()
        # Get existing data
        resp = requests.get(
            f"{base}/rest/v1/prize_money_submissions?player_id=eq.{player_id}&select=data",
            headers=headers
        )
        if resp.status_code != 200 or not resp.json():
            return jsonify({'error': 'Not found'}), 404
        existing_data = resp.json()[0].get('data', {})
        paid_at = datetime.now().isoformat()
        existing_data['paid_at'] = paid_at
        # Update record
        upd_headers = {**headers, 'Prefer': 'resolution=merge-duplicates'}
        requests.post(
            f"{base}/rest/v1/prize_money_submissions",
            json={'player_id': player_id, 'data': existing_data, 'paid_at': paid_at,
                  'submitted_at': existing_data.get('submitted_at', paid_at)},
            headers=upd_headers
        )
        return jsonify({'success': True, 'paid_at': paid_at})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prize_money.route('/prize-money/gestor/mark-unpaid/<player_id>', methods=['POST'])
def mark_unpaid(player_id):
    role = get_pm_role()
    if role not in ('gestor', 'both'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        base = supabase_url()
        headers = get_supabase_headers()
        resp = requests.get(
            f"{base}/rest/v1/prize_money_submissions?player_id=eq.{player_id}&select=data,submitted_at",
            headers=headers
        )
        if resp.status_code != 200 or not resp.json():
            return jsonify({'error': 'Not found'}), 404
        existing_data = resp.json()[0].get('data', {})
        existing_data.pop('paid_at', None)
        upd_headers = {**headers, 'Prefer': 'resolution=merge-duplicates'}
        requests.post(
            f"{base}/rest/v1/prize_money_submissions",
            json={'player_id': player_id, 'data': existing_data, 'paid_at': None,
                  'submitted_at': existing_data.get('submitted_at', datetime.now().isoformat())},
            headers=upd_headers
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""

# Insert before export route
insert_before = "# ─── Export CSV"
if insert_before in content:
    content = content.replace(insert_before, new_route + insert_before)
    print("Added mark_paid routes: OK")
else:
    # fallback: append before last line
    content = content.rstrip() + "\n" + new_route
    print("Added mark_paid routes (fallback): OK")

# 2. Update gestor_view to pass paid_at
old_gestor = """        records.append({**sub, 'player_id': pid, 'doc_url': doc_url})"""
new_gestor = """        # Get doc_url_p2
        doc_url_p2 = None
        if sub.get('doc_path_p2'):
            doc_url_p2 = get_doc_url(sub['doc_path_p2'])
        paid_at = sub.get('paid_at') or ''
        records.append({**sub, 'player_id': pid, 'doc_url': doc_url, 'doc_url_p2': doc_url_p2, 'paid_at': paid_at})"""

if old_gestor in content:
    content = content.replace(old_gestor, new_gestor)
    print("Updated gestor_view: OK")
else:
    print("gestor_view block NOT FOUND - checking existing...")
    idx = content.find("records.append({**sub")
    print(repr(content[idx:idx+200]))

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print("Done!")
