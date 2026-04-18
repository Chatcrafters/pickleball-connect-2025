f = open('routes/prize_money.py', 'r', encoding='utf-8')
content = f.read()
f.close()
old = "        if sub.get('form_type') != 'PCL':\n            continue"
new = "        if sub.get('form_type') not in ('PCL', 'BOTH'):\n            continue"
content = content.replace(old, new)
f = open('routes/prize_money.py', 'w', encoding='utf-8')
f.write(content)
f.close()
print('Done')
