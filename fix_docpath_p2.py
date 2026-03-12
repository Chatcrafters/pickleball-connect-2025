content = open('routes/prize_money.py', encoding='utf-8').read()

# Fix 1: read doc_path_p2 from existing submission
old1 = "    doc_path = existing.get('doc_path', '')"
new1 = "    doc_path = existing.get('doc_path', '')\n    doc_path_p2 = existing.get('doc_path_p2', '')"
if old1 in content:
    content = content.replace(old1, new1)
    print('Fix 1: OK')
else:
    print('Fix 1: NOT FOUND')

# Fix 2: save doc_path_p2 in submission
old2 = "        'doc_path': doc_path,"
new2 = "        'doc_path': doc_path,\n        'doc_path_p2': doc_path_p2,"
if old2 in content:
    content = content.replace(old2, new2)
    print('Fix 2: OK')
else:
    print('Fix 2: NOT FOUND')

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('doc_path_p2 count:', content.count('doc_path_p2'))
print('Done!')
