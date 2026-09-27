import json
import subprocess
import sys
import unittest
from pathlib import Path

from help_llm.lookup import Lookup, render, tokens

ROOT = Path(__file__).resolve().parents[1]


class LookupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lookup = Lookup()

    def test_index_is_complete(self):
        self.assertEqual(len(self.lookup.passages), 450)
        for p in self.lookup.passages:
            self.assertTrue(p["text"].strip() and p["path"] and len(p["commit"]) == 40, p["id"])  # docs unchanged since the index was built

    def test_everyday_wording_finds_the_split_keys(self):
        ids = [p["id"] for p in self.lookup.search("how do I split this terminal so I can see two things at once", 3)]
        self.assertIn("kilix:docs/kilix/help/operations/bindings.md#1", ids)

    def test_live_state_question_finds_listing_commands(self):
        text = " ".join(p["text"] for p in self.lookup.search("which of my panes is running htop right now", 3))
        self.assertIn("kilix ls --panes", text)

    def test_nonsense_returns_nothing_and_says_so(self):
        self.assertEqual(self.lookup.search("zzzqqq xxyyzz", 5), [])
        self.assertIn("No matching documentation", render([]))

    def test_stopwords_only_query(self):
        self.assertEqual(tokens("how do I"), [])

    def test_cli_json(self):
        out = subprocess.run([sys.executable, str(ROOT / "kilix-help-llm"), "lookup", "reload kitty config", "-k", "2", "--json"],
                             capture_output=True, text=True, check=True).stdout
        hits = json.loads(out)
        self.assertEqual(len(hits), 2)
        self.assertTrue(all("heading" in h and "path" in h for h in hits))


if __name__ == "__main__":
    unittest.main()
