f = open('templates/prize_money/gestor.html', 'r', encoding='utf-8')
content = f.read()
f.close()

# Fix badge display
content = content.replace(
    "{% if r.form_type == 'WPC' %}<span class=\"badge-wpc\">WPC</span>\n               {% else %}<span class=\"badge-pcl\">PCL</span>{% endif %}",
    "<span class=\"badge-wpc\">WPC</span>"
)

# Fix gross display
content = content.replace(
    "{% if r.form_type == 'WPC' %}€{{ r.wpc_total_gross }}{% else %}€{{ r.pcl_total_gross }}{% endif %}",
    "€{{ r.wpc_total_gross }}"
)

# Fix tax display
content = content.replace(
    "{% if r.form_type == 'WPC' %}{{ r.wpc_tax_rate }}% ({{ r.wpc_tax_type }})",
    "{{ r.wpc_tax_rate }}% ({{ r.wpc_tax_type }})"
)

# Fix net display
content = content.replace(
    "{% if r.form_type == 'WPC' %}€{{ r.wpc_net_amount }}{% else %}€{{ r.pcl_total_gross }}{% endif %}",
    "€{{ r.wpc_net_amount }}"
)

f = open('templates/prize_money/gestor.html', 'w', encoding='utf-8')
f.write(content)
f.close()
print('Done')
