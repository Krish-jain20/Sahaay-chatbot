import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.data.loader import load_catalog
from app.main import app


@pytest.fixture(scope="session")
def catalog():
    return load_catalog(get_settings().data_dir)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
