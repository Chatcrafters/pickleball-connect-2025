content = open('templates/base.html', encoding='utf-8').read()

insert = """                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            <i class="bi bi-currency-euro"></i> Prize Money
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/prize-money/admin/wpc"><i class="bi bi-trophy"></i> WPC Admin</a></li>
                            <li><a class="dropdown-item" href="/prize-money/admin/pcl"><i class="bi bi-trophy-fill"></i> PCL Admin</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="/prize-money/gestor"><i class="bi bi-file-earmark-text"></i> Gestor View</a></li>
                        </ul>
                    </li>
"""

# Find the Login nav item and insert before it
target = "url_for('auth.login')"
idx = content.find(target)
if idx == -1:
    print("ERROR: target not found")
else:
    # Find the start of that <li> tag
    li_start = content.rfind('<li class="nav-item">', 0, idx)
    content = content[:li_start] + insert + content[li_start:]
    open('templates/base.html', 'w', encoding='utf-8').write(content)
    print('Done:', content.count('Prize Money'), 'occurrence(s) added')
