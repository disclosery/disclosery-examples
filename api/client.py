"""Small dependency-free Disclosery JSON client; Python 3.10+."""
import json
import os
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class APIError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A bearer token must not follow a redirect to another origin.
        return None


def get(path, **params):
    """One request, no automatic retries. Returns the complete quota/data envelope."""
    origin = os.environ.get("DISCLOSERY_ORIGIN", "https://disclosery.com").rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.query or parsed.fragment or parsed.path:
        raise ValueError("DISCLOSERY_ORIGIN must be an HTTPS origin, without a path or credentials")
    if not path.startswith("/api/v1/") or "?" in path or "#" in path:
        raise ValueError("Expected a relative /api/v1/ path")
    headers = {"Accept": "application/json", "User-Agent": "disclosery-examples/1.0"}
    key = os.environ.get("DISCLOSERY_API_KEY", "").strip()
    if key:
        headers["Authorization"] = "Bearer " + key
    request = Request(origin + path + ("?" + urlencode(params) if params else ""), headers=headers)
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            result = json.load(response, parse_float=Decimal)
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read(65536)).get("error", {})
        except (ValueError, AttributeError):
            detail = {}
        retry = exc.headers.get("Retry-After", "not supplied")
        raise APIError(f"HTTP {exc.code}; code={detail.get('code', 'unknown')}; Retry-After={retry}. See the API contract.") from None
    except (URLError, TimeoutError) as exc:
        raise APIError("Request failed; check connectivity and service availability.") from exc
    if not isinstance(result, dict) or "data" not in result or "quota" not in result:
        raise APIError("Unexpected response envelope")
    return result


def display(envelope):
    """Readable output: Decimal values become strings to avoid floating-point loss."""
    print(json.dumps(envelope, indent=2, default=str))
