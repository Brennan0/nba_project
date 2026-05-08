"""
pytest configuration – add the backend directory to sys.path so that tests
can import backend modules directly.
"""

import sys
import os

# Add the backend directory so tests can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
