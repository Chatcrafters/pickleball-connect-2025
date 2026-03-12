content = open('templates/prize_money/gestor.html', encoding='utf-8').read()

old = """            <td>
              {% if r.doc_url %}
                <a href="{{ r.doc_url }}" target="_blank" class="btn btn-outline-dark doc-btn">View</a>
              {% elif r.doc_path %}
                <a href="/prize-money/gestor/doc/{{ r.player_id }}" target="_blank" class="btn btn-outline-dark doc-btn">View</a>
              {% else %}
                <span class="no-doc">&mdash;</span>
              {% endif %}
            </td>"""

new = """            <td>
              {% if r.doc_url %}
                <a href="{{ r.doc_url }}" target="_blank" class="btn btn-outline-dark doc-btn" style="font-size:11px;padding:2px 7px;">P1</a>
              {% elif r.doc_path %}
                <a href="/prize-money/gestor/doc/{{ r.player_id }}" target="_blank" class="btn btn-outline-dark doc-btn" style="font-size:11px;padding:2px 7px;">P1</a>
              {% else %}
                <span class="no-doc">&mdash;</span>
              {% endif %}
              {% if r.doc_url_p2 %}
                <a href="{{ r.doc_url_p2 }}" target="_blank" class="btn btn-outline-secondary doc-btn" style="font-size:11px;padding:2px 7px;margin-left:2px;">P2</a>
              {% endif %}
            </td>"""

# Try exact match first
if old in content:
    content = content.replace(old, new)
    print('Fix: OK (exact)')
else:
    # Try with encoded dash
    old2 = old.replace('&mdash;', 'â€"')
    if old2 in content:
        content = content.replace(old2, new)
        print('Fix: OK (encoded dash)')
    else:
        print('Fix: NOT FOUND - showing doc_url section:')
        idx = content.find('doc_url')
        print(repr(content[idx:idx+300]))

open('templates/prize_money/gestor.html', 'w', encoding='utf-8').write(content)
print('Done! doc_url_p2 in template:', 'doc_url_p2' in content)
