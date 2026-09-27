import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from help_llm.lookup import INDEX, MAX_WORDS, Lookup, load_passages, render, tokens

ROOT = Path(__file__).resolve().parents[1]
# A single paragraph longer than MAX_WORDS stays whole so passage ids match the question index.
OVERSIZED = {"kilix:docs/kilix/README.md#14", "kilix:docs/kilix/README.md#21", "kilix:docs/kilix/README.md#50",
             "kitty:docs/kitty/README.md#2", "pleb:README.md#20", "plebian-os:README.md#4", "plebian-os:README.md#6",
             "plebian-os:releases/0.2.0-notes.md#2"}


class IndexSnapshotTest(unittest.TestCase):
    """The checked-in index agrees with itself; independent of later documentation edits."""

    def test_sources_and_questions_resolve(self):
        sources = json.loads((INDEX / "sources.json").read_text())
        external = [json.loads(l) for l in (INDEX / "external.jsonl").read_text().splitlines() if l.strip()]
        questions = json.loads((INDEX / "questions.json").read_text())
        self.assertTrue(sources and external and questions)
        for source in sources:
            self.assertEqual(len(source["commit"]), 40)
            self.assertEqual(len(source["sha256"]), 64)
        for p in external:
            self.assertTrue(p["text"].strip() and p["path"] and len(p["commit"]) == 40, p["id"])
        if all(hashlib.sha256((ROOT / s["path"]).read_bytes()).hexdigest() == s["sha256"] for s in sources):
            ids = {p["id"] for p in load_passages()[0]}
            self.assertEqual(len(ids), 450)
            self.assertLessEqual(set(questions), ids)

    def test_passage_length_bound_or_known_exception(self):
        over = {p["id"] for p in load_passages()[0] if len(p["text"].split()) > MAX_WORDS}
        self.assertLessEqual(over, OVERSIZED)   # only the documented single-paragraph exceptions exceed the bound


class ChangedDocumentTest(unittest.TestCase):
    def test_changed_file_is_searched_without_its_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, index = Path(tmp), Path(tmp) / "index"
            (root / "docs").mkdir(); index.mkdir()
            same = b"# Same\n\nThe widget frobnicator lives here.\n"
            (root / "docs/same.md").write_bytes(same)
            (root / "docs/changed.md").write_bytes(b"# Changed\n\nuniquechangedword.\n")
            (index / "sources.json").write_text(json.dumps([
                {"label": "t", "path": "docs/same.md", "commit": "a" * 40, "sha256": hashlib.sha256(same).hexdigest()},
                {"label": "t", "path": "docs/changed.md", "commit": "b" * 40, "sha256": "0" * 64}]))
            (index / "external.jsonl").write_text("")
            (index / "questions.json").write_text(json.dumps({
                "t:docs/same.md#1": ["zebra tooling question"], "t:docs/changed.md#1": ["giraffe tooling question"]}))
            lookup = Lookup(root=root, index=index)
            self.assertEqual(lookup.search("zebra", 1)[0]["id"], "t:docs/same.md#1")      # expansion on unchanged file
            self.assertEqual(lookup.search("giraffe", 5), [])                               # none on changed file
            hit = lookup.search("uniquechangedword", 1)[0]
            self.assertEqual((hit["id"], hit["commit"]), ("t:docs/changed.md#1", ""))       # current text searchable


class SearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lookup = Lookup()

    def test_everyday_wording_finds_the_split_keys(self):
        text = " ".join(p["text"] for p in self.lookup.search("how do I split this terminal so I can see two things at once", 5))
        self.assertIn("Ctrl+Alt+R", text)

    def test_live_state_question_finds_listing_commands(self):
        text = " ".join(p["text"] for p in self.lookup.search("which of my panes is running htop right now", 3))
        self.assertIn("kilix ls --panes", text)

    def test_nonsense_and_punctuation_return_nothing(self):
        for q in ("zzzqqq xxyyzz", ".", "---", "how do I"):
            self.assertEqual(self.lookup.search(q, 5), [], q)
        self.assertIn("No matching documentation", render([]))

    def test_tokenizer_strips_edge_punctuation(self):
        self.assertEqual(tokens("config config. (--hold) kitty.conf"), ["config", "config", "--hold", "kitty.conf"])

    def test_cli_json_and_no_resource_warnings(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            Lookup()
        out = subprocess.run([sys.executable, "-W", "error::ResourceWarning", str(ROOT / "kilix-help-llm"), "lookup",
                              "reload kitty config", "-k", "2", "--json"], capture_output=True, text=True, check=True).stdout
        hits = json.loads(out)
        self.assertEqual(len(hits), 2)
        self.assertTrue(all("heading" in h and "path" in h for h in hits))


if __name__ == "__main__":
    unittest.main()
