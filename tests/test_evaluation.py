"""Evaluation boundaries and manual review identity, without model downloads."""
import unittest
from unittest.mock import patch

from help_llm.data import digest
from help_llm.evaluation import (answer_row, explicit_refusal, known_position, retrieval_row,
                                 review_template, reviewed_metrics, rubric_proxy)
from help_llm.runtime import evaluate_v2


class EvaluationTests(unittest.TestCase):
    def test_known_positive_or_unknown_are_distinct(self):
        label = {"source": "a:1", "relevant_sources": ["a:1", "a:2"], "unanswerable": False}
        pool = [{"id": "b:1"}, {"id": "a:2"}, {"id": "a:1"}]
        self.assertEqual(known_position(pool, label), 2)
        self.assertEqual(retrieval_row(pool, label)["known_relevant_mrr"], .5)
        unknown = {**label, "unanswerable": True, "relevant_sources": []}
        self.assertIsNone(retrieval_row(pool, unknown)["known_relevant_at_1"])

    def test_refusal_and_phrase_proxies_do_not_conflate_missing_citation(self):
        self.assertTrue(explicit_refusal("I do not know from the supplied excerpt."))
        self.assertFalse(explicit_refusal("I do not know, but use a secret command."))
        label = {"source": "a:1", "relevant_sources": ["a:1"], "answer": "Run kilix ls.",
                 "unanswerable": False, "rubric": {"must_include": [["kilix ls"]]}}
        draft = {"draft": "Run kilix ls.", "answer": None, "citation_valid": False,
                 "source": {"id": "a:1"}}
        row = answer_row(draft, label)
        self.assertEqual(row["kind"], "uncited-draft")
        self.assertFalse(row["known_source_cited"])
        self.assertTrue(row["rubric_phrase_proxy"])
        self.assertFalse(rubric_proxy("a kilix lsxxx typo", label["rubric"]))
        unknown = {**label, "unanswerable": True, "answer": None, "relevant_sources": []}
        refusal = {"answer": "I do not know from the supplied excerpt.", "draft": None,
                   "citation_valid": False, "source": {"id": "a:1"}}
        self.assertTrue(answer_row(refusal, unknown)["refusal_correct_proxy"])
        self.assertIsNone(answer_row(refusal, unknown)["rubric_phrase_proxy"])

    def test_review_requires_exact_saved_outputs_and_decisions(self):
        report = {"schema": "kilix.help-llm.evaluation/v2", "dataset_sha256": "d" * 64,
                  "examples": [{"id": "q", "bm25_extract": {}, "base": {}, "adapted": {}}]}
        template = review_template(report)
        self.assertEqual(len(template["ratings"]), 3)
        with self.assertRaisesRegex(ValueError, "requires correctness"):
            reviewed_metrics(report, template)
        for row in template["ratings"]:
            row.update(correct=True, supported=True)
        result = reviewed_metrics(report, template)
        self.assertEqual(result["metrics"]["adapted"]["correct"], 1)
        report["examples"][0]["base"]["answer"] = "changed"
        with self.assertRaisesRegex(ValueError, "digest"):
            reviewed_metrics(report, template)

    def test_v2_answer_baseline_keeps_unknowns_separate(self):
        labels = [{"id": "q", "group": "g", "split": "dev", "question": "How?", "answer": "Run A.",
                   "source": "a:1", "relevant_sources": ["a:1", "a:2"], "rubric": {"must_include": [["A"]]},
                   "unanswerable": False},
                  {"id": "u", "group": "u", "split": "dev", "question": "Live state?", "answer": None,
                   "source": "a:1", "relevant_sources": [], "rubric": {}, "unanswerable": True}]
        chunks = [{"id": "a:2", "text": "Run A.", "path": "a.md", "line": 4},
                  {"id": "a:1", "text": "Run B.", "path": "a.md", "line": 2}]
        bundle = {"sha256": "d" * 64, "data": {"schema": "kilix.help-llm.dataset/v2",
                                              "revision": "a" * 40, "examples": labels, "chunks": chunks}}
        with patch("help_llm.runtime.load_dataset", return_value=bundle), \
             patch("help_llm.runtime.retrieve", return_value=chunks):
            result = evaluate_v2("fixture", "dev", "answer", 384)
        self.assertEqual(result["metrics"]["bm25"]["known_relevant_at_1_n"], 1)
        self.assertEqual(result["metrics"]["bm25_extract"]["rubric_phrase_proxy_n"], 1)
        self.assertIsNone(result["examples"][1]["bm25"]["known_relevant_at_1"])


if __name__ == "__main__":
    unittest.main()
