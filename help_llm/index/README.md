# Lookup index

Passages (502) come from MIT-licensed documentation:

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
index contains 3,380 retained expansion questions. No new questions were generated.
Changed or removed support loses its questions; an unchanged heading and complete
passage text in the same source document can retain questions at a new ordinal ID.
An unambiguous passage that keeps the complete old text as its exact leading
paragraphs can also retain those questions after new paragraphs are appended.
The new paragraphs must be reviewed for contradictions or qualifications of the
old text; textual containment alone is not a semantic review. This snapshot's
three prefix migrations add corroborating model-verification, tab terminology
and raw-listing facts while preserving all old text. No questions were generated.
An ordinal match alone never establishes support. The historical measurements above
do not evaluate this refreshed corpus. The BM25 formula and weights are unchanged.
Merged passages keep every contributing section heading;
this repairs missing search context without changing their body text or boundaries.

The semantic successor retains whole-token document/heading/question counts.
Known query terms keep their exact spelling rather than globally changing term
frequencies, document frequencies and lengths. Unknown natural words may resolve
to separator/camel components or an unambiguous attested ordinary inflection base.
Unknown code identifiers, flags and chords are kept atomic. Negative terms remain
searchable, and English negative contractions expand to `not`. This is lexical
matching, not logical entailment or a dictionary of semantic equivalences.

Standalone identifiers, explicitly required/named literals and recognized
definition requests require case-sensitive, boundary-correct occurrences in the
returned source. Contextual operation names in multi-term questions remain atomic
ranking terms, without a compulsory co-occurrence filter. Backticks alone do not
make ambiguous context a required answer literal. Expansion questions never
supply literal or role evidence. Clear setting and shortcut/action requests require
body evidence of that role; the ambiguous word `key` alone does not imply a keyboard.
An explicit declaration identifying an identifier as an environment variable or
configuration key, option, variable or setting supplies setting-role evidence
independently of its descriptive verb. Direct negated declarations, output-field
labels and action labels do not supply that type. Assignment and ordinary
identifier-definition patterns remain additional evidence. None of these patterns
establishes that a passage answers the complete question.
Conventional uppercase names with underscores can also supply this clue when
used as the subject of descriptive prose. Explicit output-field/action types and
negated setting declarations do not acquire that clue. This naming convention
does not turn arbitrary identifiers or uppercase words into configuration keys.
Setting intent requires a nominal request; the verb in "does setting a field"
does not demand configuration-definition evidence. These heuristics do not
certify complete factual support. Explicit filenames and paths restrict results
to that page. A natural named-guide prefix resolves the longest complete
filename-stem alias, retaining source and path qualifiers. Other descriptive
words around a recognized name do not rename the page. Equally named pages can
remain ambiguous; unknown recognized page names return no results. These
constraints may reduce recall and require retention evaluation.

The earlier selected-source reconciliation changed five passage bodies and updated the
13 bundled source citations. Passage IDs and all 3,380 question attachments are
preserved; the five changed passages had no expansion questions. Its source
identity and retained adaptations are recorded in `docs/kilix/SNAPSHOT.json`.
The RC1 reconciliation then imports README and settings changes from Kilix
`311e4653891c1aea4191c1e9430164d7ba41d36a`, retaining those adaptations and
immutable link targets. The two changed source records cite document snapshot
`71d6db71abb159a1bb06255954c89096ac5fb29b`; all unchanged source records keep
their previous citations. There are now 502 passages. All 3,380 expansion
questions move only with the same document, heading and complete preserved
passage text or leading text; none are generated or removed. New or changed
facts require separate source-support and retrieval review.
Historical metrics above do not evaluate this analyzer
or establish release qualification. Results are cited source passages, without
generated answers, live-state access or semantic abstention guarantees.

`lookup-prepared.json.gz` precomputes the lookup representation and source-only
constraints. Its key hashes the actual source/index files, lookup/lexical/cache
implementation, schema and Python implementation tag. Runtime validates those
bytes and the compressed payload checksum; it never relies on timestamps or
executes cached code. A missing, corrupt or stale artifact triggers fresh in-memory
construction, including normal changed-document question/citation suppression.
Runtime does not write cache files. Prepare or rebuild explicitly after source,
index or implementation changes:

```sh
python3 -B -m help_llm.prepared
```

Preparation is deterministic for the same inputs and refuses inputs that change
during construction. `Lookup(use_cache=False)` exercises the uncached path for
verification. Cache-hit and fallback results must be identical. Cold process
startup and uncached construction cost are separate performance measurements.

Passages use the existing heading/paragraph cutter with a 450-word target; a single
paragraph longer than that stays whole (11 passages in this snapshot, enumerated in
`tests/test_lookup.py`; the original corpus had eight).

To reproduce the RC1 source/question manifests from the committed document snapshot:

```sh
python3 -B -m help_llm.refresh \
  --base e160c7a6aa1ca3f3a08eb9b7f7e2fa41753ddc1f \
  --documents-revision 71d6db71abb159a1bb06255954c89096ac5fb29b \
  --report ../refresh-report.json
```

The helper requires exact Git revisions, verifies document bytes against the
committed snapshot and refuses unlisted document changes. It writes only the two
index manifests and an explicit report outside the source checkout. After this
generic refresh, retain the base source record for each byte-unchanged document
to reproduce the RC1 citation policy, then rebuild the prepared cache. External
passages and unchanged source records are preserved. Commit documents first so
every source citation names an existing Git blob, then commit the refreshed index.
