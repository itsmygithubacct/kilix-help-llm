"""Optional CPU LoRA runtime. Imports stay outside the stdlib-only CLI path."""
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import re
import resource
import sys
import time

from .data import (SOURCE, answer_prompt, digest, identifier, load_dataset,
                   private_dir, rank_prompt, read_json, retrieve, state_root, write_json)
from .sizing import recommend
from .evaluation import answer_row, explicit_refusal, retrieval_row, summarize


def configure():
    os.umask(0o077)
    root = private_dir(state_root())
    for variable, suffix in {"HF_HOME": "huggingface", "TORCH_HOME": "torch",
                             "XDG_CACHE_HOME": "xdg"}.items():
        os.environ[variable] = str(private_dir(root / "cache" / suffix))
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "4"
    import torch
    torch.set_num_threads(4)
    return torch


def checkpoint_path(checkpoint):
    return state_root() / "models" / checkpoint["model_id"].replace("/", "--") / checkpoint["revision"]


def file_digest(path):
    import hashlib
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(part)
    return result.hexdigest()


def verify_checkpoint(checkpoint):
    path = checkpoint_path(checkpoint)
    identity = read_json(path / "kilix-checkpoint.json")
    if identity["model_id"] != checkpoint["model_id"] or identity["revision"] != checkpoint["revision"]:
        raise ValueError("checkpoint identity mismatch")
    for name, expected in identity["files"].items():
        target = path / name
        if not target.resolve().is_relative_to(path.resolve()) or target.is_symlink() or file_digest(target) != expected:
            raise ValueError("checkpoint file integrity check failed")
    expected = {"config.json": checkpoint["config"]["sha256"],
                **{f["path"]: f["sha256"] for f in checkpoint["checkpoint_files"]}}
    if any(identity["files"].get(k) != v for k, v in expected.items()):
        raise ValueError("checkpoint disagrees with the pinned catalog")
    return path


def fetch(plan):
    configure()
    from huggingface_hub import snapshot_download
    outputs = []
    for task in (["answer", "rank"] if plan["task"] == "both" else [plan["task"]]):
        checkpoint = plan["candidate"]["generation_checkpoint" if task == "answer" else "decision_checkpoint"]
        path = checkpoint_path(checkpoint)
        if (path / "kilix-checkpoint.json").exists():
            outputs.append(str(verify_checkpoint(checkpoint)))
            continue
        private_dir(path)
        snapshot_download(checkpoint["model_id"], revision=checkpoint["revision"], local_dir=path,
                          allow_patterns=["*.json", "*.model", "*.txt", "*.jinja", "README.md", "LICENSE*",
                                          *[f["path"] for f in checkpoint["checkpoint_files"]]], max_workers=2,
                          token=False)
        files = {str(p.relative_to(path)): file_digest(p) for p in path.rglob("*")
                 if p.is_file() and ".cache" not in p.relative_to(path).parts}
        expected = {"config.json": checkpoint["config"]["sha256"],
                    **{f["path"]: f["sha256"] for f in checkpoint["checkpoint_files"]}}
        if any(files.get(k) != v for k, v in expected.items()):
            raise ValueError("downloaded checkpoint does not match catalog hashes")
        write_json(path / "kilix-checkpoint.json", {"model_id": checkpoint["model_id"],
                                                    "revision": checkpoint["revision"], "files": files})
        outputs.append(str(path))
    return outputs


def load_base(checkpoint, task):
    from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
    import torch
    path = verify_checkpoint(checkpoint)
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    factory = AutoModelForCausalLM if task == "answer" else AutoModel
    model = factory.from_pretrained(path, local_files_only=True, trust_remote_code=False,
                                    dtype=torch.float32, attn_implementation="eager")
    return model, tokenizer


