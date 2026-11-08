import argparse
import json
from pathlib import Path

from .generator import generate_suite
from .parser import parse_requirements
from .report import build_report
from .review import ReviewQueue
from .oracles import assess_oracles
from .lineage import build_manifest, regenerate_impacted


def generate(prd_path: str, output: str, report_path: str, review_db: str,
             manifest_path: str | None = None) -> dict:
    requirements = parse_requirements(Path(prd_path).read_text(encoding="utf-8"))
    cases = generate_suite(requirements)
    Path(output).write_text(json.dumps([case.to_dict() for case in cases], indent=2) + "\n", encoding="utf-8")
    manifest_path = manifest_path or str(Path(output).with_suffix(".manifest.json"))
    Path(manifest_path).write_text(json.dumps(build_manifest(requirements, cases), indent=2) + "\n", encoding="utf-8")
    report = build_report(requirements, cases)
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    queue = ReviewQueue(review_db)
    report["queued_for_review"] = queue.add(cases)
    report["queued_for_oracle_review"] = queue.add_oracles(
        cases, assess_oracles(cases)
    )
    return report


def regenerate(prd_path: str, previous_manifest: str, output: str,
               manifest_path: str, audit_path: str, review_db: str) -> dict:
    requirements = parse_requirements(Path(prd_path).read_text(encoding="utf-8"))
    previous = json.loads(Path(previous_manifest).read_text(encoding="utf-8"))
    cases, manifest, audit, added = regenerate_impacted(previous, requirements)
    Path(output).write_text(json.dumps([case.to_dict() for case in cases], indent=2) + "\n", encoding="utf-8")
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    queue = ReviewQueue(review_db)
    audit["queued_added_cases"] = queue.add(added)
    if added:
        added_ids = {case.id for case in added}
        assessments = [item for item in assess_oracles(cases) if item.case_id in added_ids]
        audit["queued_added_oracles"] = queue.add_oracles(added, assessments)
    else:
        audit["queued_added_oracles"] = 0
    audit["audit_digest"] = __import__("hashlib").sha256(
        json.dumps({key: value for key, value in audit.items() if key != "audit_digest"},
                   sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    Path(audit_path).write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="casefoundry")
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("generate")
    make.add_argument("prd")
    make.add_argument("--output", default="cases.json")
    make.add_argument("--report", default="coverage.json")
    make.add_argument("--review-db", default="reviews.db")
    make.add_argument("--manifest", default="cases.manifest.json")
    update = sub.add_parser("regenerate")
    update.add_argument("prd")
    update.add_argument("--previous-manifest", required=True)
    update.add_argument("--output", default="cases.json")
    update.add_argument("--manifest", default="cases.manifest.json")
    update.add_argument("--audit", default="impact-audit.json")
    update.add_argument("--review-db", default="reviews.db")
    args = parser.parse_args(argv)
    if args.command == "generate":
        print(json.dumps(generate(args.prd, args.output, args.report, args.review_db,
                                  args.manifest), indent=2))
    else:
        print(json.dumps(regenerate(args.prd, args.previous_manifest, args.output,
                                    args.manifest, args.audit, args.review_db), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

