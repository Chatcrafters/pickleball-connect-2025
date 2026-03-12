import re

path = 'templates/prize_money/form_wpc.html'
content = open(path, encoding='utf-8').read()

print(f'Lines before: {len(content.splitlines())}')
print(f'Has doUpload: {"doUpload" in content}')
print(f'Has upload-area-1: {"upload-area-1" in content}')

# 1. Replace single upload area with two slots
old_upload = None
# Find the upload form-card section
start = content.find('<div class="form-card" style="border:2px dashed #dee2e6;">')
if start == -1:
    start = content.find('ID Document Upload')
    start = content.rfind('<div', 0, start)

# Find the matching closing </div> for the form-card
# Count divs from start
pos = start
depth = 0
end = start
i = start
while i < len(content):
    if content[i:i+4] == '<div':
        depth += 1
    elif content[i:i+6] == '</div>':
        depth -= 1
        if depth == 0:
            end = i + 6
            break
    i += 1

old_block = content[start:end]

new_upload = '''  <div class="form-card" style="border:2px dashed #dee2e6;">
    <h5>ID Document Upload</h5>
    <p style="font-size:12px;color:#666;margin-bottom:4px;">Please upload both sides of your ID document (passport photo page, NIE, DNI or ID card front &amp; back). Accepted: PDF, JPG, PNG. Max 10MB each.</p>
    <p style="font-size:11px;color:#888;font-style:italic;margin-bottom:14px;">Sube ambas caras de tu documento (pasaporte, NIE, DNI). Formatos: PDF, JPG, PNG. Max. 10MB cada uno.</p>
    <div style="margin-bottom:12px;">
      <div style="font-size:12px;font-weight:700;color:#856404;margin-bottom:6px;">Page 1 / Front &mdash; Pagina 1 / Anverso <span style="color:#dc3545;">*</span></div>
      <div id="upload-area-1" style="border:2px dashed #C9A84C;border-radius:8px;padding:16px;text-align:center;cursor:pointer;background:#fffbf0;" onclick="document.getElementById('doc-file-1').click()">
        <div id="upload-prompt-1"><div style="font-size:22px;margin-bottom:4px;">&#128206;</div><div style="font-size:13px;font-weight:600;color:#856404;">Click to upload</div><div style="font-size:11px;color:#aaa;">PDF, JPG or PNG</div></div>
        <div id="upload-ok-1" style="display:none;color:#1B998B;font-weight:600;font-size:13px;"></div>
        <div id="upload-err-1" style="display:none;color:#dc3545;font-size:12px;"></div>
      </div>
      <input type="file" id="doc-file-1" accept=".pdf,.jpg,.jpeg,.png,.heic" style="display:none;" onchange="doUpload(this, 1)">
    </div>
    <div>
      <div style="font-size:12px;font-weight:700;color:#856404;margin-bottom:6px;">Page 2 / Back &mdash; Pagina 2 / Reverso <span style="color:#888;font-weight:400;">(optional)</span></div>
      <div id="upload-area-2" style="border:2px dashed #dee2e6;border-radius:8px;padding:16px;text-align:center;cursor:pointer;background:#fafafa;" onclick="document.getElementById('doc-file-2').click()">
        <div id="upload-prompt-2"><div style="font-size:22px;margin-bottom:4px;">&#128206;</div><div style="font-size:13px;font-weight:600;color:#888;">Click to upload</div><div style="font-size:11px;color:#aaa;">PDF, JPG or PNG</div></div>
        <div id="upload-ok-2" style="display:none;color:#1B998B;font-weight:600;font-size:13px;"></div>
        <div id="upload-err-2" style="display:none;color:#dc3545;font-size:12px;"></div>
      </div>
      <input type="file" id="doc-file-2" accept=".pdf,.jpg,.jpeg,.png,.heic" style="display:none;" onchange="doUpload(this, 2)">
    </div>
  </div>'''

content = content.replace(old_block, new_upload)

# 2. Replace/inject doUpload JS before </script>{% endblock %}
new_js = """
let docUploaded = false;
async function doUpload(input, page) {
  const file = input.files[0];
  if (!file) return;
  const prompt = document.getElementById('upload-prompt-' + page);
  const ok = document.getElementById('upload-ok-' + page);
  const err = document.getElementById('upload-err-' + page);
  const area = document.getElementById('upload-area-' + page);
  prompt.innerHTML = '<div style="font-size:13px;color:#888;">Uploading...</div>';
  err.style.display = 'none';
  const fd = new FormData();
  fd.append('file', file);
  fd.append('page', page);
  try {
    const TOKEN_VAL = document.querySelector('[data-token]') ? document.querySelector('[data-token]').dataset.token : window.PLAYER_TOKEN;
    const res = await fetch('/prize-money/upload/' + window.PLAYER_TOKEN, {method:'POST', body:fd});
    const d = await res.json();
    if (d.success) {
      area.style.borderColor = '#1B998B';
      area.style.background = '#e8f5f3';
      prompt.style.display = 'none';
      ok.textContent = '\\u2713 ' + file.name;
      ok.style.display = 'block';
      if (page === 1) {
        docUploaded = true;
        const btn = document.getElementById('btn1next');
        if (btn) btn.disabled = false;
        const req = document.getElementById('upload-required');
        if (req) req.style.display = 'none';
      }
    } else {
      prompt.innerHTML = '<div style="font-size:13px;color:#856404;">Click to upload</div>';
      err.textContent = d.error || 'Upload failed';
      err.style.display = 'block';
    }
  } catch(e) {
    prompt.innerHTML = '<div style="font-size:13px;color:#856404;">Click to upload</div>';
    err.textContent = 'Upload failed. Please try again.';
    err.style.display = 'block';
  }
}
"""

# Find TOKEN variable in existing script and ensure PLAYER_TOKEN is set
# Look for existing TOKEN = line
if 'const TOKEN =' in content:
    content = content.replace('const TOKEN =', 'window.PLAYER_TOKEN =\n  const TOKEN =')
elif "TOKEN = '" in content or 'TOKEN="' in content:
    pass

# Replace old doUpload or inject before </script>{% endblock %}
if 'async function doUpload' in content:
    # Remove old version
    start_js = content.find('let docUploaded')
    end_js = content.find('\n}', start_js) + 2
    content = content[:start_js] + new_js.strip() + content[end_js:]
else:
    # Inject before last </script>
    endblock = content.rfind('{% endblock %}')
    script_close = content.rfind('</script>', 0, endblock)
    content = content[:script_close] + new_js + '</script>\n{% endblock %}'

open(path, 'w', encoding='utf-8').write(content)
print(f'Lines after: {len(content.splitlines())}')
print(f'Has doUpload: {"doUpload" in content}')
print(f'Has upload-area-1: {"upload-area-1" in content}')
print(f'Has upload-area-2: {"upload-area-2" in content}')
print('Done!')
