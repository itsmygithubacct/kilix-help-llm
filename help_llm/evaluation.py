"""Reviewed-source and answer proxies. They do not certify factual truth."""
import re

from .data import digest, normalized


def known_position(candidates, label):
    relevant = set(label.get("relevant_sources", [label["source"]]))
    return next((i for i, row in enumerate(candidates, 1) if row["id"] in relevant), None)


def retrieval_row(candidates, label):
    position = known_position(candidates, label)
    return {"known_relevant_position": position,
            "known_relevant_at_1": position == 1 if not label.get("unanswerable") else None,
            "known_relevant_at_5": bool(position and position <= 5) if not label.get("unanswerable") else None,
            "known_relevant_mrr": (1 / position if position else 0) if not label.get("unanswerable") else None}


def explicit_refusal(text):
    """Conservative intent detector; manual review remains necessary."""
    clean = re.sub(r"\[[a-z0-9_-]+:[0-9]+\]", "", text.casefold()).strip()
    return bool(re.fullmatch(
        r"(?:i (?:do not|don't|cannot|can't) know(?: from the supplied excerpt)?|"
        r"the (?:excerpt|document|source) does not (?:say|answer|provide|specify)[^.]*|"
        r"i (?:cannot|can't) determine[^.]*)[.]?", clean))


def phrase_present(answer, phrase):
    # Word boundaries prevent short command names from matching unrelated words.
    return bool(re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", answer.casefold()))


def rubric_proxy(answer, rubric):
    if not rubric or not rubric.get("must_include"):
        return None
    required = all(any(phrase_present(answer, phrase) for phrase in clause)
                   for clause in rubric.get("must_include", []))
    forbidden = any(any(phrase_present(answer, phrase) for phrase in clause)
                    for clause in rubric.get("must_not_include", []))
    return required and not forbidden


def answer_row(output, label):
    text = output.get("answer") or output.get("draft") or ""
    refusal = explicit_refusal(text)
    source = output.get("source", {}).get("id")
    relevant = set(label.get("relevant_sources", [label["source"]]))
    return {"kind": "refusal" if refusal else "cited-answer" if output.get("citation_valid") else "uncited-draft",
            "explicit_refusal": refusal,
            "refusal_correct_proxy": refusal if label.get("unanswerable") else not refusal,
            "citation_valid": bool(output.get("citation_valid")),
            "known_source_cited": bool(output.get("citation_valid") and source in relevant),
            "rubric_phrase_proxy": (None if label.get("unanswerable") else
                                    rubric_proxy(text, label.get("rubric"))),
            "reference_substring": (None if label.get("unanswerable") else
                                    normalized(label["answer"]) in normalized(text)),
            "needs_human_review": True}


def summarize(rows, keys):
    result = {}
    for key in keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        result[key] = sum(values) / len(values) if values else None
        result[key + "_n"] = len(values)
    return result


def reviewed_metrics(report, ratings):
    """Bind judgments to exact saved outputs and prohibit silent omissions."""
    if ratings.get("evaluation_sha256") != digest(report):
        raise ValueError("review does not match the evaluation digest")
    if ratings.get("dataset_sha256") != report.get("dataset_sha256"):
        raise ValueError("review does not match the frozen dataset")
    entries = ratings.get("ratings")
    if not isinstance(entries, list):
        raise ValueError("ratings must be a list")
    expected = {(row["id"], key) for row in report["examples"]
                for key in ("bm25_extract", "base", "adapted") if key in row}
    actual = {(entry.get("id"), entry.get("system")) for entry in entries if isinstance(entry, dict)}
    if actual != expected or len(entries) != len(expected):
        raise ValueError("review must contain each saved system/example exactly once")
    allowed = {"correct", "supported", "command_correct", "abstention_correct"}
    for entry in entries:
        if any(entry.get(key) not in (True, False, None) for key in allowed):
            raise ValueError("review judgments must be boolean or null")
        if entry.get("correct") is None or entry.get("supported") is None:
            raise ValueError("every review requires correctness and source support judgments")
        if not isinstance(entry.get("note", ""), str) or len(entry.get("note", "")) > 2000:
            raise ValueError("review note is invalid")
    by_system = {}
    for system in sorted({entry["system"] for entry in entries}):
        by_system[system] = summarize([e for e in entries if e["system"] == system], sorted(allowed))
    return {"schema": "kilix.help-llm.review/v1", "evaluation_sha256": digest(report),
            "dataset_sha256": report["dataset_sha256"], "ratings": entries,
            "metrics": by_system, "qualification_eligible": False}


def review_template(report):
    return {"evaluation_sha256": digest(report), "dataset_sha256": report["dataset_sha256"],
            "ratings": [{"id": row["id"], "system": system, "correct": None,
                         "supported": None, "command_correct": None,
                         "abstention_correct": None, "note": ""}
                        for row in report["examples"]
                        for system in ("bm25_extract", "base", "adapted") if system in row]}
