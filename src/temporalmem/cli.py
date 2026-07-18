from __future__ import annotations

import argparse
from datetime import datetime


def main() -> None:
    parser = argparse.ArgumentParser(prog="temporalmem", description="Temporal knowledge-graph memory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup-db", help="Create Neo4j constraints and indexes (idempotent)")

    ingest = sub.add_parser("ingest", help="Ingest an episode source into the graph")
    ingest.add_argument(
        "--source",
        choices=["longmemeval", "claude-code"],
        default="longmemeval",
        help="Episode source type (default: longmemeval)",
    )
    ingest.add_argument(
        "--data",
        required=True,
        help="LongMemEval JSON file, or a Claude Code transcript directory / .jsonl session file",
    )
    ingest.add_argument("--question-id", action="append", help="Limit to specific question id(s) (longmemeval only)")
    ingest.add_argument("--dry-run", action="store_true", help="Print extractions without writing")

    search = sub.add_parser("search", help="Query the memory graph directly")
    search.add_argument("--query", required=True)
    search.add_argument("--as-of", help="ISO date for point-in-time retrieval")
    search.add_argument("--limit", type=int, default=10)

    ask = sub.add_parser("ask", help="Ask the memory agent a question")
    ask.add_argument("--question", required=True)
    ask.add_argument("--date", help="ISO question date for temporal reasoning")

    run = sub.add_parser("eval", help="Run the LongMemEval harness")
    run.add_argument("--data", required=True)
    run.add_argument("--limit", type=int, help="First N questions (file order)")
    run.add_argument("--sample", type=int, help="Stratified sample of N questions across question types")
    run.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    run.add_argument(
        "--strategy",
        choices=["none", "functional", "llm"],
        help="Invalidation strategy for ingestion (default: config)",
    )
    run.add_argument("--question-id", action="append")
    run.add_argument("--out", default="results/run.json")
    run.add_argument("--skip-ingest", action="store_true")

    score = sub.add_parser("score", help="Judge and report a results file")
    score.add_argument("--data", required=True)
    score.add_argument("--out", default="results/run.json")

    compare = sub.add_parser("compare", help="Side-by-side accuracy across scored results files")
    compare.add_argument("--results", nargs="+", required=True, help="Two or more scored results files")

    sub.add_parser("wipe-db", help="Delete all graph data (keeps indexes) — needed between ablation arms")

    args = parser.parse_args()
    handler = {
        "setup-db": _setup_db,
        "ingest": _ingest,
        "search": _search,
        "ask": _ask,
        "eval": _eval,
        "score": _score,
        "compare": _compare,
        "wipe-db": _wipe_db,
    }[args.command]
    handler(args)


def _setup_db(args) -> None:
    from .graph import GraphClient, setup_schema

    with GraphClient() as graph:
        setup_schema(graph)
    print("schema ready")


def _ingest(args) -> None:
    from .graph import GraphClient
    from .ingest import Ingestor

    source = build_source(args.source, args.data, args.question_id)
    with GraphClient() as graph:
        count = Ingestor(graph).ingest(source, dry_run=args.dry_run)
    print(f"processed {count} episodes")


def build_source(source_type: str, data: str, question_ids: list[str] | None):
    if source_type == "claude-code":
        if question_ids:
            raise SystemExit("--question-id only applies to --source longmemeval")
        from .sources.claudecode import ClaudeCodeSource

        return ClaudeCodeSource(data)
    from .sources import LongMemEvalSource

    return LongMemEvalSource(data, set(question_ids) if question_ids else None)


def _search(args) -> None:
    from .graph import GraphClient
    from .retrieval import MemorySearch

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else None
    with GraphClient() as graph:
        results = MemorySearch(graph).search(args.query, as_of=as_of, limit=args.limit)
    for result in results:
        print(f"[{result.score:.4f}] ({result.via}) {result.fact}")
        print(f"          valid {result.valid_at} to {result.invalid_at or 'present'}")


def _ask(args) -> None:
    from .agent import MemoryAgent
    from .graph import GraphClient

    date = datetime.fromisoformat(args.date) if args.date else None
    with GraphClient() as graph:
        print(MemoryAgent(graph).answer(args.question, question_date=date))


def _eval(args) -> None:
    from .evaluation import EvalHarness
    from .graph import GraphClient

    question_ids = set(args.question_id) if args.question_id else None
    with GraphClient() as graph:
        harness = EvalHarness(args.data, graph, out_path=args.out)
        harness.run(
            limit=args.limit,
            sample=args.sample,
            seed=args.seed,
            strategy=args.strategy,
            question_ids=question_ids,
            skip_ingest=args.skip_ingest,
        )


def _score(args) -> None:
    from .evaluation import EvalHarness
    from .graph import GraphClient

    with GraphClient() as graph:
        EvalHarness(args.data, graph, out_path=args.out).score()


def _compare(args) -> None:
    from .evaluation.harness import compare_results

    compare_results(args.results)


def _wipe_db(args) -> None:
    from .graph import GraphClient

    with GraphClient() as graph:
        counts = graph.run("MATCH (n) RETURN count(n) AS n")[0]
        graph.run("MATCH (n) DETACH DELETE n")
    print(f"wiped {counts['n']} nodes (indexes kept)")


if __name__ == "__main__":
    main()
