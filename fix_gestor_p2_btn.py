content = open('templates/prize_money/gestor.html', encoding='utf-8').read()

# Find the exact doc_url block
idx = content.find('{% if r.doc_url %}')
end = content.find('</td>', idx) + 5
old = content[idx:end]
print('Found block:')
print(repr(old))

new = """{% if r.doc_url %}
                <a href="{{ r.doc_url }}" target="_blank" class="btn btn-outline-dark doc-btn" style="font-size:11px;padding:2px 7px;">P1</a>
              {% elif r.doc_path %}
                <a href="/prize-money/gestor/doc/{{ r.player_id }}" target="_blank" class="btn btn-outline-dark doc-btn" style="font-size:11px;padding:2px 7px;">P1</a>
              {% else %}
                <span class="no-doc">&mdash;</span>
              {% endif %}
              {% if r.doc_url_p2 %}
                <a href="{{ r.doc_url_p2 }}" target="_blank" class="btn btn-outline-secondary" style="font-size:11px;padding:2px 7px;margin-left:2px;">P2</a>
              {% endif %}
            </td>"""

content = content[:idx] + new + content[end:]
open('templates/prize_money/gestor.html', 'w', encoding='utf-8').write(content)
print('doc_url_p2 in template:', 'doc_url_p2' in content)
print('Done!')