def attach(model, rank, task):
    from peft import LoraConfig, get_peft_model
    import torch
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=rank, lora_alpha=rank * 2, lora_dropout=0.0,
                                           target_modules="all-linear", bias="none",
                                           task_type="CAUSAL_LM" if task == "answer" else "FEATURE_EXTRACTION"))
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    head = torch.nn.Linear(model.config.hidden_size, 2) if task == "rank" else None
    if head is not None:
        head.normalize_features = True
        torch.nn.init.zeros_(head.weight)
        torch.nn.init.zeros_(head.bias)
    return model, head


ABSTENTION = "I do not know from the supplied excerpt."


def encoded(tokenizer, prompt, answer=None, context=384):
    """Never truncate evidence or targets silently. Mask only the prompt."""
    ids = tokenizer.encode(prompt, add_special_tokens=True)
    labels = [-100] * len(ids)
    if answer is not None:
        target = tokenizer.encode(answer, add_special_tokens=False)
        if tokenizer.eos_token_id is not None:
            target.append(tokenizer.eos_token_id)
        ids += target
        labels += target
    if not ids or len(ids) > context:
        raise ValueError("example exceeds planned context; shorten the excerpt/label or increase --context")
    return {"input_ids": ids, "labels": labels}


def chat_encoded(tokenizer, prompt, answer=None, context=384):
    """Use the checkpoint's native non-thinking chat format and assistant boundary."""
    messages = [{"role": "user", "content": prompt}]
    options = dict(tokenize=True, return_dict=False, enable_thinking=False)
    prefix = tokenizer.apply_chat_template(messages, add_generation_prompt=True, **options)
    ids = prefix
    if answer is not None:
        ids = tokenizer.apply_chat_template(messages + [{"role": "assistant", "content": answer}],
                                            add_generation_prompt=False, **options)
        if ids[:len(prefix)] != prefix or len(ids) <= len(prefix):
            raise ValueError("chat template training/inference assistant prefixes differ")
    if not ids or len(ids) > context:
        raise ValueError("chat example exceeds planned context; shorten evidence or increase --context")
    return {"input_ids": ids, "labels": [-100] * len(prefix) + ids[len(prefix):]}


def examples(data, tokenizer, task, context, split):
    chunks = {c["id"]: c for c in data["chunks"]}
    rows = []
    for label in data["examples"]:
        if label["split"] != split:
            continue
        chunk = chunks[label["source"]]
        if task == "answer":
            target = ABSTENTION if label.get("unanswerable") else f"{label['answer']} [{chunk['id']}]"
            rows.append(chat_encoded(tokenizer, answer_prompt(label["question"], chunk), target, context))
            if not label.get("unanswerable") and label.get("negatives"):
                negative = chunks[label["negatives"][0]]
                rows.append(chat_encoded(tokenizer, answer_prompt(label["question"], negative), ABSTENTION, context))
        elif "negatives" in label and label["negatives"]:
            relevant = label.get("relevant_sources", [] if label.get("unanswerable") else [chunk["id"]])
            keys = list(dict.fromkeys([chunk["id"], *relevant, *label["negatives"]]))
            rows.append({"candidates": [encoded(tokenizer, rank_prompt(label["question"], chunks[k]),
                                               context=context) for k in keys],
                         "positive_indices": [i for i, k in enumerate(keys) if k in relevant]})
        else:
            if label.get("unanswerable"):
                raise ValueError("unanswerable ranking labels require reviewed negatives")
            rows.append({**encoded(tokenizer, rank_prompt(label["question"], chunk), context=context), "target": 1})
            negatives = [c for c in retrieve(data, label["question"], len(chunks), split)
                         if c["document"] != label["document"]][:1]
            if not negatives:
                negatives = [c for c in retrieve(data, label["question"], len(chunks), split)
                             if c["id"] != label["source"] and label["answer"] not in c["text"]][:1]
            if not negatives:
                raise ValueError("ranking requires a negative paragraph in every split")
            rows.append({**encoded(tokenizer, rank_prompt(label["question"], negatives[0]), context=context), "target": 0})
    return rows


