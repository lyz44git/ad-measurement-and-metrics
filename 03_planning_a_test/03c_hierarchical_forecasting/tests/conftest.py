import sys
from pathlib import Path

import pytest

# make the study's package and the shared test helpers importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hier_toy import make_toy_src  # noqa: E402


@pytest.fixture
def toy_src():
    return make_toy_src()
