# kilix-help-llm

Document-trained help models for Kilix: answer questions with source references,
and select or rank relevant help topics. The intended inference host for prose
answers is `kilix-llm`; model selection belongs to `plebian-model-sizer`.

**Current state: candidate catalog only.** This repository contains seven
candidate families, exact upstream checkpoint revisions and file identities,
and the source licence. It has no trainer, inference service, sizer adapter,
model weights, or user documents yet.

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

## Integration boundaries

- Prose answers need a generative adapter and source references resolved from
  the supplied document collection.
- Topic selection/ranking needs a separately trained and calibrated scoring
  path. A custom decision head is not an ordinary text-generation GGUF adapter.
- Automatic selection must use `plebian-model-sizer` with profiles for the
  exact artifacts, task, backend, context, and workload. Training and inference
  require separate profiles; co-resident models require a combined profile.
- The inspected sizer has no executable fit engine yet. Automatic selection
  is unavailable until that provider and the necessary profiles are ready.
- The current `kilix-llm` launcher checks model files against its own small
  registry. Help-model registration/export and decision-serving integration
  remain implementation work.

## Files and user data

The source repository holds code, the candidate catalog, and public usage
information. Development research and scratch files stay outside it, under
`~/research/kilix-help-llm/`.

User documents, processed datasets, retrieval indexes, downloaded models,
adapters, checkpoints, evaluation results, and logs belong under
`~/.local/gpu_terminal/kilix-help-llm/`. The planned root follows
`GPU_TERMINAL_HOME/kilix-help-llm` when `GPU_TERMINAL_HOME` is set, matching the
host's convention. Download/library caches must also be directed there.
No user-data directories are created by reading this catalog.

## Licence

Original project material is MIT; see [LICENSE](LICENSE). Upstream models,
training documents, and derived artifacts retain their own applicable terms.
This repository includes no upstream implementation or model payloads.