def rank_logits(model, head, row):
    import torch
    ids = torch.tensor([row["input_ids"]], dtype=torch.long)
    features = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False).last_hidden_state[:, -1].float()
    if getattr(head, "normalize_features", False):
        features = torch.nn.functional.layer_norm(features, (features.shape[-1],))
    return head(features)


def group_loss(scores, positive_indices):
    """Marginal likelihood of any reviewed positive, or the fixed none score."""
    import torch
    values = torch.cat((scores, scores.new_zeros(1)))
    positive_indices = positive_indices or [len(scores)]
    return torch.logsumexp(values, 0) - torch.logsumexp(values[positive_indices], 0)


def group_backward(model, head, row):
    """Exact listwise gradient by replay, keeping only one candidate graph alive."""
    import torch
    if any(isinstance(m, torch.nn.Dropout) and m.p for m in model.modules()):
        raise ValueError("gradient replay requires deterministic forwards (dropout disabled)")
    if getattr(model.config, "attention_dropout", 0):
        raise ValueError("gradient replay requires attention dropout disabled")
    with torch.no_grad():
        scores = torch.stack([(lambda x: x[0, 1] - x[0, 0])(rank_logits(model, head, c))
                              for c in row["candidates"]])
    scores.requires_grad_()
    loss = group_loss(scores, row["positive_indices"])
    weights, = torch.autograd.grad(loss, scores)
    for candidate, weight in zip(row["candidates"], weights):
        logits = rank_logits(model, head, candidate)
        ((logits[0, 1] - logits[0, 0]) * weight.detach()).backward()
    return loss.detach()


def loss_for(model, head, row):
    import torch
    if "candidates" in row:
        scores = torch.stack([(lambda x: x[0, 1] - x[0, 0])(rank_logits(model, head, c))
                              for c in row["candidates"]])
        return group_loss(scores, row["positive_indices"])
    ids = torch.tensor([row["input_ids"]], dtype=torch.long)
    if head is None:
        return model(input_ids=ids, attention_mask=torch.ones_like(ids),
                     labels=torch.tensor([row["labels"]]), use_cache=False).loss
    return torch.nn.functional.cross_entropy(rank_logits(model, head, row), torch.tensor([row["target"]]))


def selection_labels(data):
    """Predeclared small dev set: three facts and one unknown per document."""
    chosen, counts, unknown = [], {}, set()
    for label in data["examples"]:
        if label["split"] != "dev":
            continue
        document = label["document"]
        if label.get("unanswerable"):
            if document not in unknown:
                chosen.append(label)
                unknown.add(document)
        elif label["group"] not in counts.setdefault(document, []):
            if len(counts[document]) < 3:
                counts[document].append(label["group"])
                chosen.append(label)
    return chosen


def optimize(model, head, rows, steps, learning_rate, seed=17, progress=None,
             dev_rows=None, eval_every=16, patience=3, selection=None):
    import torch
    rng = random.Random(seed)
    params = [p for p in model.parameters() if p.requires_grad]
    if head is not None:
        params.extend(head.parameters())
    optimizer = torch.optim.AdamW(params, lr=learning_rate)
    model.train()
    if head is not None:
        head.train()
    order, losses = list(range(len(rows))), []
    best_weights, best_loss, stale = None, float("inf"), 0
    if dev_rows is not None and (not dev_rows or eval_every < 1 or patience < 1):
        raise ValueError("checkpoint selection needs dev rows, positive interval and patience")
    for step in range(steps):
        if step % len(rows) == 0:
            rng.shuffle(order)
        optimizer.zero_grad(set_to_none=True)
        row = rows[order[step % len(rows)]]
        loss = group_backward(model, head, row) if "candidates" in row else loss_for(model, head, row)
        if not torch.isfinite(loss):
            raise ValueError("non-finite training loss")
        if "candidates" not in row:
            loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
        optimizer.step()
        losses.append(float(loss.detach()))
        if progress is not None:
            progress(step + 1, losses[-1])
        if dev_rows is not None and ((step + 1) % eval_every == 0 or step + 1 == steps):
            model.eval()
            if head is not None:
                head.eval()
            with torch.no_grad():
                dev_loss = sum(float(loss_for(model, head, item)) for item in dev_rows) / len(dev_rows)
            if not math.isfinite(dev_loss):
                raise ValueError("non-finite development loss")
            improved = dev_loss < best_loss - 1e-4
            selection["history"].append({"step": step + 1, "loss": dev_loss, "improved": improved})
            if improved:
                best_loss, stale = dev_loss, 0
                best_weights = [p.detach().clone() for p in params]
                selection.update(selected_step=step + 1, selected_dev_loss=dev_loss)
            else:
                stale += 1
            if progress is not None:
                progress(step + 1, losses[-1], dev_loss)
            model.train()
            if head is not None:
                head.train()
            if stale >= patience:
                break
    if best_weights is not None:
        with torch.no_grad():
            for parameter, value in zip(params, best_weights):
                parameter.copy_(value)
    return losses


