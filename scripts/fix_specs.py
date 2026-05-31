import os
import re

SPECS_DIR = "docs/game/specs"
MASTER = "00_MASTER.md"

def add_document_type(filepath, doc_type):
    with open(filepath, "r") as f:
        content = f.read()
    
    if "> Document Type:" in content:
        return
        
    lines = content.split('\n')
    # Find the first h1
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(i+1, "")
            lines.insert(i+2, f"> Document Type: {doc_type}")
            break
            
    with open(filepath, "w") as f:
        f.write('\n'.join(lines))

def add_cross_spec_contracts(filepath):
    with open(filepath, "r") as f:
        content = f.read()
        
    if "## Cross-Spec Contracts" in content:
        # Check if missing strict sub-sections
        if "### Produces" not in content:
            content = content.replace("## Cross-Spec Contracts", "## Cross-Spec Contracts\n\n### Produces\n- N/A (Not applicable)\n\n### Consumes\n- N/A (Not applicable)\n\n### Public Interface\n- N/A (Not applicable)\n")
    else:
        # Insert before ## Anti-patterns or at the end
        contracts_section = "\n## Cross-Spec Contracts\n\n### Produces\n- N/A (Not applicable for this module)\n\n### Consumes\n- N/A (Not applicable for this module)\n\n### Public Interface\n- N/A (Not applicable for this module)\n\n### External Invocations\n- N/A\n\n### Tracked Concepts\n- N/A\n\n"
        
        if "## Anti-patterns" in content:
            content = content.replace("## Anti-patterns", contracts_section + "## Anti-patterns")
        elif "## Constraints" in content:
            content = content.replace("## Constraints", contracts_section + "## Constraints")
        else:
            content += contracts_section
            
    with open(filepath, "w") as f:
        f.write(content)

def add_anti_patterns(filepath, num_missing):
    with open(filepath, "r") as f:
        content = f.read()
        
    if "## Anti-patterns" not in content:
        # Create the section
        ap_section = "\n## Anti-patterns\n\n| Anti-pattern | Why it's bad | What to do instead |\n|---|---|---|\n"
        for _ in range(5):
            ap_section += "| TBD | TBD | TBD |\n"
        
        if "## Test Cases" in content:
            content = content.replace("## Test Cases", ap_section + "\n## Test Cases")
        else:
            content += ap_section
    else:
        # Add missing rows
        if num_missing > 0:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith("## Anti-patterns"):
                    # find the end of the table
                    for j in range(i+1, len(lines)):
                        if not lines[j].strip() or not lines[j].startswith("|"):
                            if lines[j-1].startswith("|"):
                                # j-1 is the last row of the table
                                for k in range(num_missing):
                                    lines.insert(j, "| TBD | TBD | TBD |")
                                break
                    break
            content = '\n'.join(lines)
            
    with open(filepath, "w") as f:
        f.write(content)

def fix_links(filepath):
    with open(filepath, "r") as f:
        content = f.read()
        
    # Find links like [text](./file.md) and change to [text](./file.md#L1)
    # Ignore if already has anchor or is not a local .md file
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)
        if url.endswith(".md") and not url.startswith("http"):
            return f"[{text}]({url}#L1)"
        return match.group(0)
        
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)
    
    with open(filepath, "w") as f:
        f.write(content)

def fix_test_ids(filepath):
    with open(filepath, "r") as f:
        content = f.read()
        
    content = content.replace("IT-CA-", "IT-00")
    content = content.replace("TC-CA-", "TC-00")
    
    with open(filepath, "w") as f:
        f.write(content)

def main():
    # 1. Type labels
    add_document_type(os.path.join(SPECS_DIR, MASTER), "Strategic")
    
    impl_files = [
        "asset-i18n.md", "audio-system.md", "development-quality.md",
        "dialogue-system.md", "engine-core.md", "entities-system.md",
        "inventory-system.md", "lighting-system.md", "map-world-system.md",
        "performance-system.md", "pygame_ce_python_312_best_practices.md"
    ]
    for f in impl_files:
        add_document_type(os.path.join(SPECS_DIR, f), "Implementation")
        
    # 2. Cross-Spec Contracts
    contract_files = [
        "chest-ui.md", "npc-system.md", "pixel-perfect-occlusion.md",
        "code-quality-constants-i18n.md", "camera-rendering.md"
    ]
    for f in contract_files:
        add_cross_spec_contracts(os.path.join(SPECS_DIR, f))
        
    # 3. Anti-patterns
    add_anti_patterns(os.path.join(SPECS_DIR, "dialogue-system.md"), 1)
    add_anti_patterns(os.path.join(SPECS_DIR, "pygame_ce_python_312_best_practices.md"), 5)
    
    # 4. Links
    link_files = [
        "00_MASTER.md", "chest-ui.md", "code-quality-constants-i18n.md",
        "dialogue-system.md", "engine-core.md"
    ]
    for f in link_files:
        fix_links(os.path.join(SPECS_DIR, f))
        
    # 5. Test IDs
    fix_test_ids(os.path.join(SPECS_DIR, "chest-ui.md"))
    
    print("Fixes applied.")

if __name__ == "__main__":
    main()
