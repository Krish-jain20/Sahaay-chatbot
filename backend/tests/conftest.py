import os

os.environ["GEMINI_API_KEY"] = ""  # tests stay offline (stub LLM)
    ""  # tests never call the live model; run the live smoke test with the key set explicitly
)

import pytest
from fastapi.testclient import TestClient

import app.api.chat as chat_api
from app.config import get_settings
from app.data.loader import load_catalog
from app.main import app

chat_api.TOKEN_DELAY_S = 0


@pytest.fixture(scope="session")
def catalog():
    return load_catalog(get_settings().data_dir)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
