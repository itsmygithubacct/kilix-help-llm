# kilix-help-llm

Document-trained help models for Kilix: answer questions with source references,
and select or rank relevant help topics. The intended inference host for prose
answers is `kilix-llm`; model selection belongs to `plebian-model-sizer`.

**Current state: local CPU training prototype.** Prepare revision-bound document
datasets, retrieve source excerpts, size candidates, and train separate LoRA
adapters for cited answers and relevance ranking. The optional runtime can
reload those adapters, answer questions, rank excerpts and record evaluation
results. Resource selection is provisional; no candidate is quality-qualified.
The model catalog contains seven families with exact checkpoint identities.

## Prepare a document dataset

Python 3.11+ runs preparation, inspection, retrieval and sizing without model
dependencies. Import only an explicit allowlist of committed UTF-8 Markdown,
text or reStructuredText files. A full Git commit binds the source bytes;
uncommitted working-tree edits are not imported.

Keep the manifest and reviewed labels outside this repository. A manifest is
a JSON list of objects like:

```json
{"id": "panes", "path": "docs/help/panes.md", "split": "train"}
```

Assign whole document families to `train`, `dev`, `calibration` and `test`
before writing labels. All four splits need documents and labels. Keep related
documents and paraphrases in the same split; exact duplicate documents,
paragraphs across splits, and normalized duplicate questions are rejected.
Semantic near-duplicates still need human review. A labels file is a JSON list:

```json
{"id": "panes-1", "document": "panes", "question": "How do I list panes?", "answer": "Run `kilix ls --panes` to list panes."}
```

The answer must be a verbatim excerpt of exactly one paragraph in that document.
Use the actual wording of your source: the example above is a format example.
The importer adds source IDs, line numbers, hashes and splits automatically.
Raw documents alone are not reviewed question/answer labels. Current datasets
use extractive labels; broader answers and unanswerable examples need a later
labeling/evaluation protocol.

```sh
./kilix-help-llm prepare --repo /path/to/kilix --revision FULL_COMMIT_SHA \
  --manifest /path/to/manifest.json --labels /path/to/labels.json --name kilix-022-r1
./kilix-help-llm inspect --dataset kilix-022-r1
./kilix-help-llm search --dataset kilix-022-r1 'How do I list panes?'
./kilix-help-llm plan --dataset kilix-022-r1
```

Names use lowercase letters, digits, underscores and hyphens. Dataset files are
immutable: choose a new name after correcting a document or label. Import
rejects symlink blobs, path traversal, oversized inputs and unsupported labels.
The retrieval baseline is deterministic BM25 and requires no embedding download.

## Install the optional runtime and train

The CPU environment uses Python 3.12 and a committed dependency lock. With
`uv` installed, run from this checkout:

```sh
HELP_HOME="${GPU_TERMINAL_HOME:-$HOME/.local/gpu_terminal}/kilix-help-llm"
umask 077
UV_CACHE_DIR="$HELP_HOME/cache/uv" \
UV_PYTHON_INSTALL_DIR="$HELP_HOME/runtimes/python" \
UV_PROJECT_ENVIRONMENT="$HELP_HOME/runtimes/cpu" \
  uv sync --project runtime --locked --python 3.12.8

./kilix-help-llm fetch --dataset kilix-022-r1
./kilix-help-llm train --dataset kilix-022-r1 --task answer --name answer-r1 --steps 32
./kilix-help-llm train --dataset kilix-022-r1 --task rank --name rank-r1 --steps 32
./kilix-help-llm ask --run answer-r1 'How do I list panes?'
./kilix-help-llm rank --run rank-r1 'How do I list panes?'
./kilix-help-llm evaluate --run answer-r1 --split dev
./kilix-help-llm evaluate --run rank-r1 --split dev
```

`fetch` explicitly downloads the catalog-pinned generation and base checkpoints
and tokenizer files. It verifies config/weight hashes against the catalog and
records all downloaded file hashes. Training and inference are local-only and
recheck those hashes; they never acquire missing models automatically. Runtime
commands find the private environment automatically. No hosted training is used.

`plan`, `fetch`, `train` and inference consult live shared sizing. The initial
recipe uses CPU FP32, batch one, independent examples, gradient checkpointing,
all-linear LoRA, AdamW, context 384 and rank four. `--context` accepts 128-512;
`--lora-rank` accepts 1-64. Training is bounded by `--steps` (default 32, maximum
10000). Oversized examples fail instead of silently truncating their evidence
or answers. `--candidate` requests a particular resource-eligible checkpoint.
Only the dense-attention families are enabled in this runtime; hybrid Qwen3.5
families remain sizing candidates until their training path is verified.

Answer training masks prompt tokens and learns excerpt-grounded completions
with source citations. Ranking trains a separate base-model adapter and a
two-output relevance head on positive paragraphs and BM25 hard negatives.
The ranker reranks the top five BM25 results by default (`--limit` accepts 1-20).
Its scores are **uncalibrated**, not acceptance probabilities. The generation
command currently uses the BM25 top result; it does not load both models at once.
Query results include the frozen document revision and dataset digest so source
paths and line numbers can be resolved against the correct document version.
This decision path is inspired by small-model decision training, but contains
no copied reference implementation.

Training sees only the training split and reports development loss. Calibration
and test sets are used only when explicitly named in `evaluate`. Reports compare
retrieval recall with learned ranking top-one accuracy/MRR, or report answer
citation validity and extractive reference matching. Those narrow checks do not
prove semantic correctness or sufficient quality. Answers with missing or
unknown citation IDs are returned as unvalidated drafts with `abstained: true`;
a valid ID alone does not establish factual support. No output executes commands.

