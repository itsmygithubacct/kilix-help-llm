"""Pinned default model acquisition and compact documentation retrieval.

The manifest is shipped source. Downloads happen only on explicit setup; an
answer never downloads weights or executes a command supplied by the model.
"""
from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen

from .data import SOURCE, digest, identifier, private_dir, read_json, state_root
from .lookup import tokens
from .presentation import SCHEMA, source_identity, source_key, validate_registry
from .sizing import provider

MANIFEST = SOURCE / "help_llm/published-model.json"
INDEX = SOURCE / "help_llm/index/answers.json"


def manifest():
    value = read_json(MANIFEST)
    if value.get("schema") != "kilix.help-llm.published-model/v1":
        raise ValueError("unsupported published model manifest")
    identifier(value["id"])
    if not re.fullmatch(r"[0-9a-f]{40}", value["parent"]["revision"]):
        raise ValueError("parent revision must be an immutable commit")
    for group in ("parent", "adapter"):
        for name, spec in value[group]["files"].items():
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
                raise ValueError("invalid checkpoint filename")
            if type(spec["bytes"]) is not int or spec["bytes"] <= 0:
                raise ValueError("invalid checkpoint size")
            if not re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]):
                raise ValueError("invalid checkpoint digest")
            url = urlsplit(spec["url"])
            if (url.scheme != "https" or url.hostname not in {"github.com", "huggingface.co"}
                    or url.username or url.password or url.query or url.fragment):
                raise ValueError("invalid checkpoint URL")
    return value


def model_root(value):
    return state_root() / "published" / identifier(value["id"])


def sizing_provider(explicit=None, ensure=False):
    if explicit or os.environ.get("PLEBIAN_MODEL_SIZER") or shutil.which("plebian-model-sizer"):
        return provider(explicit)
    host = os.environ.get("KILIX_HOME")
    if host:
        installer = Path(host) / "scripts/install-kilix-tts-sizer.sh"
        if installer.is_file() and not installer.is_symlink() and os.access(installer, os.X_OK):
            result = subprocess.run([str(installer), *([] if ensure else ["--print-path"])],
                                    capture_output=True, text=True, timeout=60)
            path = Path(result.stdout.strip())
            if result.returncode == 0 and path.is_file() and os.access(path, os.X_OK):
                return str(path)
    return provider(explicit)


@contextmanager
def model_lock():
    path = private_dir(state_root()) / "published.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another Help setup or answer is running; try again shortly") from None
        yield
    finally:
        os.close(fd)


