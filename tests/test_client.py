"""Offline checks; no credentials or network access required."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from decimal import Decimal
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import client


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.factory = patch.object(client, "build_opener")
        self.opener_factory = self.factory.start()
        self.addCleanup(self.factory.stop)
        self.opener = self.opener_factory.return_value

    def response(self, body):
        self.opener.open.return_value = io.BytesIO(body)

    def test_one_request_encodes_parameters_and_preserves_decimal(self):
        self.response(b'{"data":{"value":12345678901234567890.123456789},"quota":{"remaining":19}}')
        result = client.get("/api/v1/search", q="A & B", limit=3)
        self.assertEqual(result["data"]["value"], Decimal("12345678901234567890.123456789"))
        self.opener.open.assert_called_once()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://disclosery.com/api/v1/search?q=A+%26+B&limit=3")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(self.opener.open.call_args.kwargs, {"timeout": 20})
        self.assertIsInstance(self.opener_factory.call_args.args[0], client.NoRedirect)

    def test_bearer_key_is_trimmed_and_origin_normalized(self):
        os.environ.update(DISCLOSERY_API_KEY="  private-test-key  ", DISCLOSERY_ORIGIN="https://example.com/")
        self.response(b'{"data":[],"quota":{}}')
        client.get("/api/v1/search")
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer private-test-key")
        self.assertEqual(request.full_url, "https://example.com/api/v1/search")

    def test_origin_validation_precedes_network(self):
        for origin in ("http://example.com", "https://user:pass@example.com", "https://:pass@example.com", "https://@example.com", "https://example.com/path", "https://example.com?q=1", "https://example.com#fragment", "https://", "https://example.com:invalid", "https://example.com:99999", "https://exam ple.com", "https://example.com\n"):
            with self.subTest(origin=origin):
                os.environ["DISCLOSERY_ORIGIN"] = origin
                with self.assertRaises(ValueError):
                    client.get("/api/v1/search")
        self.opener_factory.assert_not_called()

    def test_path_validation_precedes_network(self):
        for path in ("https://example.com/api/v1/search", "//example.com/api/v1/search", "/api/v2/search", "/api/v1/search?q=1", "/api/v1/search#fragment"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                client.get(path)
        self.opener_factory.assert_not_called()

    def test_redirect_handler_refuses_all_redirects(self):
        handler = client.NoRedirect()
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                self.assertIsNone(handler.redirect_request(None, None, status, "redirect", {}, "https://other.example"))

    def test_error_quota_metadata_and_no_retries_or_secret_output(self):
        os.environ["DISCLOSERY_API_KEY"] = "private-test-key"
        error = HTTPError("https://disclosery.com/api/v1/search", 429, "rate limited", {"Retry-After": "60"}, io.BytesIO(b'{"error":{"code":"quota_exceeded","message":"private-test-key"}}'))
        self.opener.open.side_effect = error
        with self.assertRaises(client.APIError) as caught:
            client.get("/api/v1/search")
        self.assertIn("HTTP 429; code=quota_exceeded; Retry-After=60", str(caught.exception))
        self.assertNotIn("private-test-key", str(caught.exception))
        self.opener.open.assert_called_once()

    def test_malformed_error_bodies_become_api_errors(self):
        bodies = (b"not JSON", b"[]", b"null", b'{"error":null}', b'{"error":[]}', b'{"error":"oops"}')
        for body in bodies:
            with self.subTest(body=body):
                self.opener.open.side_effect = HTTPError("https://disclosery.com/api/v1/search", 500, "error", None, io.BytesIO(body))
                with self.assertRaisesRegex(client.APIError, "HTTP 500; code=unknown; Retry-After=not supplied"):
                    client.get("/api/v1/search")

    def test_network_errors_are_reported_without_retry(self):
        for error in (URLError("offline"), TimeoutError("timeout")):
            with self.subTest(error=error):
                self.opener.open.reset_mock()
                self.opener.open.side_effect = error
                with self.assertRaisesRegex(client.APIError, "Request failed"):
                    client.get("/api/v1/search")
                self.opener.open.assert_called_once()

    def test_invalid_json_becomes_api_error(self):
        for body in (b"not JSON", b"\xff"):
            with self.subTest(body=body):
                self.response(body)
                with self.assertRaisesRegex(client.APIError, "Response was not valid JSON"):
                    client.get("/api/v1/search")

    def test_missing_envelope_fields_are_rejected(self):
        for value in ({"data": []}, {"quota": {}}, [], None):
            with self.subTest(value=value):
                self.response(json.dumps(value).encode())
                with self.assertRaisesRegex(client.APIError, "Unexpected response envelope"):
                    client.get("/api/v1/search")

    def test_display_preserves_precision(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            client.display({"data": {"value": Decimal("0.1234567890123456789")}, "quota": {}})
        self.assertEqual(json.loads(output.getvalue())["data"]["value"], "0.1234567890123456789")


if __name__ == "__main__":
    unittest.main()