def train(dataset, name, task, context, rank, steps, learning_rate, sizer=None, candidate=None,
          eval_every=16, patience=3):
    if not 1 <= steps <= 10000 or not 0 < learning_rate <= .01 or not 1 <= eval_every <= 10000 or not 1 <= patience <= 100:
        raise ValueError("steps must be 1-10000 and learning rate must be in (0, .01]")
    torch = configure()
    bundle = load_dataset(dataset)
    plan = recommend(bundle, context, rank, sizer, candidate, task)
    checkpoint = plan["candidate"]["generation_checkpoint" if task == "answer" else "decision_checkpoint"]
    directory = private_dir(state_root() / "runs") / identifier(name)
    directory.mkdir(mode=0o700)  # Never overwrite a previous run, including failed ones.
    write_json(directory / "plan.json", plan)
    started = time.monotonic()
    code_sha256 = digest({str(p.relative_to(SOURCE)): file_digest(p)
                          for p in sorted((SOURCE / "help_llm").glob("*.py"))})
    torch.manual_seed(17)
    try:
        model, tokenizer = load_base(checkpoint, task)
        model, head = attach(model, rank, task)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if head is not None:
            trainable += sum(p.numel() for p in head.parameters())
        sized = next(p for c in plan["sizing"]["candidates"] if c["id"] == plan["candidate"]["id"]
                     for p in c["profiles"] if p["phase"] == "train" and p["task"] == task)
        if trainable > sized["trainable_parameters"]:
            raise ValueError("actual adapter/head parameter count exceeds the shared sizing recipe")
        rows = examples(bundle["data"], tokenizer, task, context, "train")
        dev = examples(bundle["data"], tokenizer, task, context, "dev")
        selection = None
        selected_dev = None
        if bundle["data"].get("schema") == "kilix.help-llm.dataset/v2":
            chosen = selection_labels(bundle["data"])
            selected_dev = examples({**bundle["data"], "examples": chosen}, tokenizer, task, context, "dev")
            selection = {"criterion": "mean teacher-forced dev loss", "groups": [r["group"] for r in chosen],
                         "eval_every": eval_every, "patience": patience, "history": []}
        def progress(step, loss, dev_loss=None):
            if step % 4 == 0 or step == steps or dev_loss is not None:
                print(json.dumps({"step": step, "steps": steps, "loss": loss,
                                  "selection_dev_loss": dev_loss}), file=sys.stderr, flush=True)
        losses = optimize(model, head, rows, steps, learning_rate, progress=progress,
                          dev_rows=selected_dev, eval_every=eval_every, patience=patience,
                          selection=selection)
        model.eval()
        with torch.no_grad():
            dev_loss = sum(float(loss_for(model, head, row)) for row in dev) / len(dev)
        model.save_pretrained(directory / "adapter", safe_serialization=True)
        if head is not None:
            from safetensors.torch import save_file
            save_file(head.state_dict(), str(directory / "head.safetensors"))
        artifacts = {str(p.relative_to(directory)): file_digest(p) for p in directory.rglob("*") if p.is_file()}
        report = {"schema": "kilix.help-llm.run/v1", "dataset": dataset, "dataset_sha256": bundle["sha256"],
                  "checkpoint": checkpoint, "task": task, "context": context, "lora_rank": rank,
                  "steps": steps, "actual_steps": len(losses), "learning_rate": learning_rate, "seed": 17, "losses": losses,
                  "dev_loss": dev_loss, "training_examples": len(rows), "dev_examples": len(dev),
                  "selection": selection,
                  "elapsed_seconds": time.monotonic() - started,
                  "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                  "runtime": {k: importlib.metadata.version(k) for k in
                              ("torch", "transformers", "peft", "safetensors", "accelerate")},
                  "code_sha256": code_sha256, "trainable_parameters": trainable,
                  "answer_format": "chat-nonthinking-v2",
                  "rank_recipe": ("normalized-listwise-replay-v2" if task == "rank" and all("candidates" in r for r in rows)
                                  else "normalized-binary-v2" if task == "rank" else None),
                  "artifacts": artifacts, "quality": "unmeasured", "qualification_eligible": False}
        write_json(directory / "run.json", report)
        return {"run": name, "task": task, "steps": len(losses), "selected_step": selection.get("selected_step") if selection else None,
                "dev_loss": dev_loss,
                "elapsed_seconds": report["elapsed_seconds"], "quality": "unmeasured"}
    except Exception as error:
        write_json(directory / "failure.json", {"error_type": type(error).__name__, "complete": False})
        raise


