content = open('routes/prize_money.py', encoding='utf-8').read()

# Replace load_submissions
old_load = """def load_submissions():
    if not os.path.exists(SUBMISSIONS_FILE):
        return {}
    with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)"""

new_load = """def load_submissions():
    try:
        sb = get_supabase()
        result = sb.table('prize_money_submissions').select('*').execute()
        return {row['player_id']: row['data'] for row in result.data}
    except Exception as e:
        print(f'Warning: could not load submissions from Supabase: {e}')
        # Fallback to local file
        if os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}"""

if old_load in content:
    content = content.replace(old_load, new_load)
    print('load_submissions: OK')
else:
    idx = content.find('def load_submissions')
    print('NOT FOUND - actual:')
    print(repr(content[idx:idx+200]))

# Replace save_submission
old_save = """def save_submission(player_id, data):
    submissions = load_submissions()
    submissions[player_id] = {**data, 'submitted_at': datetime.now().isoformat()}
    with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(submissions, f, indent=2, ensure_ascii=False)"""

new_save = """def save_submission(player_id, data):
    record = {**data, 'submitted_at': datetime.now().isoformat()}
    try:
        sb = get_supabase()
        sb.table('prize_money_submissions').upsert({
            'player_id': player_id,
            'data': record,
            'submitted_at': record['submitted_at'],
        }).execute()
    except Exception as e:
        print(f'Warning: could not save to Supabase: {e}')
        # Fallback to local file
        try:
            submissions = {}
            if os.path.exists(SUBMISSIONS_FILE):
                with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
                    submissions = json.load(f)
            submissions[player_id] = record
            with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(submissions, f, indent=2, ensure_ascii=False)
        except Exception as e2:
            print(f'Warning: local fallback also failed: {e2}')"""

if old_save in content:
    content = content.replace(old_save, new_save)
    print('save_submission: OK')
else:
    idx = content.find('def save_submission')
    print('save_submission NOT FOUND - actual:')
    print(repr(content[idx:idx+200]))

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('Done!')
