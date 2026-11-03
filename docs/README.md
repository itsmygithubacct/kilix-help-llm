# Help documentation corpus (MIT)

User documentation that kilix-help-llm answers questions from. Everything in
this directory is released under the repository's MIT licence (see
[../LICENSE](../LICENSE)).

| Directory | Contents | Provenance |
|---|---|---|
| [kilix/](kilix/) | The Kilix README, the automation guide (`AGENTS.md`), and the 0.2.2 help pages (`help/`, including `help/operations/`). | Written for Kilix by its author, itsmygithubacct. The same text also appears in the [kilix](https://github.com/itsmygithubacct/kilix) repository, which is GPLv3 because Kilix is a fork of kitty. The author releases these copies under MIT as well. The snapshot is taken from kilix commit `d5c5731` (0.2.2 help documentation); `AGENTS.md` is from kilix `e79615b`, which adds the agent-pane, log and safety sections; that revision is on the kilix branch `work/0.2.2-agent-docs`. Relative links to files elsewhere in the kilix repository now point to GitHub. |
| [kitty/](kitty/) | A task-oriented user guide to kitty 0.48.2 as shipped in Kilix. | Written independently under MIT by a clean-room process. See [kitty/README.md](kitty/README.md). kitty's own GPLv3 documentation is not included or quoted. |

These pages describe the software as of the versions named above. When
Kilix or kitty changes, update them with a new snapshot and do not edit them
in place without noting the source revision.

For the 0.2.3 Help candidate, six Kilix documents (README, AGENTS, the help
index, persistence, settings and storage) are refreshed from Kilix
`a77cac52799d0279a5ce3f74525fba40fc281dcd`. The managed-session, structured-action
and selected-session-controller guides from that same revision are also
included because the refreshed workflows depend on them. These author-written
copies continue the MIT convention above; this does not change the upstream
software's GPLv3 licence. The remaining Kilix pages and the independent kitty
guide retain their existing snapshots.

The related switcher operation page also corrects an obsolete toolkit pin to
the exact host-installer and Content selection. README corrections include the
matching version boundary, an obsolete internal anchor and an outdated skill
symlink count. These edits change documentation, not installed components.

[kilix/SNAPSHOT.json](kilix/SNAPSHOT.json) records each exact upstream path,
revision, original and bundled SHA-256, rewritten link, and editorial correction.
Links to bundled pages stay local. Other relative links point to immutable
upstream revisions, including the selected submodule revision where relevant.
The copied automation/persistence instructions are reconciled with that
revision's trusted-controller refusal boundary; ordinary selector-end CLI calls
do not acquire original-user authority. Source-version and optional-component
qualification limits remain in the documents. A refreshed Help corpus does not
install or qualify the described desktop components.

The subsequent retrieval repair corrects section hierarchy and names existing
workflow sections. It also brings the pinned model-verification paragraph and
raw foreground-process field into their focused help guides and clarifies
page/tab terminology. The original snapshot and every adaptation remain in
`kilix/SNAPSHOT.json`; these edits do not change desktop behavior.

The filtering successor reconciles the selected Kilix 0.2.2 source at
`9049a1a645e6a670a57ae9bc028ef0e6a0265ac6`. Eleven of the thirteen declared
upstream document blobs are unchanged. README adds local Ollama prerequisites
and resumable wizard acquisition; AGENTS adds explicit launch syntax, supported
Ask route labels, bounded live-log discovery and request-file wording. Their
exact upstream deltas are applied while retaining the prior documented local
reconciliations and immutable link targets. `kilix/SNAPSHOT.json` records this
comparison. Other historical corpus sources keep their stated versions.
