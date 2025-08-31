#!/usr/bin/env python3
"""Simple runner for the torrent creator"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main

if __name__ == "__main__":
    main()
