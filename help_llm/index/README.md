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

Measured on 253 held-out questions whose answers are in these documents: the answering passage is in the top 5
for 79% of fully documented questions (plain BM25: 65%) and for 66% of "check my machine" questions (plain: 47%).
