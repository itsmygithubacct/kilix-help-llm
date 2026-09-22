import json
import subprocess
import unittest
from unittest.mock import patch

from help_llm.data import SOURCE, digest, read_json
from help_llm.sizing import recommend


class AdmissionTests(unittest.TestCase):
    def report(self):
        catalog = read_json(SOURCE / "candidates.json")
        return {"schema": "plebian.models.llm-sizing/v1-development", "catalog_sha256": digest(catalog),
                "resource_source": "live", "workload": {"task": "both", "phase": "both", "context": 384,
                    "batch": 1, "lora_rank": 4, "topics": 2, "quant": "f32", "train_backend": "cpu",
                    "infer_backend": "cpu", "co_resident": False, "checkpointing": True, "document_bytes": 10},
                "candidates": [{"id": "qwen3-0.6b", "verdict": "estimated-fit", "profiles": [{"parameters": 750000000}]}]}

    def call(self, report):
        completed = subprocess.CompletedProcess([], 0, json.dumps(report).encode(), b"")
        with patch("help_llm.sizing.subprocess.run", return_value=completed) as run:
            result = recommend({"sha256": "dataset", "data": {"document_bytes": 10}}, 384, 4, "/example/sizer")
        self.assertIn("f32", run.call_args.args[0])
        self.assertNotIn("--resources", run.call_args.args[0])
        return result

    def test_live_cpu_report_can_plan_but_never_qualifies(self):
        result = self.call(self.report())
        self.assertEqual(result["candidate"]["id"], "qwen3-0.6b")
        self.assertFalse(result["qualification_eligible"])

    def test_simulated_mismatched_or_nonfitting_reports_cannot_admit(self):
        for mutation in (lambda r: r.update(resource_source="provided"),
                         lambda r: r.update(catalog_sha256="different"),
                         lambda r: r["workload"].update(quant="q4"),
                         lambda r: r["workload"].update(context=128),
                         lambda r: r["candidates"][0].update(verdict="unknown"),
                         lambda r: r["candidates"][0].update(verdict="does-not-fit")):
            report = self.report()
            mutation(report)
            with self.assertRaises(ValueError):
                self.call(report)
