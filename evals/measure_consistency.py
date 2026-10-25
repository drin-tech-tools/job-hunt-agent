#!/usr/bin/env python3
"""Measure score_fit consistency across repeated runs on synthetic pairs.

All fixtures in evals/fixtures/pairs.json are SYNTHETIC and clearly labeled.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from app.models.schemas import JobPosting  # noqa: E402
from app.tools.scoring import score_fit  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "pairs.json"
REPEATS = 5


def main() -> int:
    pairs = json.loads(FIXTURES.read_text())
    print(f"Evaluating {len(pairs)} SYNTHETIC resume/posting pairs × {REPEATS} repeats\n")

    failures = 0
    for pair in pairs:
        scores: list[int] = []
        job = JobPosting.model_validate(pair["job"])
        for _ in range(REPEATS):
            fit = score_fit(pair["resume"], job)
            scores.append(fit.score)

        mean = statistics.mean(scores)
        stdev = statistics.pstdev(scores)
        unique = sorted(set(scores))
        ok = stdev == 0  # heuristic scorer must be deterministic

        emin = pair.get("expected_score_min")
        emax = pair.get("expected_score_max")
        band_ok = True
        if emin is not None and mean < emin:
            band_ok = False
        if emax is not None and mean > emax:
            band_ok = False

        status = "OK" if ok and band_ok else "FAIL"
        if status == "FAIL":
            failures += 1

        print(
            f"[{status}] {pair['id']}: scores={unique} mean={mean:.1f} stdev={stdev:.3f} "
            f"label={pair.get('label')}"
        )

    print()
    if failures:
        print(f"FAILED {failures}/{len(pairs)} pairs")
        return 1
    print(f"PASSED {len(pairs)}/{len(pairs)} — perfect consistency (stdev=0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
