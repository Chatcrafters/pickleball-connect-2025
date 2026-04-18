f = open('templates/prize_money/gestor.html', 'r', encoding='utf-8')
content = f.read()
f.close()

content = content.replace(
    "              {{ r.wpc_tax_rate }}% ({{ r.wpc_tax_type }})\n              {% else %}<span style=\"color:#0d6b5e;\">None</span>{% endif %}",
    "              {{ r.wpc_tax_rate }}% ({{ r.wpc_tax_type }})"
)

f = open('templates/prize_money/gestor.html', 'w', encoding='utf-8')
f.write(content)
f.close()
print('Done')
