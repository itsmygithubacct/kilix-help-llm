"""Search-first help: find the documentation passages that answer a question. Standard library only, no model.

Passages come from the Kilix and kitty guides in this repository's `docs/` (cut at runtime) and from the pleb and
plebian-os documents shipped in `help_llm/index/external.jsonl` (both MIT). Each passage is indexed together with
user-style questions written for it (`help_llm/index/questions.json`, doc2query expansion) and ranked with BM25,
so everyday wording finds documents that use other words.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = Path(__file__).resolve().parent / "index"
STOP = set("a an the and or of to in on for with is are be it this that how do i my can what where why when does from by as at".split())
MIN_WORDS, MAX_WORDS = 60, 450


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9_+.-]+", text.lower()) if w not in STOP]


def sections(markdown):
    """(heading path, text) split at #..### headings outside code fences."""
    path, buf, fence = [], [], False
    for line in markdown.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        match = None if fence else re.match(r"^(#{1,3})\s+(.*)", line)
        if match:
            if "".join(buf).strip():
                yield list(path), "\n".join(buf).strip()
            level = len(match.group(1))
            path = path[:level - 1] + [match.group(2).strip()]
            buf = []
        else:
            buf.append(line)
    if "".join(buf).strip():
        yield list(path), "\n".join(buf).strip()


def split_long(text):
    paragraphs, current, out = re.split(r"\n\s*\n", text), [], []
    for paragraph in paragraphs:
        if current and len(" ".join(current).split()) + len(paragraph.split()) > MAX_WORDS:
            out.append("\n\n".join(current))
            current = []
        current.append(paragraph)
    if current:
        out.append("\n\n".join(current))
    return out


def cut(label, path, raw):
    """Passages of one Markdown file, identical to the corpus the questions were written for."""
    merged = []
    for heading, text in sections(raw):
        if merged and len(merged[-1][1].split()) < MIN_WORDS:
            merged[-1] = (merged[-1][0], merged[-1][1] + "\n\n" + text)
        else:
            merged.append((heading, text))
    out, n = [], 0
    for heading, text in merged:
        for part in split_long(text):
            n += 1
            out.append({"id": f"{label}:{path}#{n}", "source": label, "repo": "kilix-help-llm", "path": path,
                        "heading": " > ".join(heading), "text": part})
    return out


def load_passages(root=ROOT, index=INDEX):
    """In-repo guides cut from docs/ (questions attach only if a file is unchanged), plus shipped external docs."""
    passages, current = [], set()
    for source in json.loads((index / "sources.json").read_text(encoding="utf-8")):
        file = root / source["path"]
        if not file.is_file():
            continue
        raw = file.read_bytes()
        same = hashlib.sha256(raw).hexdigest() == source["sha256"]
        for p in cut(source["label"], source["path"], raw.decode("utf-8")):
            p["commit"] = source["commit"] if same else ""
            passages.append(p)
            if same:
                current.add(p["id"])
    for line in open(index / "external.jsonl", encoding="utf-8"):
        p = json.loads(line)
        passages.append(p)
        current.add(p["id"])
    return passages, current


class Lookup:
    def __init__(self, root=ROOT, index=INDEX, k1=1.5, b=0.75):
        self.passages, current = load_passages(root, index)
        questions = json.loads((index / "questions.json").read_text(encoding="utf-8"))
        self.docs = [Counter(tokens(p["heading"] + " " + p["text"] + " " +
                                    (" ".join(questions.get(p["id"], [])) if p["id"] in current else "")))
                     for p in self.passages]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.average = sum(self.lengths) / max(1, len(self.lengths))
        frequency = Counter(word for d in self.docs for word in d)
        count = len(self.docs)
        self.idf = {word: math.log(1 + (count - n + .5) / (n + .5)) for word, n in frequency.items()}
        self.k1, self.b = k1, b

    def search(self, question, k=5):
        query = tokens(question)
        scored = []
        for i, doc in enumerate(self.docs):
            score = 0.0
            for word in query:
                f = doc.get(word)
                if f:
                    score += self.idf[word] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.average))
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [dict(self.passages[i], score=round(score, 3)) for score, i in scored[:k]]


def render(results, full=False, width=600):
    if not results:
        return "No matching documentation found. Try different words, or ask about Kilix, kitty, pleb or plebian-os."
    blocks = []
    for n, p in enumerate(results, 1):
        text = p["text"].strip()
        if not full and len(text) > width:
            text = text[:width].rsplit(" ", 1)[0] + " …"
        source = f"{p['repo']}:{p['path']}" + (f" @ {p['commit'][:8]}" if p.get("commit") else "")
        blocks.append(f"[{n}] {p['heading']}\n    {source}\n\n" + "\n".join("    " + line for line in text.splitlines()))
    return "\n\n".join(blocks)
