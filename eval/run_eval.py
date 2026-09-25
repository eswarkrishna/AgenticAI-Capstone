"""Phase 7 harness: parse + score every labelled pair, no HITL resume.

Writes eval/results/report.json and eval/results/report.md.
Prints accuracy, FPR, latency p50/p95, and audit completeness.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from resume_screener.eval.harness import format_stdout, run_eval  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the 30 labelled eval pairs.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Score only the first N cases (debug). Default is the full set.",
    )
    args = parser.parse_args(argv)
    report = run_eval(limit=args.limit)
    print(format_stdout(report))
    print("wrote eval/results/report.json and eval/results/report.md")
    gates = report["gates"]
    failed = [name for name, ok in gates.items() if not ok]
    if failed:
        print("gates failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
