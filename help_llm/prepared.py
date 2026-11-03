"""Deterministic, read-only-at-runtime lookup preparation. Standard library only.

The cache is data, never executable code. Actual input bytes and implementation
bytes determine validity. Missing, stale or damaged data causes a fresh build
in memory; it never resurrects stale citations or expansion questions.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import zlib

from .lexical import Analyzer, Constraints, index_words

VERSION = b"help-lookup-prepared-v1"
FILENAME = "lookup-prepared.json.gz"
MAX_BYTES = 32 * 1024 * 1024


def fingerprint(root, index):
    digest = hashlib.sha256()

    def add(name, raw):
        for value in (name.encode(), raw):
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)

    add("schema", VERSION)
    add("python", sys.implementation.cache_tag.encode())
    for name in ("lookup.py", "lexical.py", "prepared.py"):
        add("code/" + name, (Path(__file__).parent / name).read_bytes())
    for name in ("sources.json", "questions.json", "external.jsonl"):
        add("index/" + name, (index / name).read_bytes())
    for source in json.loads((index / "sources.json").read_text(encoding="utf-8")):
        path = root / source["path"]
        add("source/" + source["path"], b"present\0" + path.read_bytes() if path.is_file() else b"missing")
    return digest.hexdigest()


def build(root, index):
    # Late import avoids a cycle when Lookup asks for its prepared representation.
    from .lookup import QUESTION_WEIGHT, STOP, load_passages
    passages, current = load_passages(root, index)
    questions = json.loads((index / "questions.json").read_text(encoding="utf-8"))
    bodies = [p["heading"] + " " + p["text"] for p in passages]
    expansions = [" ".join(questions.get(p["id"], [])) if p["id"] in current else "" for p in passages]
    docs = []
    for body, expansion in zip(bodies, expansions):
        doc = Counter(index_words(body, STOP))
        for word, n in Counter(index_words(expansion, STOP)).items():
            doc[word] += n * QUESTION_WEIGHT
        docs.append(dict(doc))
    lengths = [sum(d.values()) for d in docs]
    average = sum(lengths) / max(1, len(lengths))
    frequency = Counter(word for d in docs for word in d)
    count = len(docs)
    idf = {word: math.log(1 + (count - n + .5) / (n + .5)) for word, n in frequency.items()}
    metadata_analyzer = Analyzer(bodies + expansions, STOP)
    constraints = Constraints(passages, metadata_analyzer)
    return {"passages": passages, "docs": docs, "lengths": lengths,
            "average": average, "idf": idf, "constraints": constraints.prepared()}


def encode(data, key):
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    raw = b"\n".join((VERSION, key.encode("ascii"), hashlib.sha256(payload).hexdigest().encode("ascii"), payload))
    return gzip.compress(raw, mtime=0)


def valid(data):
    """Check serialized shape and numeric domains before exposing cached data."""
    passages, docs = data["passages"], data["docs"]
    n = len(passages)
    if len(docs) != n or len(data["lengths"]) != n or len({p["id"] for p in passages}) != n:
        return False
    for p in passages:
        if not all(isinstance(p[k], str) for k in ("id", "source", "repo", "path", "heading", "text", "commit")):
            return False
    for i, doc in enumerate(docs):
        if not all(isinstance(w, str) and type(v) in (int, float) and math.isfinite(v) and v > 0 for w, v in doc.items()):
            return False
        if sum(doc.values()) != data["lengths"][i]:
            return False
    if data["average"] != sum(data["lengths"]) / max(1, n):
        return False
    if not all(isinstance(w, str) and type(v) in (int, float) and math.isfinite(v) and v > 0 for w, v in data["idf"].items()):
        return False
    c = data["constraints"]
    if not all(len(c[k]) == n for k in ("roles", "path_words", "stem_words", "metadata")):
        return False
    if not all(len(role) == 2 and all(type(v) is bool for v in role) for role in c["roles"]):
        return False
    if not all(isinstance(w, str) for words in [c["vocabulary"], *c["path_words"], *c["stem_words"], *c["metadata"]] for w in words):
        return False
    return (all(isinstance(k, str) and isinstance(v, str) for k, v in c["bases"].items())
            and all(isinstance(w, str) and all(type(i) is int and 0 <= i < n for i in ids) for w, ids in c["postings"].items()))


def load(root, index, use_cache=True):
    key = fingerprint(root, index)
    if use_cache:
        try:
            with gzip.open(index / FILENAME, "rb") as f:
                raw = f.read(MAX_BYTES + 1)
            version, stored_key, digest, payload = raw.split(b"\n", 3)
            if (len(raw) <= MAX_BYTES and version == VERSION and stored_key.decode("ascii") == key
                    and hashlib.sha256(payload).hexdigest().encode("ascii") == digest):
                data = json.loads(payload)
                if valid(data) and fingerprint(root, index) == key:
                    return data, True
        except (OSError, EOFError, ValueError, KeyError, TypeError, AttributeError, OverflowError, zlib.error):
            pass
    data = build(root, index)
    # Inputs might have changed while cutting or indexing. A lookup may use this
    # fresh snapshot, but a build command must not stamp it with an earlier key.
    return data, False


def prepare(root, index):
    before = fingerprint(root, index)
    data = build(root, index)
    if fingerprint(root, index) != before:
        raise ValueError("lookup inputs changed during preparation")
    output = index / FILENAME
    output.write_bytes(encode(data, before))
    return output


def main():
    from .lookup import ROOT, INDEX
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--index", type=Path, default=INDEX)
    args = parser.parse_args()
    output = prepare(args.root, args.index)
    print(json.dumps({"prepared": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
