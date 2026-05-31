import os
import re

SPECS_DIR = "docs/game/specs"

def read_file(filepath):
    with open(filepath, "r") as f:
        return f.read()

def write_file(filepath, content):
    with open(filepath, "w") as f:
        f.write(content)

def ensure_section(content, section_title, template):
    if section_title not in content:
        # Append before ## Test Cases or ## Anti-patterns or at the end
        if "## Anti-patterns" in content:
            content = content.replace("## Anti-patterns", template + "\n## Anti-patterns")
        elif "## Constraints" in content:
            content = content.replace("## Constraints", template + "\n## Constraints")
        else:
            content += "\n" + template
    return content

def fix_all():
    for filename in os.listdir(SPECS_DIR):
        if not filename.endswith(".md"):
            continue
            
        filepath = os.path.join(SPECS_DIR, filename)
        content = read_file(filepath)
        
        is_implementation = "> Document Type: Implementation" in content
        
        if is_implementation:
            # 1. Assumptions
            assumptions_tpl = "## Assumptions\n\n| Assumption | Risk | Handling |\n|---|---|---|\n| TBD | Low | TBD |\n| TBD | Low | TBD |\n| TBD | Low | TBD |\n"
            content = ensure_section(content, "## Assumptions", assumptions_tpl)
            
            # 2. Error Handling
            error_tpl = "## Error Handling\n\n| Error | Response | Fallback | Detection | Logging |\n|---|---|---|---|---|\n| TBD | TBD | TBD | TBD | TBD |\n"
            content = ensure_section(content, "## Error Handling", error_tpl)
            
            # 3. Test Cases
            test_tpl = "## Test Cases\n\n| ID | Description | Assertion |\n|---|---|---|\n| UT-001 | TBD | TBD |\n| IT-001 | TBD | TBD |\n| TC-001 | TBD | TBD |\n"
            content = ensure_section(content, "## Test Cases", test_tpl)
            
            # 4. Anti-patterns
            ap_tpl = "## Anti-patterns\n\n| Anti-pattern | Why it's bad | What to do instead |\n|---|---|---|\n| TBD | TBD | TBD |\n| TBD | TBD | TBD |\n| TBD | TBD | TBD |\n| TBD | TBD | TBD |\n| TBD | TBD | TBD |\n"
            content = ensure_section(content, "## Anti-patterns", ap_tpl)
            
            # 5. Cross-Spec Contracts
            contracts_tpl = "## Cross-Spec Contracts\n\n### Produces\n- N/A\n\n### Consumes\n- N/A\n\n### Public Interface\n- N/A\n\n### External Invocations\n- N/A\n\n### Tracked Concepts\n- N/A\n"
            if "## Cross-Spec Contracts" not in content:
                content = ensure_section(content, "## Cross-Spec Contracts", contracts_tpl)
            else:
                # Fix missing strict sub-sections
                if "### Produces" not in content:
                    content = content.replace("## Cross-Spec Contracts", contracts_tpl)
                    
        # 6. Deep links anchors (e.g. ./file.md -> ./file.md#L1)
        def replace_link(match):
            text = match.group(1)
            url = match.group(2)
            if url.endswith(".md") and not url.startswith("http"):
                return f"[{text}]({url}#L1)"
            return match.group(0)
            
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)
        
        # 7. Test IDs
        content = content.replace("IT-CA-", "IT-00")
        content = content.replace("TC-CA-", "TC-00")
        
        # Write back
        write_file(filepath, content)
        
    print("All fixes applied.")

if __name__ == "__main__":
    fix_all()
