# Lookup index

Passages come from MIT-licensed documentation:

- `docs/kilix/` and `docs/kitty/` in this repository are cut into passages at runtime by `help_llm/lookup.py`
  (split at headings, short sections merged, long ones split). `sources.json` records each file's commit and
  SHA-256; a file that has changed since the index was built is still searched, but without the questions below.
- `external.jsonl`: the Pleb README at `631647f62216be802f0be22f4ea976e74164e6d2` and
  the Plebian-OS README at `a8bd79ee7237994d5d6246ac7bb7a8a439cfa3ad` describe the
  published 0.2.2 Linux release. Other upgrade, historical release and build
  documents retain their original `pleb` (`7ab57fea`) and `plebian-os`
  (`4b8dc54e`) snapshots. Each passage records its own repository, commit and path.
  Questions for the replaced README passages were removed rather than attached
  to changed text. Oversized external README paragraphs are split at line
  boundaries without dropping source text.

`questions.json`: for each passage id, user-style questions written for that passage (generated and then checked
against the passage). They are only used to find passages: a query is matched against each passage's text plus its
questions, which is how everyday wording ("split this terminal") reaches documents that use other words
("new-pane", "Ctrl+Alt+R"). Questions close to the project's held-out evaluation questions were removed.

Historical development-set measurements for the original 450-passage snapshot
(not the held-out test set; used to choose `QUESTION_WEIGHT` = 0.5), on the project's
v2 dev questions whose answers are in these documents: the answering passage is ranked first for 43% and in the top 5
for 80% of 169 fully documented questions (plain BM25 top 5: 65%), and in the top 5 for 69% of 32 "check my machine"
questions (plain BM25: 47%) and 58% of 52 partly documented ones. A related but less direct passage sometimes ranks
first, so read the top few results.

Unchanged passages follow the corpus their questions were written for: split at
headings and between paragraphs at 450 words. The 0.2.2 README refresh has no
new retrieval-quality measurement; the historical scores above do not transfer
to the changed corpus. The copied Kilix status edits are searched without their
old question expansions until a separate index refresh binds them.
