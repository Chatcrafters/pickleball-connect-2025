content = open('routes/prize_money.py', encoding='utf-8').read()

# Fix ensure_bucket - find and replace by position
start = content.find('def ensure_bucket():')
end = content.find('\ndef ', start + 1)
old = content[start:end]
print('ensure_bucket found:', repr(old[:50]))
new_bucket = """def ensure_bucket():
    pass  # Bucket already exists
"""
content = content[:start] + new_bucket + content[end:]
print('ensure_bucket: OK')

# Fix get_doc_url - find and replace by position
start = content.find('def get_doc_url(path):')
end = content.find('\n# ─── Countries', start)
if end == -1:
    end = content.find('\ndef ', start + 1)
old = content[start:end]
print('get_doc_url found:', repr(old[:80]))
new_doc_url = """def get_doc_url(path):
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
"""
content = content[:start] + new_doc_url + content[end:]
print('get_doc_url: OK')

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('supabase import remaining:', 'from supabase import' in content)
print('sb.storage remaining:', 'sb.storage' in content)
print('Done!')
