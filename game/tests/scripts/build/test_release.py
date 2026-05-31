import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add root to sys.path to import from scripts (go up 3 levels to reach workspace root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from scripts.build.release import run_git_commands, update_version, validate_version


@pytest.fixture
def test_settings(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"version": "0.6.0"}))
    return str(settings_path)


@pytest.mark.tc("TC-REL-01")
def test_validate_version():
    assert validate_version("0.6.1")
    assert validate_version("1.0.0")
    assert validate_version("2.1.3-beta")
    assert not validate_version("invalid")
    assert not validate_version("1.0")


@pytest.mark.tc("TC-REL-02")
def test_update_version(test_settings):
    update_version(test_settings, "0.6.1")
    with open(test_settings) as f:
        data = json.load(f)
        assert data["version"] == "0.6.1"


@pytest.mark.tc("TC-REL-03")
@patch("subprocess.run")
def test_run_git_commands(mock_run):
    # Define side effects for different git commands
    def side_effect(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "status" in cmd:
            mock.stdout = ""
        elif "branch" in cmd:
            mock.stdout = "main"
        elif "tag" in cmd and "-l" in cmd:
            mock.stdout = ""
        else:
            mock.stdout = ""
        return mock

    mock_run.side_effect = side_effect

    # Test basic flow
    run_git_commands("0.6.1", dry_run=False)

    # Check if git commands were called
    assert mock_run.call_count >= 5


if __name__ == "__main__":
    pytest.main([__file__])