def load_run(name, task, sizer=None):
    configure()
    directory = state_root() / "runs" / identifier(name)
    report = read_json(directory / "run.json")
    if report["task"] != task:
        raise ValueError("run task does not match this command")
    bundle = load_dataset(report["dataset"])
    if report["dataset_sha256"] != bundle["sha256"]:
        raise ValueError("run and dataset do not match")
    for name, expected in report["artifacts"].items():
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()) or file_digest(path) != expected:
            raise ValueError("run artifact integrity check failed")
    plan = read_json(directory / "plan.json")
    current = recommend(bundle, report["context"], report["lora_rank"], sizer, plan["candidate"]["id"], task)
    checkpoint_key = "generation_checkpoint" if task == "answer" else "decision_checkpoint"
    adapter_config = read_json(directory / "adapter/adapter_config.json")
    if report["checkpoint"] != current["candidate"][checkpoint_key] or adapter_config["r"] != report["lora_rank"]:
        raise ValueError("run checkpoint/adapter differs from the sized recipe")
    base, tokenizer = load_base(report["checkpoint"], task)
    from peft import PeftModel
    model = PeftModel.from_pretrained(base, directory / "adapter", local_files_only=True, is_trainable=False)
    model.eval()
    head = None
    if task == "rank":
        import torch
        from safetensors.torch import load_file
        head = torch.nn.Linear(model.config.hidden_size, 2)
        head.normalize_features = report.get("rank_recipe") in {"normalized-listwise-replay-v2", "normalized-binary-v2"}
        head.load_state_dict(load_file(str(directory / "head.safetensors")))
        head.eval()
    return report, bundle["data"], model, tokenizer, head


def ranked(data, model, tokenizer, head, question, context, limit=5):
    import torch
    pool = retrieve(data, question, limit)
    with torch.no_grad():
        for chunk in pool:
            row = encoded(tokenizer, rank_prompt(question, chunk), context=context)
            logits = rank_logits(model, head, row)
            chunk["relevance_score"] = (float(logits[0, 1] - logits[0, 0]) if getattr(head, "normalize_features", False)
                                        else float(logits.softmax(-1)[0, 1]))
    return sorted(pool, key=lambda c: (-c["relevance_score"], c["id"]))


