import pytest
from asset_creator.core.constants import (
    TUFT_ARCH,
    TUFT_CRESCENT_1,
    TUFT_CRESCENT_2,
    TUFT_SWEEP_LEFT,
    TUFT_SWEEP_RIGHT,
)


def test_tc004_tuft_matrices_valid():
    """TC-004: All new 5x5 tuft matrices contain only integers from {-1, 0, 1, 2, 3, 4}."""
    valid_values = {-1, 0, 1, 2, 3, 4}
    tufts = [
        TUFT_CRESCENT_1, TUFT_CRESCENT_2,
        TUFT_SWEEP_LEFT, TUFT_SWEEP_RIGHT,
        TUFT_ARCH
    ]

    for tuft in tufts:
        assert len(tuft) == 5, "Tuft should be 5x5"
        for row in tuft:
            assert len(row) == 5, "Tuft should be 5x5"
            for val in row:
                assert val in valid_values, f"Invalid value {val} in tuft"


def test_tc001_constants_pruned():
    """TC-001: Check that unused constants are pruned from constants.py."""
    import asset_creator.core.constants as consts

    # These constants should be pruned
    pruned_vars = [
        "MASK_THRESHOLD",
        "DEFAULT_NOISE_SCALE",
        "DEFAULT_LACUNARITY",
        "BORDER_SHADOW_FACTOR",
        "BAYER_4X4",
        "DEFAULT_PALETTES"
    ]

    for var in pruned_vars:
        assert not hasattr(consts, var), f"Constant {var} should be pruned but is still present"


def test_tc004_no_french_developer_comments():
    """TC-004: Ensure no French developer comments remain in source files.

    Note: UI-visible strings (buttons, labels, dialogs) intentionally remain
    in French per spec constraint. This check targets developer comments only.
    """
    import re
    from pathlib import Path

    tools_src = Path(__file__).parents[3] / "src"
    files_to_check = [
        tools_src / "asset_creator" / "core" / "converter_xp.py",
        tools_src / "asset_creator" / "gui" / "app.py"
    ]

    # Look for common French comment words or accents
    french_indicators = re.compile(r'#.*(?:virage|absence|surface|taille|grille|état|principale|icone|bouton|sélecteur|efface|cellule|motifs)', re.IGNORECASE)

    for filepath in files_to_check:
        assert filepath.exists(), f"File {filepath} does not exist"
        content = filepath.read_text(encoding="utf-8")
        matches = french_indicators.findall(content)
        assert not matches, f"Found French comments in {filepath.name}: {matches}"

