import json
import os
import sys

def get_version():
    """Extract and print the game version from settings.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
    if not os.path.exists(config_path):
        print("Error: settings.json not found", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            version = config.get("version")
            if version:
                print(version)
            else:
                print("Error: 'version' key not found in settings.json", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print(f"Error reading settings.json: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    get_version()