def generated(model, tokenizer, question, chunk, context, max_new_tokens, answer_format="plain-v1"):
    import torch
    encoder = chat_encoded if answer_format == "chat-nonthinking-v2" else encoded
    row = encoder(tokenizer, answer_prompt(question, chunk), context=context)
    remaining = context - len(row["input_ids"])
    if remaining < 1:
        raise ValueError("no planned context remains for generation")
    ids = torch.tensor([row["input_ids"]])
    with torch.no_grad():
        output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                                max_new_tokens=min(max_new_tokens, remaining), do_sample=False,
                                use_cache=True, pad_token_id=tokenizer.eos_token_id)
    answer = tokenizer.decode(output[0, ids.shape[1]:], skip_special_tokens=True).strip()
    citations = re.findall(r"\[([^\[\]\n]+)\]", answer)
    valid = bool(citations) and all(c == chunk["id"] for c in citations)
    refusal = explicit_refusal(answer)
    accepted = valid or refusal
    return {"answer": answer if accepted else None, "draft": answer if not accepted else None,
            "citation_valid": valid, "explicit_refusal": refusal, "abstained": refusal or not valid,
            "source": {k: chunk[k] for k in ("id", "path", "line", "text")},
            "factual_support": "not-automatically-verified"}


def query(name, task, question, sizer=None, limit=5, max_new_tokens=96):
    if not question.strip() or len(question) > 2000 or not 1 <= limit <= 20 or not 1 <= max_new_tokens <= 256:
        raise ValueError("invalid query limits")
    report, data, model, tokenizer, head = load_run(name, task, sizer)
    identity = {"dataset_sha256": report["dataset_sha256"], "source_revision": data["revision"],
                "quality": "unqualified", "qualification_eligible": False}
    if task == "rank":
        results = ranked(data, model, tokenizer, head, question, report["context"], limit)
        topics = {}
        for row in results:
            topics.setdefault(row["document"], {"document": row["document"], "source": row["id"],
                                                "relevance_score": row["relevance_score"]})
        return {**identity, "results": results, "topics": list(topics.values()),
                "calibrated": False, "qualification_eligible": False}
    chunk = retrieve(data, question, 1)[0]
    return {**identity, **generated(model, tokenizer, question, chunk, report["context"], max_new_tokens,
                                   report.get("answer_format", "plain-v1"))}


def require_legacy_evaluation(data):
    if data.get("schema") == "kilix.help-llm.dataset/v2":
        raise ValueError("v2 evaluation is pending support for multiple relevant sources and unanswerable labels; "
                         "legacy metrics must not be used for this dataset")


def _evaluation_progress(index, total):
    if index % 5 == 0 or index == total:
        print(json.dumps({"evaluated": index, "total": total}), file=sys.stderr, flush=True)


