# Lookup index

Passages (497) come from MIT-licensed documentation:

- `docs/kilix/` and `docs/kitty/` in this repository are cut into passages at runtime by `help_llm/lookup.py`
  (split at headings, short sections merged, long ones split). `sources.json` records each file's commit and
  SHA-256; a file that has changed since the index was built is still searched, but without the questions below.
- `external.jsonl`: passages from `pleb` at `7ab57fea` and `plebian-os` at `4b8dc54e` (both MIT; README, upgrade,
  release and build documents), with repository, commit and path.

`questions.json`: for each passage id, user-style questions written for that passage (generated and then checked
against the passage). They are only used to find passages: a query is matched against each passage's text plus its
questions, which is how everyday wording ("split this terminal") reaches documents that use other words
("new-pane", "Ctrl+Alt+R"). Questions close to the project's held-out evaluation questions were removed.

Historical development-set measurements before the documentation refresh (not the held-out test set; used to
choose `QUESTION_WEIGHT` = 0.5), on the project's
v2 dev questions whose answers are in these documents: the answering passage is ranked first for 43% and in the top 5
for 80% of 169 fully documented questions (plain BM25 top 5: 65%), and in the top 5 for 69% of 32 "check my machine"
questions (plain BM25: 47%) and 58% of 52 partly documented ones. A related but less direct passage sometimes ranks
first, so read the top few results.

The 0.2.3 documentation snapshot is recorded in `docs/kilix/SNAPSHOT.json`. Its
index contains 3,432 retained expansion questions. No new questions were generated.
Changed or removed passages lose their questions; an unchanged heading and exact
passage text in the same source document can retain questions at a new ordinal ID.
An ordinal match alone never establishes support. The historical measurements above
do not evaluate this refreshed corpus. The BM25 scorer and its weights are unchanged.

Passages use the existing heading/paragraph cutter with a 450-word target; a single
paragraph longer than that stays whole (10 passages in this snapshot, enumerated in
`tests/test_lookup.py`; the original corpus had eight).

To reproduce the source/question manifests from the committed document snapshot:

```sh
python3 -B -m help_llm.refresh \
  --base c4bf4367a23fffef6efa941550baf8603424fb2c \
  --documents-revision e7bb51a8edf754e207e6f99caf10fa1fda0a1be1 \
  --report ../refresh-report.json
```

The helper requires exact Git revisions, verifies document bytes against the
committed snapshot and refuses unlisted document changes. It writes only the two
index manifests and an explicit report outside the source checkout. External
passages and unchanged source records are preserved. Commit documents first so
every source citation names an existing Git blob, then commit the refreshed index.
