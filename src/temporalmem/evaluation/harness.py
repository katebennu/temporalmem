from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from pathlib import Path

import anthropic

from ..agent.memory_agent import MemoryAgent
from ..config import settings
from ..graph.client import GraphClient
from ..ingest import Ingestor
from ..sources.longmemeval import LongMemEvalSource, Question

JUDGE_PROMPT = """You are grading a memory system's answer against a gold answer.

Question ({question_type}): {question}
Gold answer: {gold}
System's answer: {hypothesis}

The system's answer is correct if it conveys the same information as the gold answer
(exact wording does not matter). If the gold answer indicates the information was never
mentioned, the system is correct only if it clearly states it does not know or that the
history contains no such information.

Reply with exactly one word: correct or incorrect."""


def judge(
    client: anthropic.Anthropic,
    question: Question,
    hypothesis: str,
    model: str = settings.judge_model,
) -> bool:
    response = client.messages.create(
        model=model,
        max_tokens=16,
        messages=[
            {
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    question_type=question.question_type,
                    question=question.question,
                    gold=question.answer,
                    hypothesis=hypothesis,
                ),
            }
        ],
    )
    verdict = "".join(block.text for block in response.content if block.type == "text")
    return verdict.strip().lower().startswith("correct")


def stratified_sample(questions: list[Question], n: int, seed: int = 42) -> list[Question]:
    """Round-robin sample across question types, deterministic for a given seed."""
    by_type: dict[str, list[Question]] = defaultdict(list)
    for question in questions:
        by_type[question.question_type].append(question)
    rng = random.Random(seed)
    for pool in by_type.values():
        rng.shuffle(pool)
    types = sorted(by_type)
    sampled: list[Question] = []
    index = 0
    while len(sampled) < n and any(by_type[qtype] for qtype in types):
        pool = by_type[types[index % len(types)]]
        if pool:
            sampled.append(pool.pop())
        index += 1
    return sampled


class EvalHarness:
    """Runs LongMemEval questions end-to-end and scores them with an LLM judge.

    Results are written incrementally so runs are resumable; already-answered
    question ids are skipped on re-run.
    """

    def __init__(
        self,
        dataset_path: str | Path,
        graph: GraphClient,
        out_path: str | Path = "results/run.json",
        client: anthropic.Anthropic | None = None,
    ):
        self.dataset_path = Path(dataset_path)
        self.graph = graph
        self.out_path = Path(out_path)
        self.client = client or anthropic.Anthropic()

    def run(
        self,
        limit: int | None = None,
        sample: int | None = None,
        seed: int = 42,
        strategy: str | None = None,
        question_ids: set[str] | None = None,
        skip_ingest: bool = False,
        log=print,
    ) -> list[dict]:
        source = LongMemEvalSource(self.dataset_path, question_ids)
        questions = list(source.questions())
        if sample is not None:
            questions = stratified_sample(questions, sample, seed)
        elif limit is not None:
            questions = questions[:limit]
        strategy = strategy or settings.invalidation_strategy

        results = self._load_results()
        done = {record["question_id"] for record in results}

        for question in questions:
            if question.question_id in done:
                log(f"skip (already answered): {question.question_id}")
                continue
            if not skip_ingest:
                haystack = LongMemEvalSource(self.dataset_path, {question.question_id})
                Ingestor(self.graph, strategy=strategy).ingest(haystack, log=log)
            agent = MemoryAgent(self.graph, client=self.client)
            started = time.monotonic()
            hypothesis = agent.answer(question.question, question.question_date)
            results.append(
                {
                    "question_id": question.question_id,
                    "question_type": question.question_type,
                    "question": question.question,
                    "gold": question.answer,
                    "hypothesis": hypothesis,
                    "strategy": strategy,
                    "latency_s": round(time.monotonic() - started, 2),
                }
            )
            self._save_results(results)
            log(f"answered {question.question_id}: {hypothesis[:80]!r}")
        return results

    def score(self, log=print) -> dict:
        results = self._load_results()
        per_type: dict[str, list[bool]] = defaultdict(list)
        for record in results:
            if "correct" not in record:
                question = Question(
                    question_id=record["question_id"],
                    question_type=record["question_type"],
                    question=record["question"],
                    answer=record["gold"],
                    question_date="1970-01-01T00:00:00",
                )
                record["correct"] = judge(self.client, question, record["hypothesis"])
                self._save_results(results)
            per_type[record["question_type"]].append(record["correct"])

        report = {
            "overall": _accuracy([verdict for verdicts in per_type.values() for verdict in verdicts]),
            "by_type": {qtype: _accuracy(verdicts) for qtype, verdicts in sorted(per_type.items())},
            "n": len(results),
        }
        log(json.dumps(report, indent=2))
        return report

    def _load_results(self) -> list[dict]:
        if self.out_path.exists():
            return json.loads(self.out_path.read_text())
        return []

    def _save_results(self, results: list[dict]) -> None:
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_path.write_text(json.dumps(results, indent=2))


def _accuracy(verdicts: list[bool]) -> float | None:
    if not verdicts:
        return None
    return round(sum(verdicts) / len(verdicts), 3)


def compare_results(paths: list[str | Path], log=print) -> dict:
    """Side-by-side per-type accuracy across scored results files (one per strategy arm)."""
    columns: dict[str, dict[str, float | None]] = {}
    for path in paths:
        records = json.loads(Path(path).read_text())
        unjudged = [record for record in records if "correct" not in record]
        if unjudged:
            log(f"warning: {len(unjudged)} unjudged records in {path} — run score first; skipping them")
        label = records[0].get("strategy", Path(path).stem) if records else Path(path).stem
        per_type: dict[str, list[bool]] = defaultdict(list)
        for record in records:
            if "correct" in record:
                per_type[record["question_type"]].append(record["correct"])
        column = {qtype: _accuracy(verdicts) for qtype, verdicts in per_type.items()}
        column["overall"] = _accuracy([v for verdicts in per_type.values() for v in verdicts])
        columns[label] = column

    rows = sorted({qtype for column in columns.values() for qtype in column} - {"overall"})
    rows.append("overall")
    width = max((len(row) for row in rows), default=8) + 2
    header = " " * width + "  ".join(f"{label:>12}" for label in columns)
    log(header)
    for row in rows:
        cells = "  ".join(
            f"{columns[label].get(row):>12}" if columns[label].get(row) is not None else f"{'—':>12}"
            for label in columns
        )
        log(f"{row:<{width}}{cells}")
    return columns
