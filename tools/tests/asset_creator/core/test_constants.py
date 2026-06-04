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
