"""
Configuration for Ansible Collection unit tests.
This module sets up the necessary paths to import modules from the collection.
"""

import os
import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.parent

# Add the project root to sys.path to allow proper imports
sys.path.insert(0, str(project_root))