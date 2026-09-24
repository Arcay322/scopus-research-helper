import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
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

    def test_search_query_encodes_topic_and_requests_multiple_results(self):
        payload = {"search-results": {"entry": [{"dc:title": "A"}, {"dc:title": "B"}]}}
        requests = []

        def fake_open(request, timeout):
            requests.append(request)
            return FakeResponse(payload)

        entries = scopus_search.search_query(
            'TITLE-ABS-KEY("large language models" AND software)',
            "test-key",
            count=10,
            start=20,
            open_url=fake_open,
        )
        self.assertEqual(len(entries), 2)
        self.assertIn("start=20", requests[0].full_url)
        self.assertIn("count=10", requests[0].full_url)
        self.assertNotIn("test-key", requests[0].full_url)

    def test_export_csv_escapes_spreadsheet_formulas(self):
        entries = [{"dc:title": "=1+1", "prism:doi": "10.1234/test"}]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "results.csv"
            scopus_search.export_csv(entries, output)
            saved = output.read_text(encoding="utf-8-sig")
            self.assertIn("'=1+1", saved)
            with self.assertRaises(FileExistsError):
                scopus_search.export_csv(entries, output)

    def test_unauthorized_error_does_not_reveal_key(self):
        def fake_open(*_args, **_kwargs):
            raise HTTPError("https://api.elsevier.com/", 401, "Unauthorized", {}, io.BytesIO(b""))

        with self.assertRaises(scopus_search.ScopusError) as raised:
            scopus_search.search_doi("10.1145/3695988", "test-key", fake_open)
        self.assertIn("401", str(raised.exception))
        self.assertNotIn("test-key", str(raised.exception))

    def test_missing_key_prompts_without_echo(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(scopus_search, "KEY_FILE", Path(temporary) / "absent"):
                with patch.dict("scopus_search.os.environ", {}, clear=True):
                    with patch("scopus_search.getpass", return_value="test-key") as ask:
                        self.assertEqual(scopus_search.get_api_key(), "test-key")
        ask.assert_called_once()

    def test_stored_key_is_private_and_available_without_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            key_file = Path(temporary) / "private" / "scopus_api_key"
            scopus_search.store_api_key("test-key", key_file)
            self.assertEqual(os.stat(key_file).st_mode & 0o777, 0o600)
            with patch.object(scopus_search, "KEY_FILE", key_file):
                with patch.dict("scopus_search.os.environ", {}, clear=True):
                    with patch("scopus_search.getpass") as ask:
                        self.assertEqual(scopus_search.get_api_key(), "test-key")
                        ask.assert_not_called()

    def test_store_key_refuses_to_replace_existing_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            key_file = Path(temporary) / "scopus_api_key"
            scopus_search.store_api_key("first-key", key_file)
            with self.assertRaises(scopus_search.ScopusError):
                scopus_search.store_api_key("second-key", key_file)
            self.assertEqual(key_file.read_text(), "first-key\n")

    def test_topic_cli_paginates_and_exports_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "articles.csv"
            first_page = [{"dc:title": f"Article {n}"} for n in range(25)]
            last_page = [{"dc:title": f"Article {n}"} for n in range(25, 30)]
            with patch("sys.argv", ["scopus_search.py", "--query", "TITLE-ABS-KEY(software)", "--limit", "30", "--csv", str(output)]):
                with patch("scopus_search.get_api_key", return_value="test-key"):
                    with patch("scopus_search.search_query", side_effect=[first_page, last_page]) as search:
                        with redirect_stdout(io.StringIO()):
                            scopus_search.main()
            self.assertEqual(search.call_count, 2)
            self.assertEqual(search.call_args_list[0].kwargs, {"count": 25, "start": 0})
            self.assertEqual(search.call_args_list[1].kwargs, {"count": 5, "start": 25})
            self.assertEqual(len(output.read_text(encoding="utf-8-sig").splitlines()), 31)


if __name__ == "__main__":
    unittest.main()
