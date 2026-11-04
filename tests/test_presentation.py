import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from help_llm import cli
from help_llm.presentation import SCHEMA, present, source_identity, source_key, validate_registry


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.source = {"id": "panes:1", "path": "help/panes.md", "line": 4,
                       "text": "Run kilix ls --panes to list panes."}
        self.url = "https://example.org/help/panes#listing"
        self.registry = {"schema": SCHEMA, "sources": {source_key(self.source): {
            "source": source_identity(self.source), "links": [{"title": "Panes and tabs", "url": self.url}]}}}
        self.output = {"answer": "Run `kilix ls --panes`. Lists pane numbers and programs. [panes:1]",
                       "draft": None, "source": self.source, "citation_valid": True, "explicit_refusal": False}

    def test_command_explanation_and_clickable_reference(self):
        result = present(self.output, self.registry)
        self.assertEqual(result["command"], "kilix ls --panes")
        self.assertEqual(result["explanation"], "Lists pane numbers and programs.")
        self.assertEqual(result["markdown"], "```sh\nkilix ls --panes\n```\n\nLists pane numbers and programs.\n\nRelated help: [Panes and tabs](<" + self.url + ">)")
        self.assertIn('href="' + self.url + '"', result["html"])
        self.assertNotIn("panes:1", result["markdown"])

    def test_withheld_draft_never_becomes_an_answer(self):
        self.output.update(answer=None, draft=self.output["answer"])
        result = present(self.output, self.registry)
        self.assertEqual(result["status"], "withheld")
        self.assertNotIn("kilix ls", result["markdown"])
        self.assertFalse(result["help"])

    def test_refusal_does_not_cite_unrelated_evidence(self):
        self.output.update(answer="I do not know from the supplied excerpt.", explicit_refusal=True)
        result = present(self.output, self.registry)
        self.assertEqual(result["status"], "refusal")
        self.assertFalse(result["help"])
        self.assertEqual(result["markdown"], self.output["answer"])

    def test_source_changes_and_unknown_ids_fail_closed(self):
        for field, value in [("text", "Changed facts"), ("path", "different.md"), ("line", 8), ("id", "other:1")]:
            output = copy.deepcopy(self.output)
            output["source"][field] = value
            self.assertEqual(present(output, self.registry)["status"], "withheld")
        self.output["answer"] += " [invented:2]"
        self.assertEqual(present(self.output, self.registry)["reason"], "citation-mismatch")

    def test_registry_rejects_active_schemes_and_credentials(self):
        for bad in ["javascript:alert(1)", "file:///etc/passwd", "http://example.org/help", "https://name:pass@example.org/help", "https://example.org/help\n"]:
            reg = copy.deepcopy(self.registry)
            next(iter(reg["sources"].values()))["links"][0]["url"] = bad
            with self.assertRaises(ValueError): validate_registry(reg)

    def test_html_is_escaped_and_commands_are_not_executed(self):
        self.output["answer"] = 'Run `echo "<script>"`. Shows <script>alert(1)</script>. [panes:1]'
        shown = present(self.output, self.registry)
        self.assertNotIn("<script>", shown["html"])
        self.assertIn("&lt;script&gt;", shown["html"])
        self.assertEqual(shown["command"], 'echo "<script>"')

    def test_registry_rejects_raw_url_controls_before_rendering(self):
        for code in [*range(32), *range(127, 160)]:
            for url in ["https://example.org/help/" + chr(code) + "suffix",
                        chr(code) + "https://example.org/help"]:
                with self.subTest(code=code, url=url):
                    reg = copy.deepcopy(self.registry)
                    next(iter(reg["sources"].values()))["links"][0]["url"] = url
                    with self.assertRaises(ValueError): validate_registry(reg)
                    with self.assertRaises(ValueError): present(self.output, reg)

    def test_valid_https_links_preserve_identity_and_escaping(self):
        for url in ["https://example.org/help?q=panes&lang=fr#listing",
                    "https://example.org/a%20b/%1B/%00",
                    "https://example.org/café", "https://example.org:8443/help"]:
            with self.subTest(url=url):
                reg = copy.deepcopy(self.registry)
                next(iter(reg["sources"].values()))["links"][0]["url"] = url
                before = copy.deepcopy((self.output, reg))
                result = present(self.output, reg)
                self.assertEqual(result["status"], "answer")
                self.assertEqual(result["help"][0]["url"], url)
                self.assertIn("](<" + url + ">)", result["markdown"])
                self.assertIn(url.replace("&", "&amp;"), result["html"])
                self.assertIn(url, result["text"])
                self.assertEqual((self.output, reg), before)

    def test_formatting_never_supplies_a_missing_command(self):
        self.output["answer"] = "Lists pane numbers and programs. [panes:1]"
        result = present(self.output, self.registry)
        self.assertIsNone(result["command"])
        self.assertNotIn("kilix ls", result["markdown"])

    def test_fenced_command_and_explanation_keep_the_same_content(self):
        self.output["answer"] = "```sh\nkilix ls --panes\n```\n\nLists panes. [panes:1]"
        result = present(self.output, self.registry)
        self.assertEqual(result["command"], "kilix ls --panes")
        self.assertEqual(result["explanation"], "Lists panes.")

    def test_generated_url_is_not_a_clickable_help_link(self):
        self.output["answer"] = "See https://example.net/unreviewed [panes:1]"
        result = present(self.output, self.registry)
        self.assertIn("`https://example.net/unreviewed`", result["markdown"])
        self.assertEqual(result["html"].count("href="), 1)
        self.assertEqual([x["url"] for x in result["help"]], [self.url])

    def test_source_wrappers_do_not_leave_presentation_debris(self):
        for answer in ["Answer: Run `kilix ls --panes`. Lists panes. [Source [panes:1]]",
                       "The source ID is [panes:1], and the answer is: Run `kilix ls --panes`. Lists panes.",
                       "Run `kilix ls --panes`. Lists panes.\nSource [panes:1]"]:
            self.output["answer"] = answer
            result = present(self.output, self.registry)
            self.assertEqual(result["command"], "kilix ls --panes")
            self.assertEqual(result["explanation"], "Lists panes.")

    def test_citation_only_boilerplate_is_not_a_useful_answer(self):
        for answer in ["The source ID is [panes:1].", "[Source [panes:1]]", "Source [panes:1]"]:
            self.output["answer"] = answer
            self.assertEqual(present(self.output, self.registry)["reason"], "empty-answer")

    def test_tui_and_duplicate_citations_preserve_instructions(self):
        self.output["answer"] = "Press `?` to see the keys. [panes:1] [panes:1]"
        result = present(self.output, self.registry)
        self.assertEqual(result["body"], "Press `?` to see the keys.")
        self.assertEqual(len(result["help"]), 1)

    def test_saved_output_cli_and_live_query_use_same_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"links.json").write_text(json.dumps(self.registry))
            (root/"answer.json").write_text(json.dumps({"output": self.output}))
            args = ["--help-links", str(root/"links.json"), "--format", "markdown"]
            saved, live = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(saved):
                self.assertEqual(cli.main(["format-answer", "--input", str(root/"answer.json"), *args]), 0)
            with patch("help_llm.cli.runtime_python"), patch("help_llm.runtime.query", return_value=copy.deepcopy(self.output)), contextlib.redirect_stdout(live):
                self.assertEqual(cli.main(["ask", "--run", "example", *args, "List panes"]), 0)
            self.assertEqual(saved.getvalue(), live.getvalue())

    def test_format_request_is_checked_before_loading_model(self):
        with patch("help_llm.cli.runtime_python") as runtime, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["ask", "--run", "example", "--format", "html", "List panes"]), 2)
        runtime.assert_not_called()


if __name__ == "__main__": unittest.main()
