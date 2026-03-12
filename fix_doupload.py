content = open('templates/prize_money/form_wpc.html', encoding='utf-8').read()

# Replace old single-slot doUpload with page-aware version
old_fn = """let docUploaded = false;
async function doUpload(input) {
  const file = input.files[0];
  if (!file) return;
  const prompt = document.getElementById('upload-prompt');
  const ok = document.getElementById('upload-ok');
  const err = document.getElementById('upload-err');
  prompt.innerHTML = '<div style="font-size:13px;color:#888;">Uploading...</div>';
  err.style.display = 'none';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch(`/prize-money/upload/${TOKEN}`, {method:'POST', body:fd});
    const d = await res.json();
    if (d.success) {
      docUploaded = true;
      document.getElementById('upload-area').style.borderColor = '#1B998B';
      document.getElementById('upload-area').style.background = '#e8f5f3';
      prompt.style.display = 'none';
      ok.textContent = '\\u2713 ' + file.name + ' uploaded';
      ok.style.display = 'block';
      const btn = document.getElementById('btn1next');
      if (btn) { btn.disabled = false; }
      const req = document.getElementById('upload-required');
      if (req) { req.style.display = 'none'; }
    } else {
      prompt.innerHTML = '<div style="font-size:13px;color:#856404;">Click to upload document</div>';
      err.textContent = d.error || 'Upload failed';
      err.style.display = 'block';
    }
  } catch(e) {
    prompt.innerHTML = '<div style="font-size:13px;color:#856404;">Click to upload document</div>';
    err.textContent = 'Upload failed. Please try again.';
    err.style.display = 'block';
  }
}"""

new_fn = """let docUploaded = false;
async function doUpload(input, page) {
  page = page || 1;
  const file = input.files[0];
  if (!file) return;
  const prompt = document.getElementById('upload-prompt-' + page);
  const ok = document.getElementById('upload-ok-' + page);
  const err = document.getElementById('upload-err-' + page);
  const area = document.getElementById('upload-area-' + page);
  if (prompt) prompt.innerHTML = '<div style="font-size:13px;color:#888;">Uploading...</div>';
  if (err) err.style.display = 'none';
  const fd = new FormData();
  fd.append('file', file);
  fd.append('page', page);
  try {
    const res = await fetch(`/prize-money/upload/${TOKEN}`, {method:'POST', body:fd});
    const d = await res.json();
    if (d.success) {
      if (area) { area.style.borderColor = '#1B998B'; area.style.background = '#e8f5f3'; }
      if (prompt) prompt.style.display = 'none';
      if (ok) { ok.textContent = '\\u2713 ' + file.name; ok.style.display = 'block'; }
      if (page == 1) {
        docUploaded = true;
        const btn = document.getElementById('btn1next');
        if (btn) btn.disabled = false;
        const req = document.getElementById('upload-required');
        if (req) req.style.display = 'none';
      }
    } else {
      if (prompt) prompt.innerHTML = '<div style="font-size:13px;color:#856404;">Click to upload</div>';
      if (err) { err.textContent = d.error || 'Upload failed'; err.style.display = 'block'; }
    }
  } catch(e) {
    if (prompt) prompt.innerHTML = '<div style="font-size:13px;color:#856404;">Click to upload</div>';
    if (err) { err.textContent = 'Upload failed. Please try again.'; err.style.display = 'block'; }
  }
}"""

if old_fn in content:
    content = content.replace(old_fn, new_fn)
    print('Replaced old doUpload with page-aware version')
else:
    # Try partial match - find and replace whatever doUpload exists
    import re
    pattern = r'let docUploaded = false;\nasync function doUpload\(input\).*?\n\}'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_fn, content, flags=re.DOTALL)
        print('Replaced via regex')
    else:
        # Find position of doUpload and show context
        idx = content.find('async function doUpload')
        print(f'doUpload found at pos {idx}')
        print('Context:', repr(content[idx:idx+100]))

open('templates/prize_money/form_wpc.html', 'w', encoding='utf-8').write(content)
print('Has page param:', 'page = page || 1' in content)
print('Done')
