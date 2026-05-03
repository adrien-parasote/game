import os
import re

FRENCH_WORDS = {
    ' le ', ' la ', ' les ', ' des ', ' pour ', ' avec ', ' dans ', ' sur ', 
    ' un ', ' une ', ' est ', ' ou ', ' et ', ' sont ', ' fait ', ' faire ',
    ' quand ', ' si ', ' ça ', ' ce ', ' ça ', ' de ', ' du '
}

def check_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = []
    for i, line in enumerate(lines):
        if '#' in line:
            comment = line[line.index('#'):].lower()
            if any(w in comment for w in FRENCH_WORDS) or re.search(r'[éàèçù]', comment):
                found.append(f"{i+1}: {line.strip()}")
    
    if found:
        print(f"--- {path} ---")
        for f in found:
            print(f)

for root, _, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            check_file(os.path.join(root, file))