def evaluate_v2(dataset, split, task, context, model=None, tokenizer=None, head=None,
                run=None, candidate=None, answer_format="chat-nonthinking-v2", progress=None):
    """Use one BM25 pool for each comparison; score only reviewed source IDs."""
    if split not in {"dev", "calibration", "test"}:
        raise ValueError("v2 evaluation is reserved for held-out splits")
    bundle = load_dataset(dataset)
    data = bundle["data"]
    if data.get("schema") != "kilix.help-llm.dataset/v2":
        raise ValueError("this evaluator requires reviewed dataset v2")
    labels = [r for r in data["examples"] if r["split"] == split]
    rows = []
    for index, label in enumerate(labels, 1):
        pool = retrieve(data, label["question"], 5)
        row = {"id": label["id"], "group": label["group"], "question": label["question"],
               "unanswerable": label["unanswerable"], "reference_source": label["source"],
               "reviewed_relevant_sources": label["relevant_sources"],
               "reference_answer": label["answer"], "rubric": label["rubric"],
               "bm25": retrieval_row(pool, label), "pool": [c["id"] for c in pool]}
        if task == "rank":
            if model is None or tokenizer is None or head is None:
                raise ValueError("ranking evaluation needs the trained model and head")
            scored = ranked(data, model, tokenizer, head, label["question"], context)
            row["ranked"] = retrieval_row(scored, label)
            row["ranked"].update(order=[c["id"] for c in scored],
                                 scores=[c["relevance_score"] for c in scored],
                                 none_predicted=scored[0]["relevance_score"] <= 0,
                                 none_correct_proxy=(scored[0]["relevance_score"] <= 0) == label["unanswerable"])
        else:
            chunk = pool[0]
            # Whole-paragraph extraction is a deliberately verbose baseline.
            extract = {"answer": chunk["text"] + f" [{chunk['id']}]", "draft": None,
                       "citation_valid": True, "source": chunk, "explicit_refusal": False}
            row["bm25_extract"] = {"output": extract, "proxies": answer_row(extract, label)}
            if model is not None:
                if tokenizer is None:
                    raise ValueError("answer evaluation needs its tokenizer")
                if run:
                    adapted = generated(model, tokenizer, label["question"], chunk, context, 96, answer_format)
                    with model.disable_adapter():
                        base = generated(model, tokenizer, label["question"], chunk, context, 96, answer_format)
                    row["adapted"] = {"output": adapted, "proxies": answer_row(adapted, label)}
                else:
                    base = generated(model, tokenizer, label["question"], chunk, context, 96, answer_format)
                row["base"] = {"output": base, "proxies": answer_row(base, label)}
        rows.append(row)
        if progress:
            progress(index, len(labels))
    metrics = {"bm25": summarize([r["bm25"] for r in rows],
                                  ("known_relevant_at_1", "known_relevant_at_5", "known_relevant_mrr"))}
    if task == "rank":
        metrics["ranked"] = summarize([r["ranked"] for r in rows],
                                      ("known_relevant_at_1", "known_relevant_at_5", "known_relevant_mrr",
                                       "none_correct_proxy"))
    else:
        for system in ("bm25_extract", "base", "adapted"):
            found = [r[system]["proxies"] for r in rows if system in r]
            if found:
                metrics[system] = summarize(found, ("explicit_refusal", "refusal_correct_proxy",
                                                    "citation_valid", "known_source_cited",
                                                    "rubric_phrase_proxy", "reference_substring"))
    return {"schema": "kilix.help-llm.evaluation/v2", "dataset": dataset,
            "dataset_sha256": bundle["sha256"], "source_revision": data["revision"],
            "split": split, "task": task, "run": run, "candidate": candidate,
            "context": context, "count": len(rows), "metrics": metrics, "examples": rows,
            "metric_scope": "reviewed source IDs and phrase proxies; incomplete relevance and no semantic truth guarantee",
            "quality": "unqualified", "qualification_eligible": False}


