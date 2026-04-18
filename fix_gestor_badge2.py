f = open('templates/prize_money/gestor.html', 'r', encoding='utf-8')
content = f.read()
f.close()

old = "{% if r.form_type == 'WPC' %}<span class=\"badge-wpc\">WPC</span>\n              {% else %}<span class=\"badge-pcl\">PCL</span>{% endif %}"
new = "<span class=\"badge-wpc\">WPC</span>"
if old in content:
    content = content.replace(old, new)
    print("Badge replaced OK")
else:
    print("Still not found")

f = open('templates/prize_money/gestor.html', 'w', encoding='utf-8')
f.write(content)
f.close()
