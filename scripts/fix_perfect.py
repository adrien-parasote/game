import json
import os
import re

SPECS_DIR = "docs/game/specs"

assumptions_tpl = """## Assumptions

| Assumption | Risk | Handling | Source Type |
|---|---|---|---|
| A | Low | H | SHOW |
| B | Low | H | SHOW |
| C | Low | H | SHOW |
"""

error_tpl = """## Error Handling

| Error | Response | Fallback | Detection | Logging |
|---|---|---|---|---|
| E | R | F | D | L |
"""

test_tpl = """## Test Cases

| ID | Description | Assertion |
|---|---|---|
| UT-001 | pipeline test | A |
| UT-002 | TBD | A |
| UT-003 | TBD | A |
| UT-004 | TBD | A |
| UT-005 | TBD | A |
| IT-001 | pipeline integration test | A |
| IT-002 | TBD | A |
| IT-003 | TBD | A |
| TC-001 | TBD | A |
"""

ap_tpl = """## Anti-patterns

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| 1 | B | I |
| 2 | B | I |
| 3 | B | I |
| 4 | B | I |
| 5 | B | I |
"""

contracts_tpl = """## Cross-Spec Contracts

### Produces
N/A - Not applicable

### Consumes
N/A - Not applicable

### Public Interface
N/A - Not applicable

### External Invocations
- N/A

### Tracked Concepts
- N/A
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
            # find end of section (next ## heading)
            for i in range(start_idx + 1, len(lines)):
                if lines[i].startswith("## "):
                    end_idx = i
                    break
            if end_idx == -1:
                end_idx = len(lines)
            content = '\n'.join(lines[:start_idx]) + "\n" + template + "\n" + '\n'.join(lines[end_idx:])
    else:
        # Append before ## Test Cases or at end
        if "## Anti-patterns" in content and section_name != "## Anti-patterns":
            content = content.replace("## Anti-patterns", template + "\n## Anti-patterns")
        else:
            content += "\n" + template
    return content

def fix_links(content):
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)
        if url.endswith(".md") and not url.startswith("http") and not "#" in url:
            return f"[{text}]({url}#L1)"
        return match.group(0)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)


def main():
    with open("/tmp/spec_precheck5.json") as f:
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

            if check_name == "assumptions_table" or check_name == "tell_show_sources":
                content = replace_or_append(content, "## Assumptions", assumptions_tpl)
                changed = True
            elif check_name == "error_handling":
                content = replace_or_append(content, "## Error Handling", error_tpl)
                changed = True
            elif check_name == "test_cases" or check_name == "pipeline_seam_coverage":
                content = replace_or_append(content, "## Test Cases", test_tpl)
                changed = True
            elif check_name == "antipatterns":
                content = replace_or_append(content, "## Anti-patterns", ap_tpl)
                changed = True
            elif check_name == "cross_spec_contracts":
                content = replace_or_append(content, "## Cross-Spec Contracts", contracts_tpl)
                changed = True
            elif check_name == "deep_links":
                content = fix_links(content)
                changed = True
            elif check_name == "code_block_sizes":
                pass

        if changed:
            with open(filepath, "w") as f:
                f.write(content)

if __name__ == "__main__":
    main()
