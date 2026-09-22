"""Real local backprop and adapter reload; no network or upstream weights."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from help_llm.runtime import attach, encoded, generated, loss_for, optimize, query

AVAILABLE = all(importlib.util.find_spec(name) for name in ("torch", "transformers", "peft"))


class QueryIdentityTests(unittest.TestCase):
    def test_answer_exposes_exact_corpus_identity_without_claiming_qualification(self):
        report = {"dataset_sha256": "d" * 64, "context": 384}
        data = {"revision": "a" * 40}
        with patch("help_llm.runtime.load_run", return_value=(report, data, None, None, None)), \
             patch("help_llm.runtime.retrieve", return_value=[{}]), \
             patch("help_llm.runtime.generated", return_value={"answer": "Text [example:1]"}):
            result = query("fixture", "answer", "Question?")
        self.assertEqual(result["source_revision"], data["revision"])
        self.assertEqual(result["dataset_sha256"], report["dataset_sha256"])
        self.assertFalse(result["qualification_eligible"])
        self.assertEqual(result["quality"], "unqualified")


@unittest.skipUnless(AVAILABLE, "run make check-runtime with the optional CPU environment")
class TrainingTests(unittest.TestCase):
    def setUp(self):
        import torch
        from transformers import Qwen3Config
        torch.set_num_threads(2)
        torch.manual_seed(17)
        self.config = Qwen3Config(vocab_size=32, hidden_size=16, intermediate_size=32, num_hidden_layers=1,
                                 num_attention_heads=2, num_key_value_heads=1, head_dim=8,
                                 max_position_embeddings=128, tie_word_embeddings=True)

    def test_answer_backprop_learns_without_changing_frozen_weights_and_reloads(self):
        import torch
        from transformers import Qwen3ForCausalLM
        from peft import PeftModel
        base = Qwen3ForCausalLM(self.config)
        original = {k: v.clone() for k, v in base.state_dict().items()}
        model, head = attach(base, 2, "answer")
        frozen = {n: p.clone() for n, p in model.named_parameters() if not p.requires_grad}
        row = {"input_ids": [1, 2, 3, 4, 5], "labels": [-100, -100, 3, 4, 5]}
        losses = optimize(model, head, [row], 24, .01)
        self.assertLess(losses[-1], losses[0])
        for n, p in model.named_parameters():
            if n in frozen:
                self.assertTrue(torch.equal(p, frozen[n]), n)
        model.eval()
        with tempfile.TemporaryDirectory() as directory:
            model.save_pretrained(directory, safe_serialization=True)
            self.assertTrue((Path(directory) / "adapter_model.safetensors").is_file())
            restored = Qwen3ForCausalLM(self.config)
            restored.load_state_dict(original)
            loaded = PeftModel.from_pretrained(restored, directory, local_files_only=True).eval()
            with torch.no_grad():
                self.assertTrue(torch.allclose(model(input_ids=torch.tensor([row["input_ids"]])).logits,
                                               loaded(input_ids=torch.tensor([row["input_ids"]])).logits, atol=1e-6))

    def test_rank_head_learns_two_distinct_relevance_labels(self):
        from transformers import Qwen3Model
        model, head = attach(Qwen3Model(self.config), 2, "rank")
        rows = [{"input_ids": [1, 2, 3], "target": 1}, {"input_ids": [4, 5, 6], "target": 0}]
        losses = optimize(model, head, rows, 32, .01)
        self.assertLess(sum(losses[-4:]), sum(losses[:4]))
        model.eval()
        for row in rows:
            self.assertLess(float(loss_for(model, head, row).detach()), .2)

    def test_prompt_is_masked_and_overflow_never_silently_truncates(self):
        class Tokenizer:
            eos_token_id = 0
            def encode(self, text, **kwargs):
                return list(range(1, len(text) + 1))
        row = encoded(Tokenizer(), "abc", "de", 6)
        self.assertEqual(row["labels"], [-100, -100, -100, 1, 2, 0])
        with self.assertRaisesRegex(ValueError, "exceeds"):
            encoded(Tokenizer(), "abc", "de", 5)

    def test_missing_or_unknown_citations_are_drafts_and_output_stays_in_context(self):
        import torch
        class Tokenizer:
            eos_token_id = 0
            answer = ""
            def encode(self, text, **kwargs):
                return [1, 2, 3]
            def decode(self, ids, **kwargs):
                return self.answer
        class Model:
            def generate(self, input_ids, **kwargs):
                self.limit = kwargs["max_new_tokens"]
                return torch.cat((input_ids, torch.tensor([[4]])), dim=1)
        model, tokenizer = Model(), Tokenizer()
        chunk = {"id": "example:1", "text": "A synthetic excerpt.", "path": "example.md", "line": 3}
        for answer in ("No citation", "Invented citation [missing:2]"):
            tokenizer.answer = answer
            result = generated(model, tokenizer, "Question?", chunk, 4, 96)
            self.assertIsNone(result["answer"])
            self.assertTrue(result["abstained"])
            self.assertEqual(result["draft"], answer)
            self.assertEqual(model.limit, 1)
        tokenizer.answer = "A claim [example:1]"
        result = generated(model, tokenizer, "Question?", chunk, 4, 96)
        self.assertTrue(result["citation_valid"])
        self.assertEqual(result["factual_support"], "not-automatically-verified")
