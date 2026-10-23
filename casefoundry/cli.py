import argparse
import json
from pathlib import Path

from .generator import generate_suite
from .parser import parse_requirements
from .report import build_report
from .review import ReviewQueue
from .oracles import assess_oracles


def generate(prd_path: str, output: str, report_path: str, review_db: str) -> dict:
    requirements = parse_requirements(Path(prd_path).read_text(encoding="utf-8"))
    cases = generate_suite(requirements)
    Path(output).write_text(json.dumps([case.to_dict() for case in cases], indent=2) + "\n", encoding="utf-8")
    report = build_report(requirements, cases)
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    queue = ReviewQueue(review_db)
    report["queued_for_review"] = queue.add(cases)
    report["queued_for_oracle_review"] = queue.add_oracles(
        cases, assess_oracles(cases)
    )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="casefoundry")
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("generate")
    make.add_argument("prd")
    make.add_argument("--output", default="cases.json")
    make.add_argument("--report", default="coverage.json")
    make.add_argument("--review-db", default="reviews.db")
    args = parser.parse_args(argv)
    if args.command == "generate":
        print(json.dumps(generate(args.prd, args.output, args.report, args.review_db), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

