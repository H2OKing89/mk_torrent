#!/usr/bin/env python3
"""Entry point for the torrent creator application"""

import sys
from pathlib import Path

# Add the script directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

try:
    from cli import main
    
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"Error: {e}")
    print("\nPlease ensure you're in the correct directory:")
    print("  cd /mnt/cache/scripts/mk_torrent")
    print("  python run.py [command]")
    sys.exit(1)
