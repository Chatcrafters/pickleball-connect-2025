content = open('templates/prize_money/form_wpc.html', encoding='utf-8').read()

# Check current state
print('Has doUpload:', 'doUpload' in content)
print('Has endblock:', 'endblock' in content)
print('Lines:', len(content.splitlines()))

upload_js = """
let docUploaded = false;
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
}
"""

# Insert before closing </script> tag that's before {% endblock %}
if '</script>' in content and '{% endblock %}' in content:
    # Find last </script> before endblock
    endblock_pos = content.rfind('{% endblock %}')
    script_close_pos = content.rfind('</script>', 0, endblock_pos)
    content = content[:script_close_pos] + upload_js + '</script>\n{% endblock %}'
    open('templates/prize_money/form_wpc.html', 'w', encoding='utf-8').write(content)
    print('Injected doUpload successfully')
    print('Has doUpload now:', 'doUpload' in content)
else:
    print('ERROR: Could not find insertion point')
    print('Has </script>:', '</script>' in content)
    print('Has endblock:', '{% endblock %}' in content)
