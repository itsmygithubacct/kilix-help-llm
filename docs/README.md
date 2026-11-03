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

## 0.2.2 release-status refresh

The release-status sections in `kilix/README.md`, `kilix/help/README.md` and
`kilix/help/release.md` were updated on November 3, 2026 against Kilix commit
`216a75840fbe446b70a97287654a76fdae41689f` and the published Plebian-OS 0.2.2
Linux release. This is a targeted status correction, not a replacement of the
older command snapshot above. Existing model, Windows, ARM64 and hardware
qualification limits remain in place.

The lookup index retains the original hashes for these edited corpus files,
so it searches the new text without attaching questions written for the older
passages. No training dataset, adapter or evaluation result was regenerated.
