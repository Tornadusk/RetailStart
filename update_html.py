import os
import re

files = [
    r'C:\Users\aronb\Desktop\RetailStart\backend\templates\core\home.html',
    r'C:\Users\aronb\Desktop\RetailStart\backend\templates\core\dashboard.html',
    r'C:\Users\aronb\Desktop\RetailStart\backend\templates\core\analytics.html',
    r'C:\Users\aronb\Desktop\RetailStart\backend\templates\core\evidence.html',
    r'C:\Users\aronb\Desktop\RetailStart\backend\templates\core\flow.html'
]

def add_classes(html_content, target_class, extra_classes):
    # Match class="target_class"
    pattern1 = r'class="' + target_class + r'"'
    # Match class="target_class some_other_classes"
    pattern2 = r'class="' + target_class + r'\s+([^"]+)"'
    
    # We will just replace all, but to prevent double replace, we can read the content,
    # find matches, and then do sub if extra_classes not already present
    def repl1(m):
        return f'class="{target_class} {extra_classes}"'
        
    def repl2(m):
        # check if already added
        if extra_classes in m.group(1):
            return m.group(0)
        return f'class="{target_class} {extra_classes} {m.group(1)}"'
        
    html_content = re.sub(pattern2, repl2, html_content)
    html_content = re.sub(pattern1, repl1, html_content)
    return html_content

for filepath in files:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Insert tailwind_head
    if '{% include "core/includes/tailwind_head.html" %}' not in content:
        content = content.replace('</head>', '    {% include "core/includes/tailwind_head.html" %}\n  </head>')

    # 1. Background general
    content = content.replace('<div class="appShell__main">', '<div class="appShell__main bg-bone-darker font-sans text-stone-700 min-h-screen">')
    
    # 2. Tarjetas
    content = add_classes(content, 'card', 'bg-bone-light border border-stone-300/40 rounded-xl shadow-sm p-5')
    content = add_classes(content, 'tile chartTile', 'bg-bone-light border border-stone-300/40 rounded-xl shadow-sm')

    # 3. KPIs
    content = add_classes(content, 'kpi', 'bg-white border-l-4 border-l-mars-secondary border-y border-r border-stone-300/40 rounded-r-xl shadow-sm p-4')

    # 4. Tipografia
    content = add_classes(content, 'title', 'font-bold tracking-tight text-3xl text-stone-900 mb-2')
    content = content.replace('<h2>', '<h2 class="text-xl font-bold text-stone-900 mb-4">')
    content = add_classes(content, 'subtitle', 'text-lg text-stone-900 mb-4')
    content = add_classes(content, 'muted', 'text-stone-500')

    # 5. UI Elements: Botones
    # For btn--inline, we want secondary colors
    content = add_classes(content, 'btn--inline', 'bg-white border border-stone-300 text-stone-700 hover:border-mars-accent hover:text-mars-accent shadow-sm rounded-md px-3 py-1 transition-colors')
    
    # For normal btn we want primary colors. But btn--inline might contain btn. So we should process btn--inline first? No, btn--inline is just a class.
    # Actually btn is usually first: class="btn btn--inline".
    # Let's just do:
    content = add_classes(content, 'btn', 'bg-mars-sidebar text-white hover:bg-mars-surface shadow-sm rounded-md px-4 py-2 transition-colors')
    
    # After adding btn classes, if btn--inline is present, the primary colors are added. 
    # Tailwind classes last added usually win? No, CSS specificity or order in CSS file.
    # We should just let both exist, or replace 'bg-mars-sidebar text-white hover:bg-mars-surface' with '' if btn--inline.
    content = content.replace('bg-mars-sidebar text-white hover:bg-mars-surface shadow-sm rounded-md px-4 py-2 transition-colors btn--inline', 'btn--inline bg-white border border-stone-300 text-stone-700 hover:border-mars-accent hover:text-mars-accent shadow-sm rounded-md px-3 py-1 transition-colors')

    # Consolas / Código
    content = content.replace('<code>', '<code class="bg-mars-bg border border-mars-border text-mars-textMain font-mono rounded px-1 py-0.5 text-sm">')

    # Links
    content = add_classes(content, 'link', 'text-mars-accent hover:text-mars-secondary transition-colors underline')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Updated HTML files.")
