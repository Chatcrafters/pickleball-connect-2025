content = open('routes/prize_money.py', encoding='utf-8').read()

# Replace load_pm_users with hardcoded version
old = """def load_pm_users():
    if not os.path.exists(PM_USERS_FILE):
        default = {
            'wpc_admin': {'password': generate_password_hash('wpc2026malaga'), 'role': 'wpc'},
            'pcl_admin': {'password': generate_password_hash('pcl2026malaga'), 'role': 'pcl'},
            'gestor': {'password': generate_password_hash('gestor2026'), 'role': 'gestor'},
        }
        with open(PM_USERS_FILE, 'w') as f:
            json.dump(default, f, indent=2)
    with open(PM_USERS_FILE) as f:
        return json.load(f)"""

new = """def load_pm_users():
    # Hardcoded users - no filesystem dependency (works on Vercel)
    return {
        'wpc_admin': {'password': 'wpc2026malaga', 'role': 'wpc'},
        'pcl_admin': {'password': 'pcl2026malaga', 'role': 'pcl'},
        'gestor': {'password': 'gestor2026', 'role': 'gestor'},
    }"""

if old in content:
    content = content.replace(old, new)
    print('load_pm_users: OK')
else:
    # Try without return line
    idx = content.find('def load_pm_users():')
    end = content.find('\ndef ', idx+1)
    old2 = content[idx:end]
    print('Actual function:')
    print(repr(old2))

# Also fix login to use plain text comparison instead of check_password_hash
old_login = "if username in users and check_password_hash(users[username]['password'], password):"
new_login = "if username in users and users[username]['password'] == password:"

if old_login in content:
    content = content.replace(old_login, new_login)
    print('login check: OK')
else:
    idx = content.find('check_password_hash')
    if idx > 0:
        print('check_password_hash context:', repr(content[idx-50:idx+100]))
    else:
        print('check_password_hash not found - searching for login logic...')
        idx = content.find("users[username]")
        print(repr(content[max(0,idx-20):idx+100]))

open('routes/prize_money.py', 'w', encoding='utf-8').write(content)
print('Done!')
