content = open('routes/prize_money.py', encoding='utf-8').read()

# Find and replace the entire function by position
start = content.find('def load_pm_users():')
end = content.find('\ndef ', start + 1)
old = content[start:end]

new = """def load_pm_users():
    # Hardcoded users - no filesystem needed (works on Vercel)
    return {
        'wpc_admin': {'password': 'wpc2026malaga', 'role': 'wpc'},
        'pcl_admin': {'password': 'pcl2026malaga', 'role': 'pcl'},
        'gestor': {'password': 'gestor2026', 'role': 'gestor'},
    }
"""

content = content[:start] + new + content[end:]
open('routes/prize_money.py', 'w', encoding='utf-8').write(content)

# Verify
c = open('routes/prize_money.py', encoding='utf-8').read()
idx = c.find('def load_pm_users')
print(c[idx:idx+200])
print('Done!')
