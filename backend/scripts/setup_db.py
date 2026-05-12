#!/usr/bin/env python3
"""
Setup Database Wrapper
This script is a wrapper for setup_production.py to ensure compatibility
with documentation and legacy setup commands.
"""

import sys
import os

# Add the scripts directory to path to import setup_production
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import setup_production
    if __name__ == "__main__":
        setup_production.main()
except ImportError:
    print("Error: Could not find setup_production.py in the same directory.")
    sys.exit(1)
except Exception as e:
    print(f"Error during database setup: {e}")
    sys.exit(1)
