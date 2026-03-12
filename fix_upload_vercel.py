content = open('routes/prize_money.py', encoding='utf-8').read()

old = """    # Save doc path in submissions temp store
    submissions = load_submissions()
    if player['id'] not in submissions:
        submissions[player['id']] = {}
    key = 'doc_path' if page_num == '1' else 'doc_path_p2'
    submissions[player['id']][key] = path
    submissions[player['id']]['doc_uploaded_at'] = datetime.now().isoformat()
    with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as sf:
        json.dump(submissions, sf, indent=2, ensure_ascii=False)
    return jsonify({'success': True, 'path': path})"""

new = """    # Save doc path in submissions temp store (best effort - may fail on Vercel)
    try:
        submissions = load_submissions()
        if player['id'] not in submissions:
            submissions[player['id']] = {}
        key = 'doc_path' if page_num == '1' else 'doc_path_p2'
        submissions[player['id']][key] = path
        submissions[player['id']]['doc_uploaded_at'] = datetime.now().isoformat()
        with open(SUBMISSIONS_FILE, 'w', encoding='utf-8') as sf:
            json.dump(submissions, sf, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f'Warning: could not save doc_path to submissions: {e}')
    return jsonify({'success': True, 'path': path})"""

if old in content:
    content = content.replace(old, new)
    print('Fix: OK')
else:
    idx = content.find('Save doc path in submissions')
    print('NOT FOUND - context:')
    print(repr(content[idx:idx+400]))

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('Done!')
