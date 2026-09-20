import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

@pytest.fixture(autouse=True)
def configure_testing_mode():
    """Ensure tests run with TESTING=True by default unless explicitly overridden."""
    original = settings.TESTING
    settings.TESTING = True
    yield
    settings.TESTING = original
