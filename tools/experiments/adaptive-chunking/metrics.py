from __future__ import annotations

from typing import Any


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _count_hits(text: str, terms: list[str]) -> int:
    lower = text.lower()
    return sum(lower.count(term.lower()) for term in terms if term)


def candidate_coverage(chunks: list[dict[str, Any]], candidate_terms: dict[str, list[str]]) -> dict[str, Any]:
    joined = "\n\n".join(str(chunk.get("text", "")) for chunk in chunks)
    by_candidate = {
        candidate: _contains_any(joined, aliases)
        for candidate, aliases in candidate_terms.items()
    }
    covered = sum(1 for value in by_candidate.values() if value)
    total = max(len(by_candidate), 1)
    return {
        "rate": round(covered / total, 6),
        "covered": covered,
        "total": len(by_candidate),
        "by_candidate": by_candidate,
    }


def expected_term_coverage(chunks: list[dict[str, Any]], expected_terms: list[str]) -> dict[str, Any]:
    joined = "\n\n".join(str(chunk.get("text", "")) for chunk in chunks)
    by_term = {term: term.lower() in joined.lower() for term in expected_terms}
    covered = sum(1 for value in by_term.values() if value)
    total = max(len(by_term), 1)
    return {"rate": round(covered / total, 6), "covered": covered, "total": len(by_term), "by_term": by_term}


def top_evidence(chunks: list[dict[str, Any]], terms: list[str], limit: int = 5) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for chunk in chunks:
        text = str(chunk.get("text", ""))
        score = _count_hits(text, terms)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], int(item[1].get("char_count", 0))))
    return [
        {
            "score": score,
            "strategy": chunk.get("strategy"),
            "chunk_index": chunk.get("chunk_index"),
            "char_count": chunk.get("char_count"),
            "text": str(chunk.get("text", ""))[:2500],
        }
        for score, chunk in scored[:limit]
    ]


def evaluate_chunks(
    chunks: list[dict[str, Any]],
    candidate_terms: dict[str, list[str]],
    expected_terms: list[str],
    noise_terms: list[str],
) -> dict[str, Any]:
    texts = [str(chunk.get("text", "")) for chunk in chunks]
    joined = "\n\n".join(texts)
    sizes = [len(text) for text in texts]
    candidate_terms_flat = [term for aliases in candidate_terms.values() for term in aliases]
    coverage = candidate_coverage(chunks, candidate_terms)
    expected = expected_term_coverage(chunks, expected_terms)
    noise_hits = _count_hits(joined, noise_terms)
    table_lines = sum(1 for line in joined.splitlines() if "|" in line)
    broken_table_lines = sum(1 for line in joined.splitlines() if line.strip() in {"| |", "| --- |"} or "cirtceleotohP" in line)

    return {
        "chunk_count": len(chunks),
        "avg_chunk_chars": round(sum(sizes) / max(len(sizes), 1), 2),
        "max_chunk_chars": max(sizes) if sizes else 0,
        "candidate_coverage": coverage,
        "expected_term_coverage": expected,
        "noise_hit_count": noise_hits,
        "table_fragment_ratio": round(broken_table_lines / max(table_lines, 1), 6),
        "top_evidence": top_evidence(chunks, candidate_terms_flat + expected_terms),
        "top_noise": top_evidence(chunks, noise_terms, limit=3),
    }


def score_metrics(metrics: dict[str, Any], max_chars: int) -> dict[str, Any]:
    candidate_rate = float(metrics["candidate_coverage"]["rate"])
    expected_rate = float(metrics["expected_term_coverage"]["rate"])
    noise = int(metrics["noise_hit_count"])
    table_ratio = float(metrics["table_fragment_ratio"])
    max_chunk_chars = int(metrics["max_chunk_chars"])
    oversize_penalty = 25 if max_chunk_chars > max_chars else 0
    normalized_noise = min(noise / 50, 1)
    score = candidate_rate * 40 + expected_rate * 25 - normalized_noise * 20 - table_ratio * 10 - oversize_penalty
    return {
        "score": round(score, 6),
        "rationale": {
            "candidate_rate": candidate_rate,
            "expected_rate": expected_rate,
            "normalized_noise": round(normalized_noise, 6),
            "table_fragment_ratio": table_ratio,
            "oversize_penalty": oversize_penalty,
        },
    }

