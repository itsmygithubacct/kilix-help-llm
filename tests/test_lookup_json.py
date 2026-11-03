"""CLI bytes stay stable when an optional prepared cache is absent."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from help_llm import cli, prepared
from help_llm.lookup import Lookup


class LookupJsonTests(unittest.TestCase):
    def test_cache_and_memory_build_emit_identical_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            index = root / "index"
            index.mkdir()
            document = "# Quartz\n\nThe quartz display shows café notes.\n"
            (root / "guide.md").write_text(document, encoding="utf-8")
            (index / "sources.json").write_text(json.dumps([{
                "label": "manual", "path": "guide.md", "commit": "a" * 40,
                "sha256": hashlib.sha256(document.encode()).hexdigest(),
            }]))
            (index / "external.jsonl").write_text("")
            (index / "questions.json").write_text("{}")
            prepared.prepare(root, index)
            cached = Lookup(root, index)
            self.assertTrue(cached.prepared_cache_hit)
            (index / prepared.FILENAME).unlink()
            fresh = Lookup(root, index)
            self.assertFalse(fresh.prepared_cache_hit)
            expected = fresh.search("quartz", 5)
            self.assertTrue(expected)
            outputs = []
            for lookup in (cached, fresh):
                stdout = io.StringIO()
                with patch("help_llm.lookup.Lookup", return_value=lookup), \
                        contextlib.redirect_stdout(stdout):
                    self.assertEqual(cli.main(["lookup", "quartz", "--json"]), 0)
                outputs.append(stdout.getvalue())
                self.assertEqual(json.loads(outputs[-1]), expected)
                self.assertIn("café", outputs[-1])
            self.assertEqual(outputs[0], outputs[1])
            self.assertFalse((index / prepared.FILENAME).exists())
