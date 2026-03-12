content = open('routes/prize_money.py', encoding='utf-8').read()

# Fix 1: add page param to upload_doc and use it in filename
old1 = """def upload_doc(player_id, file_bytes, filename, content_type):
    try:
        sb = get_supabase()
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
        path = f"{player_id}/id_document.{ext}\""""
new1 = """def upload_doc(player_id, file_bytes, filename, content_type, page=1):
    try:
        sb = get_supabase()
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
        path = f"{player_id}/id_document_p{page}.{ext}\""""

if old1 in content:
    content = content.replace(old1, new1)
    print('Fix 1: OK')
else:
    print('Fix 1: NOT FOUND - checking actual content...')
    idx = content.find('def upload_doc')
    print(repr(content[idx:idx+200]))

# Fix 2: pass page to upload_doc call (only if not already done)
old2 = "    path = upload_doc(player['id'], file_bytes, f.filename, f.content_type)"
new2 = "    page_num = request.form.get('page', '1')\n    path = upload_doc(player['id'], file_bytes, f.filename, f.content_type, page_num)"

if old2 in content:
    content = content.replace(old2, new2)
    print('Fix 2: OK')
elif 'page_num' in content:
    print('Fix 2: already applied')
else:
    print('Fix 2: NOT FOUND')
    idx = content.find('upload_doc(player')
    print(repr(content[idx:idx+100]))

# Fix 3: ensure doc_path_p2 logic uses page_num not page
old3 = "    page = request.form.get('page', '1')\n    key = 'doc_path' if page == '1' else 'doc_path_p2'"
new3 = "    key = 'doc_path' if page_num == '1' else 'doc_path_p2'"

if old3 in content:
    content = content.replace(old3, new3)
    print('Fix 3: OK')
elif new3 in content:
    print('Fix 3: already applied')
else:
    # try alternative
    old3b = "    page = request.form.get('page', '1')\n    key = 'doc_path' if page == '1' else 'doc_path_p2'"
    if old3b in content:
        content = content.replace(old3b, "    key = 'doc_path' if page_num == '1' else 'doc_path_p2'")
        print('Fix 3b: OK')
    else:
        print('Fix 3: NOT FOUND - checking...')
        idx = content.find("doc_path_p2")
        print(repr(content[max(0,idx-100):idx+50]))

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('id_document_p in content:', 'id_document_p' in content)
print('page_num in content:', 'page_num' in content)
print('Done!')
