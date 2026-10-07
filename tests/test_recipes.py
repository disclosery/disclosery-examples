"""Run the published recipes offline; network requests are replaced with mocks."""
import contextlib
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "reported_portfolio.ipynb"


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.notebook = json.loads(NOTEBOOK.read_text())
        self.code = ["".join(cell["source"]) for cell in self.notebook["cells"]
                     if cell["cell_type"] == "code"]

    def execute(self, directory=ROOT):
        namespace = {"__name__": "__main__"}
        output = io.StringIO()
        with working_directory(directory), contextlib.redirect_stdout(output), \
                patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Unexpected network request")):
            for index, source in enumerate(self.code):
                exec(compile(source, f"{NOTEBOOK}:cell-{index}", "exec"), namespace)
        return namespace, output.getvalue()

    def test_all_cells_execute_offline_from_repository_root(self):
        namespace, output = self.execute()
        self.assertFalse(namespace["LIVE"])
        self.assertTrue(namespace["data"]["synthetic"])
        self.assertEqual(namespace["weights"], [Decimal(50), Decimal(30), Decimal(20)])
        self.assertIn("reported concentration 100 %", output)
        self.assertIn("SYNTHETIC DATA 2099q1 2099-03-31", output)

    def test_all_cells_execute_from_notebooks_directory(self):
        namespace, output = self.execute(ROOT / "notebooks")
        self.assertEqual(namespace["ROOT"], ROOT)
        self.assertIn("reported concentration 100 %", output)

    def test_committed_outputs_are_empty(self):
        self.assertEqual(self.notebook["nbformat"], 4)
        for cell in self.notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_missing_denominator_is_not_assumed_zero(self):
        data = {"summary": {}, "holdings": [{"value_usd": 10, "pct_portfolio": 50}]}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(self.code[-1], {"data": data, "Decimal": Decimal})
        self.assertIn("concentration is unavailable", output.getvalue())
        self.assertNotIn("reported concentration", output.getvalue())

    def test_missing_ratio_prevents_partial_concentration(self):
        data = {"summary": {"value_total_usd": 100}, "holdings": [
            {"value_usd": 60, "pct_portfolio": 60}, {"value_usd": 40, "pct_portfolio": None}]}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(self.code[-1], {"data": data, "Decimal": Decimal})
        self.assertIn("no combined concentration reported", output.getvalue())


class RecipeTests(unittest.TestCase):
    def run_recipe(self, script, arguments, failure=None):
        client = types.ModuleType("client")
        client.APIError = type("APIError", (Exception,), {})
        client.get = Mock(return_value={"data": {}, "quota": {}})
        client.display = Mock()
        if failure:
            client.get.side_effect = client.APIError(failure)
        output = io.StringIO()
        exit_code = None
        with patch.dict(sys.modules, {"client": client}), \
                patch.object(sys, "argv", [script, *arguments]), \
                contextlib.redirect_stderr(output):
            try:
                runpy.run_path(str(ROOT / "api" / script), run_name="__main__")
            except SystemExit as exc:
                exit_code = exc.code
        return client, exit_code, output.getvalue()

    def test_portfolio_is_one_bounded_request(self):
        client, code, _ = self.run_recipe("portfolio.py", ["1350694", "--quarter", "2025q3", "--limit", "3", "--page", "2"])
        self.assertIsNone(code)
        client.get.assert_called_once_with("/api/v1/funds/1350694/portfolio", view="summary", limit=3, page=2, sort="value", quarter="2025q3")
        client.display.assert_called_once_with(client.get.return_value)

    def test_search_is_one_request(self):
        client, code, _ = self.run_recipe("search_and_filings.py", ["--search", "Bridgewater"])
        self.assertIsNone(code)
        client.get.assert_called_once_with("/api/v1/search", q="Bridgewater", limit=5)

    def test_filings_is_one_request(self):
        client, code, _ = self.run_recipe("search_and_filings.py", ["--cik", "1350694"])
        self.assertIsNone(code)
        client.get.assert_called_once_with("/api/v1/funds/1350694/filings", limit=10)

    def test_invalid_arguments_do_not_make_requests(self):
        cases = [("portfolio.py", args) for args in [
            ["0"], ["-1"], ["1", "--page", "0"], ["1", "--page", "10001"],
            ["1", "--limit", "0"], ["1", "--limit", "101"],
            ["1", "--quarter", "2025q5"], ["1", "--quarter", "2025Q1"]]]
        cases += [("search_and_filings.py", args) for args in [
            [], ["--cik", "0"], ["--cik", "-1"], ["--cik", "1", "--search", "a"]]]
        for script, arguments in cases:
            with self.subTest(script=script, arguments=arguments):
                client, code, _ = self.run_recipe(script, arguments)
                self.assertEqual(code, 2)
                client.get.assert_not_called()

    def test_api_errors_exit_once_without_display_or_retry(self):
        for script, arguments in [("portfolio.py", ["1350694"]), ("search_and_filings.py", ["--search", "Bridgewater"])]:
            with self.subTest(script=script):
                client, code, output = self.run_recipe(script, arguments, "API HTTP 429")
                self.assertEqual(code, 1)
                self.assertIn("API HTTP 429", output)
                client.get.assert_called_once()
                client.display.assert_not_called()


if __name__ == "__main__":
    unittest.main()
