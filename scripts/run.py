#!/usr/bin/env python3
"""Entry point for the mk_torrent application using the new src layout."""

import sys
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from mk_torrent.cli import main

    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"Error importing mk_torrent: {e}")
    print(
        "\nPlease ensure you're in the correct directory and the virtual environment is activated:"
    )
    print("  cd /mnt/cache/scripts/mk_torrent")
    print("  source .venv/bin/activate")
    print("  python scripts/run_new.py")
    sys.exit(1)
