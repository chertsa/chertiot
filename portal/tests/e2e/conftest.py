"""e2e fixtures. Public URLs (http://app.localhost etc.) don't resolve on macOS outside a browser,
so requests connect to DEV_CONNECT_HOST (127.0.0.1) while sending the real Host header."""

import os
from http.cookiejar import Cookie, DefaultCookiePolicy
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest

CONNECT_HOST = os.environ.get("DEV_CONNECT_HOST", "127.0.0.1")


class HostRewriteTransport(httpx.HTTPTransport):
    """Send Host: <original>, but open the TCP connection to CONNECT_HOST:80."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        original = request.url
        is_local = original.host == "localhost" or original.host.endswith(".localhost")
        if not (original.scheme == "http" and is_local):
            return super().handle_request(request)
        # Build a separate request for the wire so the client's cookie jar still keys on the
        # original host (cookies from auth.localhost must be sent back to auth.localhost).
        request.read()
        headers = request.headers.copy()
        headers["Host"] = original.netloc.decode()
        wire = httpx.Request(
            request.method,
            original.copy_with(host=CONNECT_HOST, port=80),
            headers=headers,
            content=request.content,
        )
        response = super().handle_request(wire)
        response.request = request
        return response


def _return_ok_secure_localhost(self: DefaultCookiePolicy, cookie: Cookie, request: Any) -> bool:
    """Browsers treat http://*.localhost as a secure context and send `Secure` cookies there;
    Python's cookie jar does not. Mirror the browser so dev-over-http flows work (Keycloak marks
    its auth-session cookies Secure). httpx rebuilds the jar per request, so this must be patched
    on the policy class, not on one jar instance. Test process only."""
    host = str(request.host)
    if host == "localhost" or host.endswith(".localhost"):
        return True
    return bool(_orig_return_ok_secure(self, cookie, request))


_orig_return_ok_secure = DefaultCookiePolicy.return_ok_secure
DefaultCookiePolicy.return_ok_secure = _return_ok_secure_localhost  # type: ignore[method-assign]


def make_client(**kw: object) -> httpx.Client:
    return httpx.Client(transport=HostRewriteTransport(), timeout=30, **kw)  # type: ignore[arg-type]


def _reachable(url: str) -> bool:
    try:
        with make_client(follow_redirects=True) as c:
            return c.get(url).status_code < 500
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session")
def tb_url() -> str:
    url = os.environ.get("TB_PUBLIC_URL", "http://app.localhost")
    if not _reachable(f"{url}/login"):
        pytest.skip(f"ThingsBoard not reachable at {url} (run `make dev`)")
    return url


@pytest.fixture(scope="session")
def kc_url() -> str:
    url = os.environ.get("KC_HOSTNAME", "http://auth.localhost")
    if not _reachable(f"{url}/realms/{os.environ.get('KC_REALM', 'chertiot')}"):
        pytest.skip(f"Keycloak not reachable at {url} (run `make dev` + `make bootstrap`)")
    assert urlparse(url).scheme == "http", "dev e2e expects plain http"
    return url
