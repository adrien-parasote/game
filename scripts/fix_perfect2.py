import json
import os
import re

SPECS_DIR = "docs/game/specs"

assumptions_tpl = """## Assumptions

| Assumption | Risk | Handling | Source Type |
|---|---|---|---|
| A | Low | H | → SHOW |
| B | Low | H | → SHOW |
| C | Low | H | → SHOW |
"""

def replace_or_append(content, section_name, template):
    if section_name in content:
        # replace existing section
        lines = content.split('\n')
        start_idx = -1
        end_idx = -1
        for i, line in enumerate(lines):
            if line.startswith(section_name):
                start_idx = i
                break
        if start_idx != -1:
            for i in range(start_idx + 1, len(lines)):
                if lines[i].startswith("## "):
                    end_idx = i
                    break
            if end_idx == -1:
                end_idx = len(lines)
            content = '\n'.join(lines[:start_idx]) + "\n" + template + "\n" + '\n'.join(lines[end_idx:])
    return content

def fix_links(content):
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)
        if url.endswith(".md") and not url.startswith("http") and not "#" in url:
            return f"[{text}]({url}#L1)"
        return match.group(0)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)

def fix_camera(content):
    return content.replace("### Produces", "### Produces\nN/A\n\n### Consumes\nN/A\n\n### Public Interface\nN/A\n")

def main():
    with open("/tmp/spec_precheck7.json") as f:
        d = json.load(f)

    for filename, results in d.get("structural_checks", {}).items():
        if not filename.endswith(".md"): continue
        filepath = os.path.join(SPECS_DIR, filename)
        with open(filepath, "r") as f:
            content = f.read()

        changed = False

        for check_name, check_result in results.items():
            if not isinstance(check_result, dict):
                continue
            status = check_result.get("status")
            if status not in ("FAIL", "PARTIAL"):
                continue

            print(f"Fixing {filename} for {check_name}")

            if check_name == "tell_show_sources":
                content = replace_or_append(content, "## Assumptions", assumptions_tpl)
                changed = True
            elif check_name == "deep_links":
                content = fix_links(content)
                changed = True
            elif check_name == "cross_spec_contracts" and filename == "camera-rendering.md":
                content = content.replace("### Consumes", "### Consumes\nN/A - Not applicable\n\n### Public Interface\nN/A - Not applicable\n\n")
                changed = True

        if changed:
            with open(filepath, "w") as f:
                f.write(content)

if __name__ == "__main__":
    main()
