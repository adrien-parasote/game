"""
Apply calibration result from scripts/calibration_result.py into title_screen_constants.py.
Run: python3 scripts/apply_calibration.py
"""
import re
import sys
import os

RESULT_PATH = os.path.join("scripts", "calibration_result.py")
CONSTANTS_PATH = os.path.join("src", "ui", "title_screen_constants.py")


def _extract(content: str, var: str) -> str | None:
    """Extract a variable assignment block (list) from content."""
    m = re.search(rf"({re.escape(var)}\s*=\s*\[.*?\])", content, re.DOTALL)
    return m.group(1) if m else None


def _inject(constants: str, var: str, new_block: str) -> str:
    """Replace existing variable block in constants, or append if missing."""
    pattern = rf"{re.escape(var)}\s*=\s*\[.*?\]"
    updated, n = re.subn(pattern, new_block, constants, flags=re.DOTALL)
    if n == 0:
        # Not found — append before last line
        updated = constants.rstrip() + f"\n\n{new_block}\n"
    return updated


def main() -> None:
    if not os.path.exists(RESULT_PATH):
        sys.stdout.write(f"ERROR: {RESULT_PATH} not found. Run scripts/calibrate_halos.py first.")
        sys.exit(1)

    with open(RESULT_PATH) as f:
        result = f.read()

    fire_block = _extract(result, "BACKGROUND_LIGHTS")
    mush_block = _extract(result, "MUSHROOM_LIGHTS")

    if not fire_block:
        sys.stdout.write("ERROR: BACKGROUND_LIGHTS not found in result file.")
        sys.exit(1)

    with open(CONSTANTS_PATH) as f:
        constants = f.read()

    constants = _inject(constants, "BACKGROUND_LIGHTS", fire_block)
    if mush_block:
        constants = _inject(constants, "MUSHROOM_LIGHTS", mush_block)

    with open(CONSTANTS_PATH, "w") as f:
        f.write(constants)

    n_fire = fire_block.count("(") - 1  # subtract the list open
    n_mush = mush_block.count("(") // 2 if mush_block else 0
    sys.stdout.write(f"✅ Applied {n_fire} fire + {n_mush} mushroom halos to {CONSTANTS_PATH}")
    sys.stdout.write("Run: python3 -m pytest tests/ui/test_title_screen.py -q")


if __name__ == "__main__":
    main()
