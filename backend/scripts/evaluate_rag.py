"""Measure how well knowledge retrieval finds the right document.

Runs every query in scripts/rag_eval_set.json against the real index (the
Ollama embedding model must be running) and reports:
  hit@1 / hit@4  share of queries whose expected document is ranked first /
                 within the top 4 (RAG_TOP_K)
  MRR            mean reciprocal rank (1.0 = always first, 0.5 = always second)
It also prints the similarity of the first correct chunk against the best
wrong one, which is what RAG_MIN_SCORE should sit between.

Each eval item names an acceptable answer in one of three ways:
  "expected": [paths]         any of these documents
  "expected_prefix": "path/"  any document under this folder
  "expected_technique": "T1110.003"  that MITRE ATT&CK technique's chunk

Usage:
    python scripts/evaluate_rag.py
    python scripts/evaluate_rag.py --verbose
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.services.rag.service import search_security_knowledge  # noqa: E402

EVAL_SET = Path(__file__).resolve().parent / "rag_eval_set.json"
SEARCH_DEPTH = 10


def is_correct(item: dict, result) -> bool:
    if "expected_technique" in item:
        return result.source.startswith("mitre_attack/") and (result.heading or "").startswith(item["expected_technique"] + " ")
    if "expected_prefix" in item:
        return result.source.startswith(item["expected_prefix"])
    return result.source in item["expected"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="Show the top results for every query.")
    args = parser.parse_args()
    settings = get_settings()
    items = json.loads(EVAL_SET.read_text(encoding="utf-8"))

    ranks: list[int | None] = []
    correct_scores: list[float] = []
    wrong_scores: list[float] = []
    for item in items:
        response = search_security_knowledge(item["query"], top_k=SEARCH_DEPTH, min_score=0.0)
        if not response.available:
            sys.exit(f"Knowledge search unavailable: {response.message}")
        rank = next((i + 1 for i, r in enumerate(response.results) if is_correct(item, r)), None)
        ranks.append(rank)
        if rank:
            correct_scores.append(response.results[rank - 1].score)
        wrong = [r.score for r in response.results if not is_correct(item, r)]
        if wrong:
            wrong_scores.append(max(wrong))

        mark = f"rank {rank}" if rank else "MISS  "
        print(f"[{mark:>7}] {item['query']}")
        if args.verbose or not rank or rank > settings.RAG_TOP_K:
            for i, r in enumerate(response.results[:5], start=1):
                where = f"{r.source}" + (f" p.{r.page}" if r.page else "") + (f" [{r.heading}]" if r.heading else "")
                print(f"           {i}. {r.score:.3f} {r.match:8s} {where[:110]}")

    n = len(items)
    hit1 = sum(1 for r in ranks if r == 1) / n
    hitk = sum(1 for r in ranks if r and r <= settings.RAG_TOP_K) / n
    mrr = sum(1 / r for r in ranks if r) / n
    print("\n" + "=" * 60)
    print(f"Queries: {n}   hit@1: {hit1:.0%}   hit@{settings.RAG_TOP_K}: {hitk:.0%}   MRR: {mrr:.3f}")
    if correct_scores and wrong_scores:
        print(
            f"Similarity of first correct chunk: min {min(correct_scores):.3f}, median {statistics.median(correct_scores):.3f}\n"
            f"Similarity of best wrong chunk:    min {min(wrong_scores):.3f}, median {statistics.median(wrong_scores):.3f}\n"
            f"Current RAG_MIN_SCORE: {settings.RAG_MIN_SCORE}  (correct chunks below it: "
            f"{sum(1 for s in correct_scores if s < settings.RAG_MIN_SCORE)})"
        )


if __name__ == "__main__":
    main()
