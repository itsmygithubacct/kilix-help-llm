"""The basic commands need only Python's standard library."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from .data import SOURCE, SPLITS, load_dataset, prepare, read_json, retrieve, state_root
from .sizing import provider, recommend


def parser():
    root = argparse.ArgumentParser(description="Document-trained answers and topic ranking for Kilix")
    commands = root.add_subparsers(dest="command", required=True)
    size = commands.add_parser("size", add_help=False, help="delegate to the shared model sizer")
    size.add_argument("--sizer")
    ingest = commands.add_parser("prepare", help="freeze reviewed Git documents and extractive labels")
    for name in ("repo", "revision", "manifest", "labels", "name"):
        ingest.add_argument("--" + name, required=True)
    inspect = commands.add_parser("inspect", help="show dataset identities and split counts")
    inspect.add_argument("--dataset", required=True)
    search = commands.add_parser("search", help="BM25 retrieval baseline; no model needed")
    search.add_argument("--dataset", required=True)
    search.add_argument("question")
    for name in ("review-template", "review-import"):
        command = commands.add_parser(name, help="prepare or import manual factual review of saved v2 outputs")
        command.add_argument("--evaluation", required=True)
        if name == "review-import":
            command.add_argument("--ratings", required=True)
    for name in ("plan", "fetch", "train", "baseline"):
        command = commands.add_parser(name)
        command.add_argument("--dataset", required=True)
        command.add_argument("--candidate")
        command.add_argument("--sizer")
        command.add_argument("--context", type=int, default=384)
        command.add_argument("--lora-rank", type=int, default=4)
        if name == "baseline":
            command.add_argument("--split", choices=["dev", "calibration", "test"], default="dev")
        command.add_argument("--task", choices=["answer", "rank"] if name == "train" else ["answer", "rank", "both"],
                             required=name == "train", default="both" if name != "train" else None)
        if name == "train":
            command.add_argument("--name", required=True)
            command.add_argument("--steps", type=int, default=32)
            command.add_argument("--learning-rate", type=float, default=.0002)
            command.add_argument("--eval-every", type=int, default=16)
            command.add_argument("--patience", type=int, default=3)
    for name in ("ask", "rank", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--run", required=True)
        command.add_argument("--sizer")
        if name == "evaluate":
            command.add_argument("--split", choices=["dev", "calibration", "test"], default="dev")
        else:
            command.add_argument("question")
        if name == "ask":
            command.add_argument("--max-new-tokens", type=int, default=96)
        if name == "rank":
            command.add_argument("--limit", type=int, default=5)
    return root


def runtime_python():
    python = state_root() / "runtimes/cpu/bin/python"
    if Path(sys.prefix).resolve() != python.parent.parent.resolve():
        if not python.is_file():
            raise ValueError("CPU training runtime is not installed; see README runtime setup")
        os.execv(str(python), [str(python), str(SOURCE / "kilix-help-llm"), *sys.argv[1:]])


def main(argv=None):
    root = parser()
    args, rest = root.parse_known_args(argv)
    os.umask(0o077)
    try:
        if args.command == "size":
            executable = provider(args.sizer)
            os.execv(executable, [executable, "recommend", "help-llm", "--catalog", str(SOURCE / "candidates.json"), *rest])
        if rest:
            root.error("unrecognized arguments: " + " ".join(rest))
        if args.command in {"fetch", "train", "ask", "rank", "evaluate", "baseline"}:
            runtime_python()
            from . import runtime
        if args.command == "prepare":
            bundle = prepare(args.repo, args.revision, read_json(args.manifest), read_json(args.labels), args.name)
            result = {"dataset": args.name, "sha256": bundle["sha256"], "documents": len(bundle["data"]["documents"]),
                      "examples": len(bundle["data"]["examples"])}
        elif args.command == "inspect":
            bundle = load_dataset(args.dataset)
            result = {"dataset": args.dataset, "sha256": bundle["sha256"], "revision": bundle["data"]["revision"],
                      "splits": {s: {"documents": sum(d["split"] == s for d in bundle["data"]["documents"]),
                                      "examples": sum(r["split"] == s for r in bundle["data"]["examples"])} for s in sorted(SPLITS)}}
        elif args.command == "search":
            if not args.question.strip() or len(args.question) > 2000:
                raise ValueError("question must contain 1-2000 characters")
            result = retrieve(load_dataset(args.dataset)["data"], args.question)
        elif args.command in {"review-template", "review-import"}:
            from .data import private_dir, write_json
            from .evaluation import review_template, reviewed_metrics
            root_dir = state_root() / "evaluations"
            evaluation = Path(args.evaluation).absolute()
            if evaluation.is_symlink() or evaluation.parent.resolve() != root_dir.resolve():
                raise ValueError("evaluation must be a private saved evaluation file")
            saved = read_json(evaluation)
            if saved.get("schema") != "kilix.help-llm.evaluation/v2" or saved.get("task") != "answer":
                raise ValueError("manual answer review requires a v2 answer evaluation")
            if args.command == "review-template":
                result = review_template(saved)
                output = private_dir(root_dir) / f"review-template-{time.time_ns()}.json"
            else:
                result = reviewed_metrics(saved, read_json(args.ratings))
                output = private_dir(root_dir) / f"review-{time.time_ns()}.json"
            write_json(output, result)
            result = {"saved_to": str(output), "systems": list(result.get("metrics", {})),
                      "evaluation_sha256": result["evaluation_sha256"]}
        elif args.command in {"plan", "fetch"}:
            result = recommend(load_dataset(args.dataset), args.context, args.lora_rank, args.sizer, args.candidate, args.task)
            if args.command == "fetch":
                result = {"downloaded": runtime.fetch(result), "quality": "unmeasured"}
        elif args.command == "train":
            result = runtime.train(args.dataset, args.name, args.task, args.context, args.lora_rank,
                                   args.steps, args.learning_rate, args.sizer, args.candidate,
                                   args.eval_every, args.patience)
        elif args.command in {"ask", "rank"}:
            result = runtime.query(args.run, "answer" if args.command == "ask" else "rank", args.question, args.sizer,
                                   limit=getattr(args, "limit", 5), max_new_tokens=getattr(args, "max_new_tokens", 96))
        elif args.command == "evaluate":
            result = runtime.evaluate(args.run, args.split, args.sizer)
        elif args.command == "baseline":
            result = runtime.baseline(args.dataset, args.candidate, args.context, args.split, args.sizer)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except FileNotFoundError:
        print("kilix-help-llm: required file or executable is missing", file=sys.stderr)
        return 69
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"kilix-help-llm: {error}", file=sys.stderr)
        return 2
