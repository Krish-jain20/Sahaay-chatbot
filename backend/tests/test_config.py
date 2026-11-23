import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize("url", ["hrnzqzuhfzvcfywugbnv", "http://x.supabase.co", "https://nodot"])
def test_bad_supabase_url_gives_clear_error(url):
    with pytest.raises(ValidationError, match="full project URL"):
        Settings(supabase_url=url, _env_file=None)


def test_good_and_empty_supabase_url():
    assert (
        Settings(supabase_url="https://abc.supabase.co/", _env_file=None).supabase_url
        == "https://abc.supabase.co"
    )
    assert Settings(supabase_url="", _env_file=None).supabase_url == ""
