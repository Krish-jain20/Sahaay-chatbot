from urllib.parse import urlparse

from app.data.models import Allowlist


def is_allowed(url: str, allowlist: Allowlist) -> bool:
    """Exact host match only. A .gov.in suffix alone is not proof."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return any(d.host.lower() == host for d in allowlist.domains)
