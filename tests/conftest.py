from pathlib import Path

import pytest

from trustdesk.answer import Engine
from trustdesk.embed import HashEmbedder
from trustdesk.store import Store

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data"


@pytest.fixture(scope="session")
def sample() -> Path:
    return SAMPLE


@pytest.fixture()
def engine() -> Engine:
    eng = Engine(Store(":memory:"), HashEmbedder())
    eng.index(SAMPLE / "policies", [SAMPLE / "past_questionnaires" / "2025_customer_questionnaire.csv"])
    return eng
