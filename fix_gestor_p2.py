content = open('routes/prize_money.py', encoding='utf-8').read()

old1 = """        doc_url = None
        if sub.get('doc_path'):
            doc_url = get_doc_url(sub['doc_path'])
        records.append({**sub, 'player_id': pid, 'doc_url': doc_url})"""

new1 = """        doc_url = None
        if sub.get('doc_path'):
            doc_url = get_doc_url(sub['doc_path'])
        doc_url_p2 = None
        if sub.get('doc_path_p2'):
            doc_url_p2 = get_doc_url(sub['doc_path_p2'])
        records.append({**sub, 'player_id': pid, 'doc_url': doc_url, 'doc_url_p2': doc_url_p2})"""

if old1 in content:
    content = content.replace(old1, new1)
    print('Fix 1: OK')
else:
    print('Fix 1: NOT FOUND')

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('Done!')
