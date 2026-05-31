# conftest for calibration tests — adds tools/src to sys.path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
