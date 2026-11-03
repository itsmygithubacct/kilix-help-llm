"""Conservative lexical matching, with source-only syntax and role constraints.

These checks restrict retrieval; they do not establish that a passage answers a
question. Original text, passage boundaries and citations are never rewritten.
"""
import re
from pathlib import PurePosixPath


def components(text):
    """One word stream, without counting an identifier and its parts twice."""
    text = re.sub(r"\bwon['’]t\b", "will not", text, flags=re.I)
    text = re.sub(r"\bcan['’]t\b", "can not", text, flags=re.I)
    text = re.sub(r"n['’]t\b", " not", text, flags=re.I)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", text)
    return re.findall(r"[a-z0-9]+", text.lower())


class Analyzer:
    def __init__(self, texts, stop):
        self.vocabulary = {w for text in texts for w in components(text)}
        self.stop = stop
        self.cache = {}

    def base(self, word):
        """Strip only ordinary suffixes with a unique attested shorter base.

        Ambiguous forms (e.g. axes when both ax and axe occur) stay distinct.
        No derivational prefixes or suffixes such as dis-, -er or -tion change.
        """
        if word in self.cache:
            return self.cache[word]
        possible = set()
        if len(word) > 3:
            if word.endswith(("ies", "ied")):
                possible.add(word[:-3] + "y")
            if word.endswith("s") and not word.endswith(("ss", "us", "is")):
                possible.add(word[:-1])
                if word.endswith("es"):
                    possible.add(word[:-2])
            for suffix in ("ed", "ing"):
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    stem = word[:-len(suffix)]
                    possible.update((stem, stem + "e"))
                    if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
                        possible.add(stem[:-1])
            if word.endswith("ly"):
                possible.add(word[:-2])
                if word.endswith("ily"):
                    possible.add(word[:-3] + "y")
                if word.endswith("ally"):
                    possible.add(word[:-4])
        possible = {w for w in possible if len(w) >= 2 and len(w) < len(word) and w in self.vocabulary}
        # Prefer the ordinary y plural over a coincidental plural stem (policies).
        if word.endswith(("ies", "ied")) and word[:-3] + "y" in possible:
            possible = {word[:-3] + "y"}
        result = self.base(next(iter(possible))) if len(possible) == 1 else word
        self.cache[word] = result
        return result

    def words(self, text):
        return [base for word in components(text)
                if word not in self.stop and (base := self.base(word)) not in self.stop]


_PAGE = re.compile(r"(?<![\w/.-])(?:[\w.-]+/)*[\w.-]+\.md\b", re.I)
_PAGE_PREFIX = re.compile(
    r"^\s*(?:in|from|according to)\s+(?:the\s+)?(.+?)\s+"
    r"(?:page|guide|manual|reference)\s*[,;:]\s*", re.I)
_STRUCTURED = re.compile(r"(?<![\w.+-])(?:--[A-Za-z0-9][\w-]*|"
                         r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+|"
                         r"[A-Za-z][\w-]*(?:\.[A-Za-z0-9_-]+)+)(?![\w.+-])")
_DEFINITION = re.compile(
    r"(?:`([A-Za-z][A-Za-z0-9_]*)`|\b((?-i:[A-Z][A-Z0-9]*_[A-Z0-9_]+))\b)\s+"
    r"(?:sets?|controls?|selects?|changes?|enables?|disables?|determines?|limits?|caps?)\b", re.I)
_ASSIGNMENT = re.compile(r"(?<![-\w.])[A-Za-z_]\w*=(?!=)\S+")
_CHORD = re.compile(r"\b(?:ctrl|control|alt|shift|super|cmd|meta)(?:\+[A-Za-z0-9_]+)+\b", re.I)


def source_roles(text):
    """Use body evidence, never expansion questions or heading vocabulary."""
    actions = set(re.findall(r"`([\w.-]+)`\s+action\b", text))
    actions.update(re.findall(r"\baction\s+`([\w.-]+)`", text))
    actions.update(re.findall(r"(?m)^\s*map\s+\S+\s+([\w.-]+)", text))
    setting = bool(_ASSIGNMENT.search(text) or any((m[1] or m[2]) not in actions for m in _DEFINITION.finditer(text)))
    action = bool(_CHORD.search(text) or re.search(r"(?m)^\s*map\s+\S+\s+\S+", text)
                  or actions
                  or re.search(r"\b(?:press|hit)\s+(?:`)?(?:Enter|Escape|Esc|F\d{1,2})\b", text, re.I))
    return setting, action


def requested_roles(question):
    setting = bool(re.search(r"\b(?:setting|(?:config|configuration)\s+(?:key|option))\b", question, re.I))
    action = bool(re.search(r"\b(?:shortcuts?|hotkeys?|key\s*bindings?|keyboard\s+keys?)\b|"
                            r"\b(?:which|what)\s+(?:key|action)\b", question, re.I))
    return setting, action


def exact_literals(question):
    literals = set(_STRUCTURED.findall(question))
    literals.update(re.findall(r"(?<!`)`([^`\n]+)`(?!`)", question))
    return sorted(s for s in literals if not _PAGE.fullmatch(s))


def contains_literal(text, literal):
    # Identifier components cannot stand in for an explicitly named identifier.
    pattern = (r"(?<![A-Za-z0-9_])(?<![A-Za-z0-9_][.+/-])" + re.escape(literal)
               + r"(?![A-Za-z0-9_]|[.+/-][A-Za-z0-9_])")
    return re.search(pattern, text) is not None


class Constraints:
    def __init__(self, passages, analyzer):
        self.passages = passages
        self.analyzer = analyzer
        self.roles = [source_roles(p["text"]) for p in passages]
        self.source = [p["heading"] + "\n" + p["text"] for p in passages]
        self.path_words = [set(analyzer.words(str(PurePosixPath(p["path"]).with_suffix("")))) for p in passages]
        self.stem_words = [set(analyzer.words(PurePosixPath(p["path"]).stem)) for p in passages]
        self.metadata = [words | set(analyzer.words(p["heading"])) for words, p in zip(self.path_words, passages)]

    def select(self, question):
        """Return topical question and eligible passage indices. No query I/O."""
        eligible = set(range(len(self.passages)))
        pages = _PAGE.findall(question)
        for page in pages:
            eligible &= {i for i, p in enumerate(self.passages)
                         if p["path"] == page or p["path"].endswith("/" + page)}
        prefix = _PAGE_PREFIX.match(question)
        topic = question[prefix.end():] if prefix else question
        if prefix and not pages:
            name = set(self.analyzer.words(prefix[1])) - {"help", "documentation"}
            # A named file is stronger evidence than a generic heading mention.
            direct = {i for i, words in enumerate(self.stem_words) if name and name <= words}
            eligible &= direct or {i for i, words in enumerate(self.metadata) if name and name <= words}
        literals = exact_literals(topic)
        setting, action = requested_roles(topic)
        eligible = {i for i in eligible if (not setting or self.roles[i][0])
                    and (not action or self.roles[i][1])
                    and all(contains_literal(self.source[i], s) for s in literals)}
        topic = _PAGE.sub("", topic)
        return topic, eligible
