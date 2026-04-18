f = open('templates/prize_money/gestor.html', 'r', encoding='utf-8')
content = f.read()
f.close()

content = content.replace(
    "{% set wpc_recs = records | selectattr('form_type', 'in', ['WPC', 'BOTH']) | list %}",
    "{% set wpc_recs = records | selectattr('form_type', 'ne', 'PCL') | list %}"
)

f = open('templates/prize_money/gestor.html', 'w', encoding='utf-8')
f.write(content)
f.close()
print('Done')