def matches(path, spec):
    if path.is_symlink():
        raise ValueError("checkpoint files cannot be symlinks")
    if not path.is_file() or path.stat().st_size != spec["bytes"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == spec["sha256"]


def verify(value):
    root = model_root(value)
    for group in ("parent", "adapter"):
        private_dir(root / group)
        for name, spec in value[group]["files"].items():
            if not matches(root / group / name, spec):
                raise ValueError("Help model is missing or damaged; run kilix help-setup "
                                 "(or kilix-help-llm setup)")
    config = read_json(root / "adapter/adapter_config.json")
    if (config.get("base_model_name_or_path") != value["parent"]["model_id"]
            or config.get("revision") != value["parent"]["revision"]
            or config.get("r") != value["adapter"]["rank"]
            or config.get("lora_alpha") != value["adapter"]["alpha"]):
        raise ValueError("adapter does not match its pinned parent and recipe")
    return root


def acquire(value, base_dir=None, adapter_dir=None):
    """Install exact files atomically, optionally from existing offline copies."""
    root = model_root(value)
    for group, local in (("parent", base_dir), ("adapter", adapter_dir)):
        directory = private_dir(root / group)
        for name, spec in value[group]["files"].items():
            target = directory / name
            if matches(target, spec):
                continue
            fd, temporary = tempfile.mkstemp(prefix=".download-", dir=directory)
            try:
                stream = ((Path(local) / name).open("rb") if local else
                          urlopen(spec["url"], timeout=60))
                with stream, os.fdopen(fd, "wb") as output:
                    fd = None
                    if not local and urlsplit(stream.url).scheme != "https":
                        raise ValueError("checkpoint download redirected away from HTTPS")
                    size, sha = 0, hashlib.sha256()
                    while block := stream.read(1024 * 1024):
                        size += len(block)
                        if size > spec["bytes"]:
                            raise ValueError("checkpoint exceeds its pinned size")
                        sha.update(block)
                        output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                if size != spec["bytes"] or sha.hexdigest() != spec["sha256"]:
                    raise ValueError("checkpoint download failed hash/size verification")
                os.replace(temporary, target)
            finally:
                if fd is not None:
                    os.close(fd)
                Path(temporary).unlink(missing_ok=True)
    return verify(value)


def admit(value, explicit=None):
    """Assess this selected model, never silently substitute a smaller model."""
    import json
    private_dir(state_root())
    catalog = read_json(SOURCE / "candidates.json")
    document_bytes = INDEX.stat().st_size
    workload = {"task": "answer", "phase": "infer", "context": 384, "batch": 1,
                "lora_rank": 16, "topics": 2, "quant": "f32", "train_backend": "cpu",
                "infer_backend": "cpu", "co_resident": False, "checkpointing": True,
                "document_bytes": document_bytes}
    command = [sizing_provider(explicit), "recommend", "help-llm", "--catalog", str(SOURCE / "candidates.json"),
               "--task", "answer", "--phase", "infer", "--context", "384", "--batch", "1",
               "--lora-rank", "16", "--topics", "2", "--quant", "f32", "--train-backend", "cpu",
               "--infer-backend", "cpu", "--document-bytes", str(document_bytes),
               "--data-root", str(state_root()), "--json"]
    result = subprocess.run(command, capture_output=True, timeout=45)
    if result.returncode or len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError("shared model sizer failed")
    report = json.loads(result.stdout)
    if (report.get("schema") != "plebian.models.llm-sizing/v1-development"
            or report.get("catalog_sha256") != digest(catalog)
            or report.get("resource_source") != "live"
            or any(report.get("workload", {}).get(k) != v for k, v in workload.items())):
        raise ValueError("sizer must assess the exact Help workload against live resources")
    candidate = next(c for c in catalog["candidates"] if c["id"] == "qwen3.5-2b")
    checkpoint = candidate["generation_checkpoint"]
    if (checkpoint["revision"] != value["parent"]["revision"]
            or checkpoint["config"]["sha256"] != value["parent"]["files"]["config.json"]["sha256"]):
        raise ValueError("sizing catalog does not describe the selected model")
    row = next((c for c in report["candidates"] if c["id"] == candidate["id"]), {})
    if row.get("verdict") != "estimated-fit":
        raise ValueError("the default 2B Help model does not fit current resources; use kilix help-search")
    if not row.get("profiles") or any(
            profile.get("model_id") != checkpoint["model_id"]
            or profile.get("revision") != checkpoint["revision"]
            or profile.get("config_sha256") != checkpoint["config"]["sha256"]
            for profile in row["profiles"]):
        raise ValueError("sizing report describes a different checkpoint")
    return report


def setup(base_dir=None, adapter_dir=None, sizer=None):
    value = manifest()
    with model_lock():
        admit(value, sizing_provider(sizer, ensure=True))
        uv = shutil.which("uv")
        if uv is None:
            raise ValueError("install uv first, then run kilix help-setup again")
        env = dict(os.environ)
        for name, relative in (("UV_CACHE_DIR", "cache/uv"),
                               ("UV_PYTHON_INSTALL_DIR", "runtimes/python"),
                               ("UV_PROJECT_ENVIRONMENT", "runtimes/cpu")):
            env[name] = str(private_dir(state_root() / relative))
        subprocess.run([uv, "sync", "--project", str(SOURCE / "runtime"), "--locked",
                        "--python", "3.12.8"], env=env, check=True)
        acquire(value, base_dir, adapter_dir)
    return {"model": value["id"], "ready": True, "release_target": value["release_target"]}


def status():
    value = manifest()
    try:
        with model_lock():
            verify(value)
        installed, error = True, None
    except ValueError as exc:
        installed, error = False, str(exc)
    runtime = (state_root() / "runtimes/cpu/bin/python").is_file()
    return {"model": value["id"], "release_target": value["release_target"],
            "weights_verified": installed, "runtime_installed": runtime,
            "ready": installed and runtime, "detail": error,
            "quality": value["quality"], "setup": "kilix help-setup"}


def evidence(question):
    if not question.strip() or len(question) > 2000 or "\0" in question:
        raise ValueError("question must contain 1-2000 characters without NUL")
    index = read_json(INDEX)
    if index.get("schema") != "kilix.help-llm.answer-index/v1":
        raise ValueError("unsupported answer index")
    rows = index["sources"]
    docs = []
    registry = {"schema": SCHEMA, "sources": {}}
    for row in rows:
        source = row["source"]
        registry["sources"][source_key(source)] = {"source": source_identity(source), "links": row["links"]}
        doc = Counter(tokens(row["title"] + " " + source["text"]))
        for word, count in Counter(tokens(" ".join(row["queries"]))).items():
            doc[word] += count * 0.5
        docs.append(doc)
    validate_registry(registry)
    lengths = [sum(doc.values()) for doc in docs]
    average = sum(lengths) / len(docs)
    frequency = Counter(word for doc in docs for word in doc)
    scores = []
    for i, doc in enumerate(docs):
        score = sum(math.log(1 + (len(docs) - frequency[word] + .5) / (frequency[word] + .5))
                    * doc[word] * 2.5 / (doc[word] + 1.5 * (.25 + .75 * lengths[i] / average))
                    for word in tokens(question) if doc[word])
        if score > 0:
            scores.append((score, i))
    scores.sort(key=lambda pair: (-pair[0], rows[pair[1]]["source"]["id"]))
    return (rows[scores[0][1]]["source"] if scores else None), registry
