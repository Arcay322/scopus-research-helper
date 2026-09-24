import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import scopus_search


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ScopusSearchTests(unittest.TestCase):
    def test_search_doi_sends_key_in_header_and_returns_entries(self):
        payload = {"search-results": {"entry": [{"dc:title": "Test article"}]}}
        requests = []

        def fake_open(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(payload)

        entries = scopus_search.search_doi("10.1145/3695988", "test-key", fake_open)

        self.assertEqual(entries, [{"dc:title": "Test article"}])
        request, timeout = requests[0]
        self.assertIn("query=DOI%28%2210.1145%2F3695988%22%29", request.full_url)
        self.assertNotIn("test-key", request.full_url)
        self.assertEqual(request.get_header("X-els-apikey"), "test-key")
        self.assertEqual(timeout, 15)

    def test_rejects_invalid_doi_before_network_call(self):
        def fake_open(*_args, **_kwargs):
            self.fail("Network request must not happen")

        with self.assertRaises(ValueError):
            scopus_search.search_doi('10.1234/abc") OR ALL(x)', "test-key", fake_open)

    def test_unauthorized_error_does_not_reveal_key(self):
        def fake_open(*_args, **_kwargs):
            raise HTTPError("https://api.elsevier.com/", 401, "Unauthorized", {}, io.BytesIO(b""))

        with self.assertRaises(scopus_search.ScopusError) as raised:
            scopus_search.search_doi("10.1145/3695988", "test-key", fake_open)
        self.assertIn("401", str(raised.exception))
        self.assertNotIn("test-key", str(raised.exception))

    def test_missing_key_prompts_without_echo(self):
        with patch.dict("scopus_search.os.environ", {}, clear=True):
            with patch("scopus_search.getpass", return_value="test-key") as ask:
                self.assertEqual(scopus_search.get_api_key(), "test-key")
        ask.assert_called_once()


if __name__ == "__main__":
    unittest.main()
