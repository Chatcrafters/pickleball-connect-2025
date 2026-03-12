content = open('routes/prize_money.py', encoding='utf-8').read()

old_supabase = """# ─── Supabase ─────────────────────────────────────────────────────────────────
def get_supabase():
    from supabase import create_client
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY')
    return create_client(url, key)"""

new_supabase = """# ─── Supabase REST ───────────────────────────────────────────────────────────
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
    \"\"\"Returns a simple dict-based client for REST calls\"\"\"
    return {'url': supabase_url(), 'headers': get_supabase_headers()}"""

if old_supabase in content:
    content = content.replace(old_supabase, new_supabase)
    print('Fix supabase client: OK')
else:
    idx = content.find('def get_supabase')
    print('NOT FOUND, showing:', repr(content[idx:idx+200]))

# Fix ensure_bucket to use requests
old_bucket = """def ensure_bucket():
    try:
        sb = get_supabase()
        sb.storage.from_(BUCKET).list()
    except Exception as e:
        print(f'Bucket check error: {e}')"""

new_bucket = """def ensure_bucket():
    pass  # Bucket already exists"""

if old_bucket in content:
    content = content.replace(old_bucket, new_bucket)
    print('Fix ensure_bucket: OK')
else:
    idx = content.find('def ensure_bucket')
    print('ensure_bucket NOT FOUND, showing:', repr(content[idx:idx+200]))

# Fix upload_doc to use requests
old_upload_doc = """def upload_doc(player_id, file_bytes, filename, content_type, page=1):
    try:
        sb = get_supabase()
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
        path = f"{player_id}/id_document_p{page}.{ext}"
        sb.storage.from_(BUCKET).upload(
            path, file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        return path
    except Exception as e:
        print(f'Upload error: {e}')
        return None"""

new_upload_doc = """def upload_doc(player_id, file_bytes, filename, content_type, page=1):
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
        return None"""

if old_upload_doc in content:
    content = content.replace(old_upload_doc, new_upload_doc)
    print('Fix upload_doc: OK')
else:
    idx = content.find('def upload_doc')
    print('upload_doc NOT FOUND, showing:', repr(content[idx:idx+300]))

# Fix get_doc_url to use requests
old_doc_url = """def get_doc_url(path):
    try:
        sb = get_supabase()
        result = sb.storage.from_(BUCKET).create_signed_url(path, 3600)
        return result.get('signedURL') or result.get('signedUrl')
    except Exception as e:
        print(f'Doc URL error: {e}')
        return None"""

new_doc_url = """def get_doc_url(path):
    try:
        base = supabase_url()
        headers = get_supabase_headers()
        headers['Content-Type'] = 'application/json'
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
        return None"""

if old_doc_url in content:
    content = content.replace(old_doc_url, new_doc_url)
    print('Fix get_doc_url: OK')
else:
    idx = content.find('def get_doc_url')
    print('get_doc_url NOT FOUND, showing:', repr(content[idx:idx+300]))

# Fix load_submissions to use requests
old_load = """def load_submissions():
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

new_load = """def load_submissions():
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
        return {}"""

if old_load in content:
    content = content.replace(old_load, new_load)
    print('Fix load_submissions: OK')
else:
    idx = content.find('def load_submissions')
    print('load_submissions NOT FOUND, showing:', repr(content[idx:idx+300]))

# Fix save_submission to use requests
old_save = """def save_submission(player_id, data):
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

new_save = """def save_submission(player_id, data):
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
        print(f'Warning: could not save to Supabase: {e}')"""

if old_save in content:
    content = content.replace(old_save, new_save)
    print('Fix save_submission: OK')
else:
    idx = content.find('def save_submission')
    print('save_submission NOT FOUND, showing:', repr(content[idx:idx+300]))

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('\nDone! supabase import remaining:', 'from supabase import' in content)
