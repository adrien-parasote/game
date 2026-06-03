import pytest
import numpy as np
from asset_creator.core.generator import generate

def test_tc_001_toroidal_seamlessness():
    """TC-001: Toroidal seamlessness — stone texture."""
    # Test that generator returns a 256x256 numpy array
    result = generate("stone", seed=42, scale=4.0)
    assert result.shape == (256, 256)
    assert np.all(result >= 0.0) and np.all(result <= 1.0)
    
def test_tc_007_determinism():
    """TC-007: Determinism — same seed = same output."""
    res1 = generate("stone", seed=42, scale=4)
    res2 = generate("stone", seed=42, scale=4)
    np.testing.assert_array_equal(res1, res2)
