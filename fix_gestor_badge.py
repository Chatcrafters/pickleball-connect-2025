f = open('templates/prize_money/gestor.html', 'r', encoding='utf-8')
content = f.read()
f.close()

# Fix pcl_recs stat
content = content.replace(
    "{% set pcl_recs = records | selectattr('form_type', 'equalto', 'PCL') | list %}",
    "{% set pcl_recs = [] %}"
)

# Fix badge in table
old = "{% if r.form_type == 'WPC' %}<span class=\"badge-wpc\">WPC</span>\n               {% else %}<span class=\"badge-pcl\">PCL</span>{% endif %}"
new = "<span class=\"badge-wpc\">WPC</span>"
if old in content:
    content = content.replace(old, new)
    print("Badge replaced")
else:
    print("Badge NOT found - checking raw...")
    print(repr(content[content.find('badge-wpc">WPC')-50:content.find('badge-wpc">WPC')+150]))

f = open('templates/prize_money/gestor.html', 'w', encoding='utf-8')
f.write(content)
f.close()
print('Done')
