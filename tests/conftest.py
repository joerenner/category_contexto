import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def tmp_db_path(tmp_path):
    return tmp_path / "test_rankings.db"
