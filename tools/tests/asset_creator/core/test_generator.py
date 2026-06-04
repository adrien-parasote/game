import numpy as np
from src.asset_creator.core.generator import generate_texture

def test_generate_grass_valid():
    """ Grass should generate values within [0, 1, 2, 3] """
    arr = generate_texture("grass", seed=42, density=10, sub_type="classic")
    assert arr.shape == (32, 32)
    assert np.all((arr >= 0) & (arr <= 3))

def test_generate_sub_types():
    """ Different sub_types should produce slightly different arrays due to different tufts """
    arr_classic = generate_texture("grass", seed=42, density=10, sub_type="classic")
    arr_short = generate_texture("grass", seed=42, density=10, sub_type="short")
    
    # Due to different tuft matrices being applied with the same seed, the output should differ
    assert not np.array_equal(arr_classic, arr_short)
    assert np.all(np.isin(arr_classic, [0, 1, 2, 3]))

def test_tc005_generator_fallback():
    """TC-005: Unknown texture_type is handled gracefully."""
    output = generate_texture("some_unknown_type", seed=42, density=10)
    assert output.shape == (32, 32)
    assert np.all(np.isin(output, [0, 1, 2, 3]))

def test_tc007_determinism():
    """TC-007: Same seed = same ndarray output."""
    out1 = generate_texture("grass", seed=42, density=10)
    out2 = generate_texture("grass", seed=42, density=10)
    assert np.array_equal(out1, out2)
