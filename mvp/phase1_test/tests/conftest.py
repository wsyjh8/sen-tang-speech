"""Pytest configuration - adds project root to sys.path."""

import sys
from pathlib import Path

import pytest

# Add project root to sys.path for proper module imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as requiring external API access"
    )
