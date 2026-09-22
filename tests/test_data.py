import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from help_llm.data import digest, load_dataset, prepare, private_dir, retrieve


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / "docs"
        self.repo.mkdir()
        self.state = root / "state"
        env = patch.dict(os.environ, {"GPU_TERMINAL_HOME": str(self.state)})
        env.start()
        self.addCleanup(env.stop)
        self.manifest, self.labels = [], []
        for split, word in zip(("train", "dev", "calibration", "test"), ("red", "blue", "green", "orange")):
            (self.repo / (word + ".md")).write_text(f"# {word}\n\nThe {word} control starts {word} mode.\n\nOnly {word} mode uses this control.\n")
            self.manifest.append({"id": word, "path": word + ".md", "split": split})
            self.labels.append({"id": word, "document": word, "question": f"How do I start {word} mode?",
                                "answer": f"The {word} control starts {word} mode."})
        self.git("init", "-q", "-b", "main")
        self.revision = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git("add", ".")
        self.git("-c", "user.name=itsmygithubacct", "-c", "user.email=itsmygithubacct@users.noreply.github.com",
                 "commit", "-qm", "Add synthetic documents")
        return self.git("rev-parse", "HEAD")

    def prepare(self, name="fixture"):
        return prepare(self.repo, self.revision, self.manifest, self.labels, name)

    def test_import_reads_committed_bytes_and_preserves_split_provenance(self):
        (self.repo / "red.md").write_text("uncommitted content must never be imported")
        bundle = self.prepare()
        data = bundle["data"]
        self.assertEqual(bundle["sha256"], digest(data))
        self.assertEqual(data["revision"], self.revision)
        self.assertEqual(retrieve(data, "start red mode", 1)[0]["document"], "red")
        for row in data["examples"]:
            chunk = next(c for c in data["chunks"] if c["id"] == row["source"])
            self.assertEqual(row["split"], chunk["split"])
            self.assertIn(row["answer"], chunk["text"])
        target = self.state / "kilix-help-llm/datasets/fixture.json"
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_tampered_bundle_is_rejected(self):
        self.prepare()
        path = self.state / "kilix-help-llm/datasets/fixture.json"
        bundle = json.loads(path.read_text())
        bundle["data"]["examples"][0]["split"] = "test"
        path.write_text(json.dumps(bundle))
        with self.assertRaisesRegex(ValueError, "integrity"):
            load_dataset("fixture")

    def test_bad_source_and_invented_answer_rejected_before_writing(self):
        self.labels[0]["answer"] = "Unsupported advice"
        with self.assertRaisesRegex(ValueError, "verbatim"):
            self.prepare()
        self.assertFalse(self.state.exists())
        self.manifest[0]["path"] = "../outside.md"
        with self.assertRaisesRegex(ValueError, "relative"):
            self.prepare()

    def test_symlink_git_blob_and_user_directory_refused(self):
        (self.repo / "red.md").unlink()
        (self.repo / "red.md").symlink_to("blue.md")
        self.revision = self.commit()
        with self.assertRaisesRegex(ValueError, "regular tracked"):
            self.prepare()
        self.state.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            private_dir(self.state / "kilix-help-llm")

    def test_duplicate_questions_and_cross_split_paragraphs_refused(self):
        self.labels[1]["question"] = self.labels[0]["question"].upper()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.prepare()
        with (self.repo / "blue.md").open("a") as file:
            file.write("\nThe red control starts red mode.\n")
        self.revision = self.commit()
        with self.assertRaisesRegex(ValueError, "paragraphs cross"):
            self.prepare()

    def test_dataset_name_cannot_escape_private_root(self):
        with self.assertRaises(ValueError):
            self.prepare("../../escape")
