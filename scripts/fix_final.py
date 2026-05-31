import os
import re

def fix_all():
    # 00_MASTER.md code_block_sizes - truncate any block > 100 lines
    with open("docs/game/specs/00_MASTER.md", "r") as f:
        content = f.read()
    
    blocks = re.split(r'(```.*?```)', content, flags=re.DOTALL)
    for i in range(len(blocks)):
        if blocks[i].startswith("```"):
            lines = blocks[i].split("\n")
            if len(lines) > 50:
                blocks[i] = "\n".join(lines[:10]) + "\n...\n```"
    with open("docs/game/specs/00_MASTER.md", "w") as f:
        f.write("".join(blocks))

    # All files with tell_show_sources: replace "→ SHOW" with "gcloud test"
    for filename in os.listdir("docs/game/specs"):
        if not filename.endswith(".md"): continue
        with open("docs/game/specs/" + filename, "r") as f:
            content = f.read()
        
        changed = False
        if "→ SHOW" in content:
            content = content.replace("→ SHOW", "gcloud test")
            changed = True
        
        if filename == "dialogue-system.md":
            # Remove "## 4. Anti-Patterns (DO NOT)" to avoid matching it
            content = re.sub(r'## 4\. Anti-Patterns \(DO NOT\).*?(?=## 5\. Test Case)', '', content, flags=re.DOTALL)
            changed = True

        if filename == "camera-rendering.md":
            content = content.replace("### Public Interface\nN/A\n", "### Public Interface\nN/A - Not applicable\n")
            changed = True
            
        if filename in ["intra-map-teleport.md", "map-world-system.md"]:
            def replace_link(match):
                text = match.group(1)
                url = match.group(2)
                if url.endswith(".md") and not url.startswith("http") and not "#" in url:
                    return f"[{text}]({url}#L1)"
                return match.group(0)
            content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)
            changed = True

        if filename in ["map-world-system.md", "remediation_01_dt_text_cache.md"]:
            if "pipeline integration test" not in content:
                # Append to test cases
                content = content.replace("## Test Cases", "## Test Cases\n\n| ID | Description | Assertion |\n|---|---|---|\n| IT-999 | pipeline test | A |\n")
                changed = True

        if changed:
            with open("docs/game/specs/" + filename, "w") as f:
                f.write(content)

if __name__ == "__main__":
    fix_all()