Each run records its dataset/checkpoint identity, training recipe, runtime
versions, code hash, losses, elapsed time, process peak RSS and artifact hashes.
Adapters and ranking heads use safetensors. Run names cannot overwrite earlier
results; failed attempts retain their plan and a failure marker. Optimizer resume,
confidence calibration, a larger held-out benchmark and GGUF export remain work.

Run `make check` for the stdlib checks and `make check-runtime` for actual tiny
local-model backprop, frozen-weight preservation and adapter reload tests. The
tests do not download model weights. Tiny-model tests establish mechanics, not
the quality of a catalog candidate.

## Candidate models

| Family | Evaluation role | Generation checkpoint | Decision-training checkpoint |
| --- | --- | --- | --- |
| Qwen3 0.6B | Small smoke baseline | [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) | [Qwen3-0.6B-Base](https://huggingface.co/Qwen/Qwen3-0.6B-Base) |
| Qwen3 1.7B | First main candidate | [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) | [Qwen3-1.7B-Base](https://huggingface.co/Qwen/Qwen3-1.7B-Base) |
| Qwen3.5 0.8B | Compact challenger | [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) | [Qwen3.5-0.8B-Base](https://huggingface.co/Qwen/Qwen3.5-0.8B-Base) |
| Qwen3.5 2B | Main challenger | [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | [Qwen3.5-2B-Base](https://huggingface.co/Qwen/Qwen3.5-2B-Base) |
| Qwen3.5 4B | Larger resource budget | [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | [Qwen3.5-4B-Base](https://huggingface.co/Qwen/Qwen3.5-4B-Base) |
| SmolLM2 1.7B | Independent control | [SmolLM2-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) | [SmolLM2-1.7B](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B) |
| SmolLM3 3B | Alternative family | [SmolLM3-3B](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) | [SmolLM3-3B-Base](https://huggingface.co/HuggingFaceTB/SmolLM3-3B-Base) |

[candidates.json](candidates.json) is the machine-readable catalog. Each
checkpoint records its upstream revision, config/model-card digest, and
safetensors file sizes and hashes reported by the upstream host. No weight
payload was downloaded to establish this catalog. All 14 upstream checkpoints
declare Apache-2.0; full redistribution review remains separate from that
metadata. The SmolLM checkpoints declare the licence in model-card metadata
without a standalone licence file in the inspected repository revision.

A candidate's role is an evaluation order, not a measured quality or fit
ranking. Checkpoint file bytes are download/storage sizes, not peak training
RAM, VRAM, or inference memory. Every local fit/quality verdict is unmeasured.

## Size the candidates

```sh
./kilix-help-llm size
./kilix-help-llm size --task both --phase both --context 2048 --batch 1 --json
./kilix-help-llm size --train-backend cpu --infer-backend cpu --co-resident
./kilix-help-llm size --help
```

The command finds an installed `plebian-model-sizer` or its source launcher in
the sibling `kilix-system-monitor` checkout. Use `--sizer /path/to/executable`
or `PLEBIAN_MODEL_SIZER` to select a provider explicitly. Python 3.11+ is needed.
`make check` verifies the catalog and delegation boundary.

The raw `size` defaults assess both tasks, sequentially, with separate training and inference
budgets, rank-16 all-linear LoRA, checkpointing, and 128 scoring-head outputs.
Q4 estimates apply only to answer inference; ranking uses an unquantized model
with a separate scoring head. `--co-resident` sums inference memory for both
tasks. `--document-bytes N` adds a preprocessing allowance; include the corpus
size when planning a training run. The prototype's `plan` and runtime commands
set their exact recipe explicitly: FP32, two head outputs and the requested
context and LoRA rank. Raw `size` defaults are not that runtime's admission plan.

The provider checks current RAM, cgroup limits, observed CUDA free memory, and
the user-data filesystem. JSON includes checkpoint identities, assumptions,
memory breakdowns and failed checks. `provisional_candidate` identifies the
smallest candidate within the estimated budgets; `selected_model` remains null
until task quality and runtime support are established. An empty shortlist is a
valid report, so consumers must inspect the verdict rather than exit 0 alone.
No weights or document data are required to run sizing, and the command creates
no user state. Missing provider executables exit 69.

## Integration boundaries

- Prose answers use a generative adapter and references resolved from the frozen
  document collection. Grounding and command correctness need further evaluation.
- Topic ranking uses a separate trained scoring path; confidence calibration
  remains pending. A custom head is not an ordinary text-generation GGUF adapter.
- Automatic selection must use `plebian-model-sizer` with profiles for the
  exact artifacts, task, backend, context, and workload. Training and inference
  require separate profiles; co-resident models require a combined profile.
- The provider now produces provisional resource shortlists. Measured profiles,
  task-quality evaluation and runtime compatibility are still required for
  automatic model selection and execution admission.
- The current `kilix-llm` launcher checks model files against its own small
  registry. Help-model registration/export and decision-serving integration
  remain implementation work.

## Files and user data

The source repository holds code, the candidate catalog, and public usage
information. Development research and scratch files stay outside it, under
`~/research/kilix-help-llm/`.

User documents, processed datasets, retrieval indexes, downloaded models,
adapters, checkpoints, evaluation results, and logs belong under
`~/.local/gpu_terminal/kilix-help-llm/`. The sizing root follows
`GPU_TERMINAL_HOME/kilix-help-llm` when `GPU_TERMINAL_HOME` is set, matching the
host's convention. Download/library caches must also be directed there.
No user-data directories are created by reading this catalog.

## Licence

Original project material is MIT; see [LICENSE](LICENSE). Upstream models,
training documents, and derived artifacts retain their own applicable terms.
This repository includes no upstream implementation or model payloads.
