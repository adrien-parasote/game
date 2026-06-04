import numpy as np
from asset_creator.core.generator import generate_texture


def test_generate_grass_valid():
    """ Grass should generate values within [0, 1, 2, 3, 4] """
    arr = generate_texture("grass", seed=42, density=10, sub_type="classic")
    assert arr.shape == (32, 32)
    assert np.all((arr >= 0) & (arr <= 4))

def test_generate_sub_types():
    """ Different sub_types should produce slightly different arrays due to different tufts """
    arr_classic = generate_texture("grass", seed=42, density=10, sub_type="classic")
    arr_short = generate_texture("grass", seed=42, density=10, sub_type="short")

    # Due to different tuft matrices being applied with the same seed, the output should differ
    assert not np.array_equal(arr_classic, arr_short)
    assert np.all(np.isin(arr_classic, [0, 1, 2, 3, 4]))

def test_tc005_generator_fallback():
    """TC-005: Unknown texture_type is handled gracefully."""
    output = generate_texture("some_unknown_type", seed=42, density=10)
    assert output.shape == (32, 32)
    assert np.all(np.isin(output, [0, 1, 2, 3, 4]))

def test_tc005_crescent_highlight():
    """TC-005: With sub_type='crescent', returns a numpy array where np.max >= 4"""
    arr = generate_texture("grass", seed=42, density=10, sub_type="crescent")
    assert np.max(arr) >= 4

def test_tc006_crescent_values():
    """TC-006: With sub_type='crescent', returns a (32, 32) array with values in {0,1,2,3,4}"""
    arr = generate_texture("grass", seed=42, density=10, sub_type="crescent")
    assert arr.shape == (32, 32)
    assert np.all(np.isin(arr, [0, 1, 2, 3, 4]))

def test_it002_toroidal_wrapping():
    """IT-002: Verify toroidal wrapping correctly handles a 6x6 (or 5x5) tuft placed at the edge."""
    from asset_creator.core.generator import apply_composite_stamp
    # create a small grid
    grid = np.zeros((32, 32), dtype=int)
    # mock a 5x5 crescent tuft
    tuft = [
        [-1, -1,  4,  4, -1],
        [-1,  3,  4,  4,  3],
        [ 2,  3,  3,  3,  2],
        [ 1,  2,  2,  2,  1],
        [-1,  0,  0,  0, -1]
    ]
    # stamp at 30, 30
    apply_composite_stamp(grid, tuft, 30, 30)
    # check that wrapping occurred correctly
    assert grid[30, 30] == 0
    assert grid[30, 31] == 0
    assert grid[31, 31] == 3
    # Check pixels that wrapped to 0,0 etc.
    assert grid[30, 0] == 4
    assert grid[30, 1] == 4
    assert grid[31, 0] == 4


def test_tc007_determinism():
    """TC-007: Same seed = same ndarray output."""
    out1 = generate_texture("grass", seed=42, density=10)
    out2 = generate_texture("grass", seed=42, density=10)
    assert np.array_equal(out1, out2)
