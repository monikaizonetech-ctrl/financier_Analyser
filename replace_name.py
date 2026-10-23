import os
import re

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return

    orig_content = content

    # 1. Domains and emails
    content = re.sub(r'iZone Analyzer\.in', 'iZoneAnalyzer.in', content, flags=re.IGNORECASE)
    
    # 2. Local storage keys and internal variables
    content = content.replace('izone_token', 'izone_token')
    content = content.replace('izone_user', 'izone_user')
    content = content.replace('izone_pass', 'izone_pass')

    # 3. Exact UI casing
    content = content.replace('iZone Analyzer', 'iZone Analyzer')
    content = content.replace('iZoneAnalyzer', 'iZoneAnalyzer')

    if content != orig_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk(r'c:\Users\IZONE 194\Downloads\Financier'):
    if 'node_modules' in root or '.git' in root or '__pycache__' in root or 'venv' in root:
        continue
    for file in files:
        if file.endswith(('.py', '.js', '.jsx', '.html', '.json', '.css')):
            replace_in_file(os.path.join(root, file))

print("Replacement complete.")
