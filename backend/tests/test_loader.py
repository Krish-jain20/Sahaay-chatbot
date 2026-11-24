import json
import shutil

import pytest

from app.config import get_settings
from app.data.loader import DataError, load_catalog


def test_real_data_loads(catalog):
    assert "delhi-income-certificate" in catalog.services


@pytest.fixture
def data_copy(tmp_path):
    shutil.copytree(get_settings().data_dir, tmp_path / "data")
    return tmp_path / "data"


def _edit(data_dir, fn):
    path = data_dir / "schemes" / "delhi-income-certificate.json"
    rec = json.loads(path.read_text("utf-8"))
    fn(rec)
    path.write_text(json.dumps(rec), "utf-8")


@pytest.mark.parametrize(
    ("mutate", "msg"),
    [
        (lambda r: r["sources"][0].update(url="https://evil.gov.in.example.com/"), "allowlist"),
        (lambda r: r["sources"][0].update(url="https://delhi.gov.in/"), "allowlist"),
        (lambda r: r["eligibility"]["rules"][0].update(source_ref="s9"), "source_ref"),
        (lambda r: r["eligibility"]["rules"][0].update(field="favourite_colour"), "profile key"),
        (lambda r: r.update(status="verified"), "verified"),
        (lambda r: r.update(prerequisites=["missing-record"]), "prerequisite"),
        (lambda r: r.update(id="other-id"), "filename"),
    ],
)
def test_invalid_records_fail_clearly(data_copy, mutate, msg):
    _edit(data_copy, mutate)
    with pytest.raises(DataError, match=msg):
        load_catalog(data_copy)