def evaluate(name, split, sizer=None):
    directory = state_root() / "runs" / identifier(name)
    identity = read_json(directory / "run.json")
    if load_dataset(identity["dataset"])["data"].get("schema") == "kilix.help-llm.dataset/v2":
        report, _, model, tokenizer, head = load_run(name, identity["task"], sizer)
        result = evaluate_v2(report["dataset"], split, report["task"], report["context"], model, tokenizer, head,
                             name, read_json(directory / "plan.json")["candidate"]["id"],
                             report.get("answer_format", "plain-v1"), progress=_evaluation_progress)
        output = private_dir(state_root() / "evaluations") / f"{name}-{split}-{time.time_ns()}.json"
        write_json(output, result)
        return {"saved_to": str(output), "count": result["count"], "metrics": result["metrics"],
                "quality": "unqualified"}
    require_legacy_evaluation(load_dataset(identity["dataset"])["data"])
    task = identity["task"]
    report, data, model, tokenizer, head = load_run(name, task, sizer)
    labels = [r for r in data["examples"] if r["split"] == split]
    rows = []
    for label in labels:
        baseline = retrieve(data, label["question"], 5)
        row = {"id": label["id"], "retrieval_hit_at_5": label["source"] in [c["id"] for c in baseline]}
        baseline_position = next((i + 1 for i, c in enumerate(baseline) if c["id"] == label["source"]), None)
        row.update(retrieval_top1=baseline_position == 1,
                   retrieval_reciprocal_rank=1 / baseline_position if baseline_position else 0)
        if task == "rank":
            result = ranked(data, model, tokenizer, head, label["question"], report["context"])
            position = next((i + 1 for i, c in enumerate(result) if c["id"] == label["source"]), None)
            row.update(top1=position == 1, reciprocal_rank=1 / position if position else 0)
        else:
            result = generated(model, tokenizer, label["question"], baseline[0], report["context"], 96,
                               report.get("answer_format", "plain-v1"))
            with model.disable_adapter():
                unchanged = generated(model, tokenizer, label["question"], baseline[0], report["context"], 96,
                                      report.get("answer_format", "plain-v1"))
            # This is an extractive regression check, not semantic correctness.
            row.update(citation_valid=result["citation_valid"], abstained=result["abstained"],
                       reference_substring=bool(result["answer"] and label["answer"] in result["answer"]),
                       base_citation_valid=unchanged["citation_valid"],
                       base_reference_substring=bool(unchanged["answer"] and label["answer"] in unchanged["answer"]),
                       base_output=unchanged,
                       output=result)
        rows.append(row)
    metrics = {key: sum(float(r[key]) for r in rows) / len(rows) for key in rows[0]
               if key not in {"id", "output", "base_output"}}
    result = {"run": name, "split": split, "task": task, "count": len(rows), "metrics": metrics,
              "examples": rows, "quality": "unqualified", "calibrated": False}
    output = private_dir(state_root() / "evaluations") / f"{name}-{split}-{time.time_ns()}.json"
    write_json(output, result)
    return {**result, "saved_to": str(output)}


def baseline(dataset, candidate, context, split, sizer=None):
    bundle = load_dataset(dataset)
    configure()
    plan = recommend(bundle, context, 4, sizer, candidate, "answer")
    model, tokenizer = load_base(plan["candidate"]["generation_checkpoint"], "answer")
    model.eval()
    if bundle["data"].get("schema") == "kilix.help-llm.dataset/v2":
        result = evaluate_v2(dataset, split, "answer", context, model, tokenizer,
                             candidate=plan["candidate"]["id"], progress=_evaluation_progress)
        output = private_dir(state_root() / "evaluations") / f"baseline-{dataset}-{candidate}-{split}-{time.time_ns()}.json"
        write_json(output, result)
        return {"saved_to": str(output), "count": result["count"], "metrics": result["metrics"]}
    rows = []
    for label in bundle["data"]["examples"]:
        if label["split"] != split:
            continue
        chunk = retrieve(bundle["data"], label["question"], 1)[0]
        result = generated(model, tokenizer, label["question"], chunk, context, 96, "chat-nonthinking-v2")
        rows.append({"id": label["id"], "reference": label["answer"], "output": result,
                     "retrieval_top1": chunk["id"] == label["source"]})
    report = {"schema": "kilix.help-llm.baseline/v1", "dataset": dataset, "dataset_sha256": bundle["sha256"],
              "candidate": plan["candidate"]["id"], "checkpoint": plan["candidate"]["generation_checkpoint"],
              "answer_format": "chat-nonthinking-v2", "split": split, "context": context, "examples": rows,
              "qualification_eligible": False}
    output = private_dir(state_root() / "evaluations") / f"baseline-{dataset}-{candidate}-{split}-{time.time_ns()}.json"
    write_json(output, report)
    return {"saved_to": str(output), "count": len(rows), "examples": rows}
