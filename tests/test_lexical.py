"""Generic retrieval contracts; no production passages or evaluation IDs."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from help_llm.lexical import Analyzer, components, contains_literal, source_roles
from help_llm.lookup import Lookup, STOP


class WordsTest(unittest.TestCase):
    def test_separator_stream_counts_each_component_once(self):
        expected = ["buffer", "size"]
        for text in ("buffer size", "buffer_size", "buffer-size", "buffer.size", "buffer+size", "buffer/size", "bufferSize", "BufferSize"):
            self.assertEqual(components(text), expected)

    def test_regular_inflections_use_attested_bases(self):
        analyzer = Analyzer(["file process directory policy run change automatic prune setting set"], STOP)
        self.assertEqual(analyzer.words("files processes directories policies running changes automatically pruned settings"),
                         ["file", "process", "directory", "policy", "run", "change", "automatic", "prune", "set"])

    def test_ambiguity_and_derivation_do_not_collapse(self):
        analyzer = Analyzer(["ax axe hop hope police policy class status analysis allow disallow use user"], STOP)
        self.assertEqual(analyzer.words("axes hoping police policy class status analysis allow disallow user"),
                         ["axes", "hoping", "police", "policy", "class", "status", "analysis", "allow", "disallow", "user"])
        self.assertEqual(analyzer.words("unattestedly"), ["unattestedly"])

    def test_negation_survives(self):
        analyzer = Analyzer(["can allow delete"], STOP)
        self.assertEqual(analyzer.words("cannot allow"), ["cannot", "allow"])
        self.assertEqual(analyzer.words("can't allow"), ["not", "allow"])
        self.assertEqual(analyzer.words("don't delete"), ["not", "delete"])
        self.assertEqual(analyzer.words("no never without disallow"), ["no", "never", "without", "disallow"])

    def test_literal_boundaries_case_and_negative_flags(self):
        for body in ("change_buffer_size", "buffer_size_limit", "BUFFER_SIZE", "buffer-size"):
            self.assertFalse(contains_literal(body, "buffer_size"))
        self.assertTrue(contains_literal("Set `buffer_size=24`.", "buffer_size"))
        self.assertFalse(contains_literal("--no-cache", "--cache"))
        self.assertFalse(contains_literal("--cached", "--cache"))
        self.assertTrue(contains_literal("use --cache=value", "--cache"))
        self.assertTrue(contains_literal("Use --cache.", "--cache"))

    def test_role_evidence_requires_a_definition_or_concrete_action(self):
        self.assertEqual(source_roles("Settings and shortcuts are configurable."), (False, False))
        self.assertEqual(source_roles("`buffer_size` sets the buffer capacity."), (True, False))
        self.assertEqual(source_roles("BUFFER_LIMIT changes the maximum capacity."), (True, False))
        self.assertEqual(source_roles("The `grow_buffer` action changes its size.\nmap ctrl+b grow_buffer"), (False, True))
        self.assertEqual(source_roles("The action `grow_buffer` changes the capacity."), (False, True))
        self.assertEqual(source_roles("`buffer_size=24`; Ctrl+B grows it."), (True, True))


class RetrievalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index = self.root / "index"
        self.index.mkdir()

    def lookup(self, documents, questions=None):
        sources = []
        for path, text in documents.items():
            full = self.root / path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(text, encoding="utf-8")
            sources.append({"label": "fixture", "path": path, "sha256": hashlib.sha256(full.read_bytes()).hexdigest(), "commit": "a" * 40})
        (self.index / "sources.json").write_text(json.dumps(sources))
        (self.index / "external.jsonl").write_text("")
        (self.index / "questions.json").write_text(json.dumps(questions or {}))
        return Lookup(self.root, self.index)

    def test_natural_compounds_and_inflections_share_scores(self):
        lookup = self.lookup({"docs/buffer.md": "# Buffers\n\nA buffer_size controls buffer capacity; buffers use files. Each file contains data.\n"})
        self.assertEqual(lookup.search("buffer-size"), lookup.search("buffer size"))
        self.assertEqual(lookup.search("file"), lookup.search("files"))

    def test_exact_identifiers_are_source_constraints(self):
        lookup = self.lookup({
            "docs/a.md": "# Capacity\n\n`buffer_size` sets capacity. Use --cache.\n",
            "docs/b.md": "# Capacity\n\nThe change_buffer_size action changes capacity. Use --no-cache.\n"})
        for question in ("buffer_size", "`buffer_size`", "--cache"):
            self.assertEqual([p["path"] for p in lookup.search(question)], ["docs/a.md"])
        for question in ("BUFFER_SIZE", "`buffer-size`", "--cached"):
            self.assertEqual(lookup.search(question), [])

    def test_expansions_cannot_supply_literal_or_role_evidence(self):
        lookup = self.lookup({"docs/a.md": "# Buffer\n\nA general capacity introduction.\n"},
                             {"fixture:docs/a.md#1": ["Which setting changes buffer_size? Which shortcut grows capacity?"]})
        self.assertEqual(lookup.search("buffer_size"), [])
        self.assertEqual(lookup.search("which setting changes capacity"), [])
        self.assertEqual(lookup.search("which shortcut grows capacity"), [])

    def test_configuration_and_shortcut_requests_select_supported_roles(self):
        lookup = self.lookup({
            "docs/config.md": "# Buffer capacity\n\n`buffer_size` sets buffer capacity.\n",
            "docs/keys.md": "# Change the buffer size\n\nThe `grow_buffer` action changes buffer size.\nmap ctrl+b grow_buffer\n"})
        self.assertEqual([p["path"] for p in lookup.search("which setting changes buffer size")], ["docs/config.md"])
        self.assertEqual([p["path"] for p in lookup.search("which shortcut changes buffer size")], ["docs/keys.md"])
        self.assertEqual([p["path"] for p in lookup.search("which action changes buffer size")], ["docs/keys.md"])
        self.assertEqual(lookup.search("which setting and shortcut change buffer size"), [])

    def test_same_passage_can_support_both_roles(self):
        lookup = self.lookup({"docs/both.md": "# Capacity\n\n`buffer_size` sets capacity. Ctrl+B grows it.\n"})
        self.assertEqual(len(lookup.search("which setting and shortcut change capacity")), 1)

    def test_explicit_page_has_priority_over_heading_mentions(self):
        lookup = self.lookup({
            "docs/settings.md": "# Preferences\n\nCtrl+B changes buffer capacity.\n",
            "docs/overview.md": "# Settings\n\nCtrl+B changes buffer capacity; buffer capacity settings.\n"})
        for question in ("In the settings help page, which shortcut changes buffer capacity?", "In settings.md, which shortcut changes buffer capacity?"):
            self.assertEqual([p["path"] for p in lookup.search(question)], ["docs/settings.md"])
        for question in ("In the missing help page, which shortcut changes buffer capacity?", "In missing.md, capacity"):
            self.assertEqual(lookup.search(question), [])

    def test_explicit_page_can_combine_path_and_heading(self):
        lookup = self.lookup({
            "docs/operations/listing.md": "# Listing panes\n\nThis pane operation displays the process_names field, which contains names.\n",
            "docs/overview.md": "# Overview\n\nThe process_names field contains names.\n"})
        hits = lookup.search("In the pane-listing operation guide, which field contains names?")
        self.assertEqual([p["path"] for p in hits], ["docs/operations/listing.md"])

    def test_unrelated_near_matches_are_not_substrings(self):
        lookup = self.lookup({"docs/a.md": "# Policy\n\nA policy governs a carpet and a cargo shipment.\n"})
        for question in ("police", "car", "unrelatedword", "`policies`"):
            self.assertEqual(lookup.search(question), [])


if __name__ == "__main__":
    unittest.main()
