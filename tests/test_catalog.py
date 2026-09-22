"""Check public catalog consistency and the provider delegation boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def test_checkpoint_sizing_is_bound_to_config_and_file_totals(self):
        catalog = json.loads((ROOT / "candidates.json").read_text())
        self.assertEqual(len(catalog["candidates"]), 7)
        for candidate in catalog["candidates"]:
            for key in ("generation_checkpoint", "decision_checkpoint"):
                checkpoint = candidate[key]
                self.assertRegex(checkpoint["revision"], r"^[0-9a-f]{40}$")
                self.assertEqual(checkpoint["checkpoint_bytes"], sum(f["bytes"] for f in checkpoint["checkpoint_files"]))
                self.assertEqual(checkpoint["sizing"]["config_sha256"], checkpoint["config"]["sha256"])
                self.assertEqual(len(checkpoint["sizing"]["layer_types"]), checkpoint["sizing"]["num_hidden_layers"])
                self.assertGreater(checkpoint["sizing"]["parameters"], 0)

    def test_delegates_both_tasks_and_does_not_create_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = Path(directory) / "sizer"
            provider.write_text(f"#!{sys.executable}\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
            provider.chmod(0o700)
            data = Path(directory) / "user-data"
            result = subprocess.run([sys.executable, str(ROOT / "kilix-help-llm"), "size", "--sizer", str(provider),
                                     "--task", "both", "--phase", "both", "--json"],
                                    env={**os.environ, "GPU_TERMINAL_HOME": str(data)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), ["recommend", "help-llm", "--catalog", str(ROOT / "candidates.json"),
                                                        "--task", "both", "--phase", "both", "--json"])
            self.assertFalse(data.exists())

    def test_missing_explicit_provider_never_falls_back_to_an_estimate(self):
        result = subprocess.run([sys.executable, str(ROOT / "kilix-help-llm"), "size", "--sizer", "/nonexistent/sizer"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 69)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
