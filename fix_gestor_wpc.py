f = open('templates/prize_money/gestor.html', 'r', encoding='utf-8')
content = f.read()
f.close()

# Fix stats counters (BOTH zaehlt als WPC hier)
content = content.replace(
    "{% set wpc_recs = records | selectattr('form_type', 'equalto', 'WPC') | list %}",
    "{% set wpc_recs = records | selectattr('form_type', 'in', ['WPC', 'BOTH']) | list %}"
)
content = content.replace(
    "{% set pcl_recs = records | selectattr('form_type', 'equalto', 'PCL') | list %}",
    "{% set pcl_recs = [] %}"
)

# Fix badge in table (WPC Gestor = immer WPC Badge)
content = content.replace(
    "{% if r.form_type == 'WPC' %}<span class=\"badge-wpc\">WPC</span>\n               {% else %}<span class=\"badge-pcl\">PCL</span>{% endif %}",
    "<span class=\"badge-wpc\">WPC</span>"
)

# Fix JS modal: BOTH treated as WPC
content = content.replace(
    "const isWPC = r.form_type === 'WPC';",
    "const isWPC = r.form_type === 'WPC' || r.form_type === 'BOTH';"
)

f = open('templates/prize_money/gestor.html', 'w', encoding='utf-8')
f.write(content)
f.close()
print('Done')
