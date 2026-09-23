"""Real local backprop and adapter reload; no network or upstream weights."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from help_llm.runtime import attach, encoded, chat_encoded, examples, file_digest, generated, load_run, loss_for, optimize, query, group_backward, require_legacy_evaluation, selection_labels

AVAILABLE = all(importlib.util.find_spec(name) for name in ("torch", "transformers", "peft"))


class QueryIdentityTests(unittest.TestCase):
    def test_run_rejects_incomplete_or_corrupt_artifacts_before_sizing(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'runs/fixture'
            (directory / 'adapter').mkdir(parents=True)
            names = ('plan.json', 'adapter/adapter_config.json',
                     'adapter/adapter_model.safetensors', 'head.safetensors')
            for name in names:
                (directory / name).write_text('fixture')
            artifacts = {name: file_digest(directory / name) for name in names}
            cases = [({}, 'incomplete'),
                     ({k: v for k, v in artifacts.items() if k != 'head.safetensors'}, 'incomplete'),
                     ({**artifacts, 'head.safetensors': '0' * 64}, 'integrity'),
                     ({**artifacts, '../outside': '0' * 64}, 'integrity')]
            for entries, error in cases:
                (directory / 'run.json').write_text(json.dumps({'task': 'rank', 'dataset': 'fixture',
                    'dataset_sha256': 'd', 'artifacts': entries}))
                with patch('help_llm.runtime.configure'), patch('help_llm.runtime.state_root', return_value=root), \
                        patch('help_llm.runtime.load_dataset', return_value={'sha256': 'd'}), \
                        patch('help_llm.runtime.recommend') as sizing, patch('help_llm.runtime.load_base') as base:
                    with self.assertRaisesRegex(ValueError, error):
                        load_run('fixture', 'rank')
                    sizing.assert_not_called()
                    base.assert_not_called()

    def test_combined_query_releases_ranker_and_uses_its_selected_evidence(self):
        import weakref
        class Resource:
            pass
        shared = {"dataset": "fixture", "dataset_sha256": "d", "context": 384}
        answer_report, rank_report = {**shared, "task": "answer"}, {**shared, "task": "rank"}
        data = {"revision": "r"}
        chunk = {"id": "a:2", "text": "Run B.", "path": "a.md", "line": 2, "relevance_score": .5}
        references, events = [], []
        def load(name, task, sizer):
            events.append(task)
            if task == "rank":
                model, tokenizer, head = Resource(), Resource(), Resource()
                references.extend(weakref.ref(x) for x in (model, tokenizer, head))
                return rank_report, data, model, tokenizer, head
            self.assertTrue(all(ref() is None for ref in references))
            return answer_report, data, Resource(), Resource(), None
        def rank(*args):
            self.assertEqual(events, ["rank"])
            return [chunk]
        def generate(model, tokenizer, question, evidence, *args):
            self.assertEqual(evidence, chunk)
            return {"answer": "Run B. [a:2]", "source": evidence}
        with patch("help_llm.runtime.read_json", side_effect=[answer_report, rank_report]), \
                patch("help_llm.runtime.load_run", new=load), patch("help_llm.runtime.ranked", new=rank), \
                patch("help_llm.runtime.generated", new=generate), \
                patch("help_llm.runtime.retrieve", side_effect=AssertionError("must use ranked evidence")):
            result = query("answer", "answer", "How?", rank_name="rank")
        self.assertEqual(events, ["rank", "answer"])
        self.assertEqual(result["ranking"]["order"], ["a:2"])
        self.assertFalse(result["ranking"]["calibrated"])
        self.assertFalse(result["qualification_eligible"])

    def test_combined_query_rejects_mismatched_runs_before_loading(self):
        common = {"dataset": "fixture", "dataset_sha256": "d", "context": 384}
        answer = {**common, "task": "answer"}
        for key, value in (("dataset", "other"), ("dataset_sha256", "e"), ("context", 512), ("task", "answer")):
            rank = {**common, "task": "rank", key: value}
            with patch("help_llm.runtime.read_json", side_effect=[answer, rank]), \
                    patch("help_llm.runtime.load_run") as load:
                with self.assertRaisesRegex(ValueError, "identical"):
                    query("answer", "answer", "How?", rank_name="rank")
                load.assert_not_called()

    def test_combined_query_rejects_manifest_changes_during_admission(self):
        common = {"dataset": "fixture", "dataset_sha256": "d", "context": 384}
        answer, rank = {**common, "task": "answer"}, {**common, "task": "rank"}
        chunk = {"id": "a:1", "relevance_score": .5}
        for changed_task in ("rank", "answer"):
            def load(name, task, sizer):
                report = dict(rank if task == "rank" else answer)
                if task == changed_task:
                    report["dataset_sha256"] = "changed"
                return report, {}, None, None, None
            with self.subTest(task=changed_task), \
                    patch("help_llm.runtime.read_json", side_effect=[answer, rank]), \
                    patch("help_llm.runtime.load_run", new=load), \
                    patch("help_llm.runtime.ranked", return_value=[chunk]), \
                    patch("help_llm.runtime.generated") as generate:
                with self.assertRaisesRegex(ValueError, "changed during admission"):
                    query("answer", "answer", "How?", rank_name="rank")
                generate.assert_not_called()

    def test_unknown_exposure_changes_only_explicit_training_unknowns(self):
        labels = [{"split": split, "source": "a:1", "question": question,
                   "answer": None if unknown else "Run A.", "unanswerable": unknown,
                   "negatives": ["a:2"]}
                  for split in ("train", "dev") for question, unknown in (("known", False), ("live", True))]
        data = {"chunks": [{"id": "a:1", "text": "Run A."}, {"id": "a:2", "text": "Run B."}],
                "examples": labels}
        with patch("help_llm.runtime.chat_encoded", side_effect=lambda tokenizer, prompt, target, context: {"prompt": prompt, "target": target}):
            normal = examples(data, None, "answer", 384, "train", 4)
            repeated = examples(data, None, "answer", 384, "train", 4, 3)
            dev = examples(data, None, "answer", 384, "dev", 4)
        self.assertEqual(repeated, normal[:2] + [normal[2]] * 3)
        self.assertEqual(dev, normal)
        with self.assertRaisesRegex(ValueError, "only available"):
            examples(data, None, "answer", 384, "dev", 4, 3)
        with self.assertRaisesRegex(ValueError, "only available"):
            examples(data, None, "rank", 384, "train", 4, 3)
        for invalid in (0, 17, True, 1.5):
            with self.assertRaisesRegex(ValueError, "integer"):
                examples(data, None, "answer", 384, "train", 4, invalid)

    def test_answer_negative_stride_keeps_every_positive_and_unknown(self):
        chunks = [{"id": "a:1", "text": "Run A."}, {"id": "a:2", "text": "Run B."}]
        labels = [{"split": "train", "source": "a:1", "question": str(i), "answer": "Run A.",
                   "negatives": ["a:2"], "unanswerable": False} for i in range(8)]
        labels.append({"split": "train", "source": "a:1", "question": "unknown", "answer": None,
                       "negatives": ["a:2"], "unanswerable": True})
        with patch("help_llm.runtime.chat_encoded", side_effect=lambda *a: {"input_ids": [1], "labels": [1]}):
            rows = examples({"chunks": chunks, "examples": labels}, None, "answer", 384, "train", 4)
        self.assertEqual(len(rows), 11)  # Eight known, two negatives, one unknown.

    def test_development_selection_covers_fact_and_unknown_groups_per_document(self):
        labels = [{"split": "dev", "document": doc, "group": f"{doc}-{fact}",
                   "unanswerable": fact == 9} for doc in ("a", "b", "c") for fact in range(10)]
        selected = selection_labels({"examples": labels})
        self.assertEqual(len(selected), 12)
        self.assertEqual(sum(row["unanswerable"] for row in selected), 3)

    def test_legacy_metrics_refuse_new_label_semantics(self):
        require_legacy_evaluation({"schema": "kilix.help-llm.dataset/v1"})
        with self.assertRaisesRegex(ValueError, "v2 evaluation is pending"):
            require_legacy_evaluation({"schema": "kilix.help-llm.dataset/v2"})

    def test_chat_template_masks_prefix_and_retains_turn_terminator(self):
        class Tokenizer:
            def apply_chat_template(self, messages, **options):
                self.options = options
                return [10, 11, 12] if options["add_generation_prompt"] else [10, 11, 12, 20, 99]
        tokenizer = Tokenizer()
        row = chat_encoded(tokenizer, "Question?", "Answer", 8)
        self.assertEqual(row["labels"], [-100, -100, -100, 20, 99])
        self.assertFalse(tokenizer.options["enable_thinking"])
        self.assertFalse(tokenizer.options["return_dict"])
        self.assertEqual(chat_encoded(tokenizer, "Question?", context=8)["input_ids"], row["input_ids"][:3])
        with self.assertRaisesRegex(ValueError, "exceeds"):
            chat_encoded(tokenizer, "Question?", "Answer", 4)

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

    def test_selection_restores_the_best_measured_step(self):
        from transformers import Qwen3Model
        model, head = attach(Qwen3Model(self.config), 2, "rank")
        rows = [{"input_ids": [1, 2, 3], "target": 1}, {"input_ids": [4, 5, 6], "target": 0}]
        selection = {"history": []}
        losses = optimize(model, head, rows, 12, .01, dev_rows=rows, eval_every=4,
                          patience=2, selection=selection)
        measured = [r["loss"] for r in selection["history"]]
        self.assertEqual(selection["selected_dev_loss"], min(measured))
        model.eval()
        import torch
        with torch.no_grad():
            restored = sum(float(loss_for(model, head, r)) for r in rows) / 2
        self.assertAlmostEqual(restored, selection["selected_dev_loss"], places=5)
        self.assertLessEqual(len(losses), 12)

    def test_quality_proxy_takes_precedence_over_teacher_forced_loss(self):
        from transformers import Qwen3Model
        model, head = attach(Qwen3Model(self.config), 2, "rank")
        rows = [{"input_ids": [1, 2, 3], "target": 1}, {"input_ids": [4, 5, 6], "target": 0}]
        scores = iter((2, 1, 3))
        selection = {"history": []}
        optimize(model, head, rows, 6, .01, dev_rows=rows, eval_every=2,
                 patience=3, selection=selection, quality=lambda _: next(scores))
        self.assertEqual(selection["selected_quality_proxy_count"], 3)
        self.assertEqual(selection["selected_step"], 6)

    def test_listwise_replay_matches_full_graph_gradient_and_learns_none(self):
        import torch
        from transformers import Qwen3Model
        model, head = attach(Qwen3Model(self.config), 2, "rank")
        torch.nn.init.normal_(head.weight, std=.02)
        row = {"candidates": [{"input_ids": [1, 2, 3]}, {"input_ids": [4, 5, 6]},
                              {"input_ids": [7, 8, 9]}], "positive_indices": [0, 2]}
        params = [p for p in model.parameters() if p.requires_grad] + list(head.parameters())
        expected_loss = loss_for(model, head, row)
        expected_loss.backward()
        gradients = [p.grad.clone() for p in params]
        for p in params:
            p.grad = None
        replay_loss = group_backward(model, head, row)
        self.assertAlmostEqual(float(replay_loss), float(expected_loss.detach()), places=6)
        for param, expected in zip(params, gradients):
            self.assertTrue(torch.allclose(param.grad, expected, atol=2e-6))
        row["positive_indices"] = []
        losses = optimize(model, head, [row], 24, .01)
        self.assertLess(losses[-1], losses[0] / 2)

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
