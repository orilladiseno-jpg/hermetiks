import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def isolated_appdata(tmp_path, monkeypatch):
    """Never touch the real %APPDATA%/Hermetiks."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path
