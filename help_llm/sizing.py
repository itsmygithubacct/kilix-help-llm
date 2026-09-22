"""Use the shared provider's exact workload and checkpoint identities."""
import os
import shutil
import subprocess
from .data import SOURCE, digest, read_json, state_root


def provider(explicit=None):
    executable = explicit or os.environ.get("PLEBIAN_MODEL_SIZER") or shutil.which("plebian-model-sizer")
    if executable is None:
        source = SOURCE.parents[1] / "kilix-system-monitor/components/plebian-model-sizer/plebian-model-sizer"
        if source.is_file() and os.access(source, os.X_OK):
            executable = str(source)
    if executable is None:
        raise FileNotFoundError("install plebian-model-sizer or provide --sizer PATH")
    return executable


def recommend(bundle, context, rank, explicit=None, candidate=None, task="both"):
    if not 128 <= context <= 512 or not 1 <= rank <= 64:
        raise ValueError("CPU prototype requires context 128-512 and LoRA rank 1-64")
    catalog = read_json(SOURCE / "candidates.json")
    command = [provider(explicit), "recommend", "help-llm", "--catalog", str(SOURCE / "candidates.json"),
               "--task", task, "--phase", "both", "--context", str(context), "--batch", "1",
               "--lora-rank", str(rank), "--topics", "2", "--quant", "f32",
               "--train-backend", "cpu", "--infer-backend", "cpu",
               "--document-bytes", str(bundle["data"]["document_bytes"]), "--data-root", str(state_root()), "--json"]
    result = subprocess.run(command, capture_output=True, timeout=45)
    if result.returncode or len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError("shared model sizer failed")
    import json
    report = json.loads(result.stdout)
    if report.get("schema") != "plebian.models.llm-sizing/v1-development" or report.get("catalog_sha256") != digest(catalog):
        raise ValueError("sizer report schema/catalog does not match this module")
    expected_workload = {"task": task, "phase": "both", "context": context, "batch": 1,
                         "lora_rank": rank, "topics": 2, "quant": "f32", "train_backend": "cpu",
                         "infer_backend": "cpu", "co_resident": False, "checkpointing": True,
                         "document_bytes": bundle["data"]["document_bytes"]}
    if report.get("resource_source") != "live" or any(report.get("workload", {}).get(k) != v for k, v in expected_workload.items()):
        raise ValueError("sizer must assess this exact workload against live resources")
    supported = {c["id"]: c for c in catalog["candidates"] if c["architecture_class"] == "attention"}
    shortlist = [c for c in report["candidates"] if c["verdict"] == "estimated-fit" and c["id"] in supported]
    if candidate:
        shortlist = [c for c in shortlist if c["id"] == candidate]
    if not shortlist:
        raise ValueError("no supported candidate within current estimated CPU training/inference budgets")
    row = min(shortlist, key=lambda c: (max(p["parameters"] for p in c["profiles"]), c["id"]))
    return {"schema": "kilix.help-llm.plan/v1", "dataset_sha256": bundle["sha256"],
            "candidate": supported[row["id"]], "context": context, "lora_rank": rank,
            "task": task, "backend": "cpu", "dtype": "float32", "sizing": report,
            "quality": "unmeasured", "qualification_eligible": False}
