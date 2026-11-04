"""Local FP32 inference for the selected, unmerged Qwen3.5 Help adapter."""
import os

from . import published
from .data import answer_prompt, private_dir, state_root
from .presentation import present
from .runtime import chat_encoded, generated


def load(value, sizer=None):
    published.admit(value, sizer)
    root = published.verify(value)
    for variable, suffix in {"HF_HOME": "huggingface", "TORCH_HOME": "torch",
                             "XDG_CACHE_HOME": "xdg"}.items():
        os.environ[variable] = str(private_dir(state_root() / "cache" / suffix))
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false",
                      OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    import torch
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration
    from peft import PeftModel
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(root / "parent", local_files_only=True,
                                              trust_remote_code=False)
    base, info = Qwen3_5ForConditionalGeneration.from_pretrained(
        root / "parent", local_files_only=True, trust_remote_code=False,
        dtype=torch.float32, attn_implementation="eager", output_loading_info=True)
    if any(info.get(k) for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
        raise ValueError("parent checkpoint did not load exactly")
    model = PeftModel.from_pretrained(base, root / "adapter", adapter_name="sft",
                                     is_trainable=False, local_files_only=True)
    model.requires_grad_(False)
    model.eval()
    return model, tokenizer


def answer_with(model, tokenizer, value, question, source, registry):
    # Never truncate evidence or reduce the frozen 96-token answer allowance.
    row = chat_encoded(tokenizer, answer_prompt(question, source), context=384)
    if len(row["input_ids"]) + 96 > 384:
        raise ValueError("question and evidence exceed the Help context; shorten the question or use kilix help-search")
    result = generated(model, tokenizer, question, source, 384, 96, "chat-nonthinking-v2")
    result.pop("draft", None)
    result["model"] = value["id"]
    result["parent_revision"] = value["parent"]["revision"]
    result["adapter_sha256"] = value["adapter"]["files"]["adapter_model.safetensors"]["sha256"]
    result["quality"] = value["quality"]["scope"]
    result["presentation"] = present(result, registry)
    return result


def query(question, sizer=None):
    source, registry = published.evidence(question)
    if source is None:
        result = {"answer": "I do not know. No matching Help documentation was found.",
                  "explicit_refusal": True}
        result["presentation"] = present(result, registry)
        return result
    value = published.manifest()
    with published.model_lock():
        model, tokenizer = load(value, sizer)
        return answer_with(model, tokenizer, value, question, source, registry)
