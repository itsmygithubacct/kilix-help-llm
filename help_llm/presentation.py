"""Present admitted answers with documentation links from reviewed metadata.

No model is loaded and no URL is fetched here. Formatting never repairs a
missing command, supplies an answer from metadata, or promotes an uncited draft.
"""
import hashlib
import html
import json
import re
from urllib.parse import urlsplit

from .evaluation import explicit_refusal

SCHEMA = "kilix.help-llm.help-links/v1"
UNAVAILABLE = "I could not produce an answer with a verified help reference."


def source_identity(source):
    """Bind a mapping to the exact source selected for this generation."""
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    if any(not isinstance(source.get(k), str) or not source[k] for k in ("id", "path", "text")):
        raise ValueError("source needs an ID, path and text")
    if type(source.get("line")) is not int or source["line"] < 1:
        raise ValueError("source needs a positive line number")
    return {"id": source["id"], "path": source["path"], "line": source["line"],
            "text_sha256": hashlib.sha256(source["text"].encode("utf-8")).hexdigest()}


def source_key(source):
    return hashlib.sha256(json.dumps(source_identity(source), sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_registry(registry):
    if not isinstance(registry, dict) or registry.get("schema") != SCHEMA:
        raise ValueError("unsupported help-link registry")
    if not isinstance(registry.get("sources"), dict):
        raise ValueError("help-link registry needs sources")
    for key, entry in registry["sources"].items():
        if not isinstance(entry, dict) or not isinstance(entry.get("source"), dict):
            raise ValueError("invalid help-link source entry")
        actual = hashlib.sha256(json.dumps(entry["source"], sort_keys=True,
                                           separators=(",", ":")).encode("utf-8")).hexdigest()
        if key != actual:
            raise ValueError("help-link source identity mismatch")
        links = entry.get("links")
        if not isinstance(links, list) or not links:
            raise ValueError("help-link source needs reviewed links")
        for link in links:
            if not isinstance(link, dict):
                raise ValueError("invalid help link")
            title, url = link.get("title"), link.get("url")
            if not isinstance(title, str) or not title.strip() or any(ord(c) < 32 for c in title):
                raise ValueError("invalid help-link title")
            if not isinstance(url, str) or any(c.isspace() or c in '<>\\\"' for c in url):
                raise ValueError("invalid help-link URL")
            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise ValueError("help links must be credential-free HTTPS URLs")
    return registry


def _markdown(text):
    # Keep simple inline code; escape model-supplied link/HTML formatting.
    pieces = re.split(r"(`[^`\n]+`)", text)
    def prose(piece):
        # Bare generated URLs remain visible as code, so GFM cannot turn them
        # into additional clickable references outside the reviewed registry.
        return "".join("`" + p + "`" if re.fullmatch(r"https?://[^\s`]+", p) else
                       re.sub(r"([\\`*_{}\[\]<>!#|])", r"\\\1", p)
                       for p in re.split(r"(https?://[^\s`]+)", piece))
    return "".join(p if p.startswith("`") and p.endswith("`") else prose(p) for p in pieces)


def _html(text):
    return "".join("<code>" + html.escape(p[1:-1]) + "</code>" if p.startswith("`") and p.endswith("`")
                   else html.escape(p).replace("\n", "<br>")
                   for p in re.split(r"(`[^`\n]+`)", text))


def _without_references(answer, source_id):
    token = r"`?\[" + re.escape(source_id) + r"\]`?"
    text = re.sub(r"\[Source\s+" + token + r"\]\s*:?", "", answer, flags=re.I)
    text = re.sub(r"^The source ID is " + token + r"[.,]?\s*(?:(?:and )?the answer is:?\s*(?:that\s+)?)?",
                  "", text, flags=re.I)
    text = re.sub(r"(?:^|\s+)(?:Source(?: ID)?\s*:?\s*)?" + token + r"\s*[.:]?\s*$", "", text, flags=re.I)
    text = re.sub(token, "", text).strip()
    return re.sub(r"^Answer:\s*", "", text, flags=re.I).strip()


def _result(status, body, links, reason=None):
    # Only an explicitly leading command is lifted into a code block. Never
    # search the evidence or reorder alternatives to manufacture instructions.
    lead = re.fullmatch(r"(?:Run|Use) `([^`\n]+)`\.\s+(.+)", body, re.S)
    if lead is None:
        lead = re.fullmatch(r"```(?:sh|bash|shell)?\n([^`\n]+)\n```\s+(.+)", body, re.S)
    command, explanation = (lead.group(1), lead.group(2)) if lead else (None, body)
    if command:
        markdown = "```sh\n" + command + "\n```\n\n" + _markdown(explanation)
        markup = "<pre><code>" + html.escape(command) + "</code></pre><p>" + _html(explanation) + "</p>"
        text = command + "\n\n" + explanation
    else:
        markdown, markup, text = _markdown(body), "<p>" + _html(body) + "</p>", body
    if links:
        markdown += "\n\nRelated help: " + " · ".join("[" + _markdown(x["title"]) + "](<" + x["url"] + ">)" for x in links)
        markup += '<p class="related-help">Related help: ' + " · ".join(
            '<a href="' + html.escape(x["url"], quote=True) + '">' + html.escape(x["title"]) + '</a>' for x in links) + "</p>"
        text += "\n\nRelated help:\n" + "\n".join(x["title"] + ": " + x["url"] for x in links)
    return {"status": status, "reason": reason, "body": body, "command": command,
            "explanation": explanation, "help": links, "markdown": markdown, "html": markup, "text": text}


def present(output, registry):
    """Return a display object, keeping admission and presentation distinct.

    Plain accepted refusals stay plain. A refusal that cites a documented way
    to check state can include links. Withheld drafts never become display text.
    Citation validity establishes provenance only, not factual correctness.
    """
    validate_registry(registry)
    if not isinstance(output, dict):
        raise ValueError("answer output must be an object")
    answer = output.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return _result("withheld", UNAVAILABLE, [], "no-admitted-answer")
    answer = answer.strip()
    if any(ord(c) < 32 and c not in "\n\t" for c in answer):
        return _result("withheld", UNAVAILABLE, [], "control-character")
    citations = re.findall(r"\[([^\[\]\n]+)\]", answer)
    if not citations:
        if output.get("explicit_refusal") is True and explicit_refusal(answer):
            return _result("refusal", answer, [])
        return _result("withheld", UNAVAILABLE, [], "no-citation")
    source = output.get("source")
    try:
        identity, key = source_identity(source), source_key(source)
    except ValueError:
        return _result("withheld", UNAVAILABLE, [], "invalid-source")
    if not all(c == source["id"] for c in citations):
        return _result("withheld", UNAVAILABLE, [], "citation-mismatch")
    entry = registry["sources"].get(key)
    if not entry or entry["source"] != identity:
        return _result("withheld", UNAVAILABLE, [], "unmapped-source")
    body = _without_references(answer, source["id"])
    if not body:
        return _result("withheld", UNAVAILABLE, [], "empty-answer")
    links = list({x["url"]: {"title": x["title"], "url": x["url"]} for x in entry["links"]}.values())
    return _result("refusal" if explicit_refusal(answer) else "answer", body, links)
