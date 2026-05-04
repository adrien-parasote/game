"""
Apply calibration result from scripts/calibration_result.py into title_screen_constants.py.
Run: python3 scripts/apply_calibration.py
"""
import re
import sys
import os

RESULT_PATH = os.path.join("scripts", "calibration_result.py")
CONSTANTS_PATH = os.path.join("src", "ui", "title_screen_constants.py")


def _load_result(path: str) -> str:
    """Return the BACKGROUND_LIGHTS block from calibration result."""
    with open(path) as f:
        content = f.read()
    # Extract the list block
    m = re.search(r"(BACKGROUND_LIGHTS\s*=\s*\[.*?\])", content, re.DOTALL)
    if not m:
        sys.stdout.write("ERROR: BACKGROUND_LIGHTS not found in result file.")
        sys.exit(1)
    return m.group(1)


def _apply(constants_path: str, new_block: str) -> None:
    with open(constants_path) as f:
        content = f.read()

    updated = re.sub(
        r"BACKGROUND_LIGHTS\s*=\s*\[.*?\]",
        new_block,
        content,
        flags=re.DOTALL,
    )
    if updated == content:
        sys.stdout.write("ERROR: Could not find BACKGROUND_LIGHTS in constants file.")
        sys.exit(1)

    with open(constants_path, "w") as f:
        f.write(updated)

    sys.stdout.write(f"✅ Applied {new_block.count('('):d} light sources to {constants_path}")


if __name__ == "__main__":
    if not os.path.exists(RESULT_PATH):
        print(f"ERROR: {RESULT_PATH} not found. Run scripts/calibrate_halos.py first.")
        sys.exit(1)
    block = _load_result(RESULT_PATH)
    _apply(CONSTANTS_PATH, block)
    print("Done. Run tests to verify:")
    print("  python3 -m pytest tests/ui/test_title_screen.py -q")
