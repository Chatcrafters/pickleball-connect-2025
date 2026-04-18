f = open('templates/base.html', 'r', encoding='utf-8')
content = f.read()
f.close()

old = '                            <li><a class="dropdown-item" href="/prize-money/gestor"><i class="bi bi-file-earmark-text"></i> Gestor View</a></li>'
new = '                            <li><a class="dropdown-item" href="/prize-money/gestor"><i class="bi bi-file-earmark-text"></i> Gestor WPC</a></li>\n                            <li><a class="dropdown-item" href="/prize-money/gestor/pcl"><i class="bi bi-file-earmark-text"></i> Gestor PCL</a></li>'

if old in content:
    content = content.replace(old, new)
    print("Done")
else:
    print("Not found")

f = open('templates/base.html', 'w', encoding='utf-8')
f.write(content)
f.close()
