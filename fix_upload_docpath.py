content = open('routes/prize_money.py', encoding='utf-8').read()

old = """    # Save doc path in submissions temp store (best effort - may fail on Vercel)
    try:
        submissions = load_submissions()
        if player['id'] not in submissions:
            submissions[player['id']] = {}
        key = 'doc_path' if page_num == '1' else 'doc_path_p2'
        submissions[player['id']][key] = path
        submissions[player['id']]['doc_uploaded_at'] = datetime.now().isoformat()
       
 with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as sf:\n            json.dump(submissions, sf, indent=2, ensure_ascii=False)\n    except Exception as e:\n  
      print(f'Warning: could not s"""

# Find the block by start marker
start = content.find("    # Save doc path in submissions temp store")
end = content.find("\n    return jsonify({'path'", start)
if end == -1:
    end = content.find("\n    return jsonify({'success'", start)
if end == -1:
    end = content.find("\n    return jsonify({", start)

print(f"Block found: {start} to {end}")
print("Old block:", repr(content[start:end]))

new_block = """    # Save doc_path immediately to Supabase (upsert partial record)
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
        print(f'Warning: could not save doc_path to Supabase: {e}')"""

content = content[:start] + new_block + content[end:]
open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print("Done!")
print("Verify - showing patched area:")
idx2 = content.find("# Save doc_path immediately")
print(repr(content[idx2:idx2+400]))
