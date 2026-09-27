# Lookup index

Passages (450) come from MIT-licensed documentation:

- `docs/kilix/` and `docs/kitty/` in this repository are cut into passages at runtime by `help_llm/lookup.py`
  (split at headings, short sections merged, long ones split). `sources.json` records each file's commit and
  SHA-256; a file that has changed since the index was built is still searched, but without the questions below.
- `external.jsonl`: passages from `pleb` at `7ab57fea` and `plebian-os` at `4b8dc54e` (both MIT; README, upgrade,
  release and build documents), with repository, commit and path.

`questions.json`: for each passage id, user-style questions written for that passage (generated and then checked
against the passage). They are only used to find passages: a query is matched against each passage's text plus its
questions, which is how everyday wording ("split this terminal") reaches documents that use other words
("new-pane", "Ctrl+Alt+R"). Questions close to the project's held-out evaluation questions were removed.

Development-set measurements (not the held-out test set; used to choose `QUESTION_WEIGHT` = 0.5), on the project's
v2 dev questions whose answers are in these documents: the answering passage is ranked first for 43% and in the top 5
for 80% of 169 fully documented questions (plain BM25 top 5: 65%), and in the top 5 for 69% of 32 "check my machine"
questions (plain BM25: 47%) and 58% of 52 partly documented ones. A related but less direct passage sometimes ranks
first, so read the top few results.

Passages follow the corpus the questions were written for: split at headings and between paragraphs at 450 words;
a single paragraph longer than that stays whole (8 passages).
