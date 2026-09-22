# kilix-help-llm

Document-trained help models for Kilix: answer questions with source references,
and select or rank relevant help topics. The intended inference host for prose
answers is `kilix-llm`; model selection belongs to `plebian-model-sizer`.

**Current state: candidate catalog and development sizing command.** This
repository contains seven candidate families with exact upstream checkpoint
identities and architecture metadata. `kilix-help-llm size` delegates training
and inference estimates to `plebian-model-sizer`. Training, inference serving,
and measured task evaluation remain to be implemented.

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

Defaults assess both tasks, sequentially, with separate training and inference
budgets, rank-16 all-linear LoRA, checkpointing, and 128 scoring-head outputs.
Q4 estimates apply only to answer inference; ranking uses an unquantized model
with a separate scoring head. `--co-resident` sums inference memory for both
tasks. `--document-bytes N` adds a preprocessing allowance; include the corpus
size when planning a training run. These are planning recipes, not implemented
trainers or tested runtime exports.

The provider checks current RAM, cgroup limits, observed CUDA free memory, and
the user-data filesystem. JSON includes checkpoint identities, assumptions,
memory breakdowns and failed checks. `provisional_candidate` identifies the
smallest candidate within the estimated budgets; `selected_model` remains null
until task quality and runtime support are established. An empty shortlist is a
valid report, so consumers must inspect the verdict rather than exit 0 alone.
No weights or document data are required to run sizing, and the command creates
no user state. Missing provider executables exit 69.

## Integration boundaries

- Prose answers need a generative adapter and source references resolved from
  the supplied document collection.
- Topic selection/ranking needs a separately trained and calibrated scoring
  path. A custom decision head is not an ordinary text-generation GGUF adapter.
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
