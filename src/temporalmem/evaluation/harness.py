from __future__ import annotations

import json
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
        question_ids: set[str] | None = None,
        skip_ingest: bool = False,
        log=print,
    ) -> list[dict]:
        source = LongMemEvalSource(self.dataset_path, question_ids)
        questions = list(source.questions())
        if limit is not None:
            questions = questions[:limit]

        results = self._load_results()
        done = {record["question_id"] for record in results}

        for question in questions:
            if question.question_id in done:
                log(f"skip (already answered): {question.question_id}")
                continue
            if not skip_ingest:
                haystack = LongMemEvalSource(self.dataset_path, {question.question_id})
                Ingestor(self.graph).ingest(haystack, log=log)
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
