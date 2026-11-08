"""Tamper-evident suite manifests and clause-scoped incremental regeneration."""

from __future__ import annotations

from dataclasses import fields
from hashlib import sha256
import json
from typing import Any

from .generator import generate_for, requirement_fingerprint
from .models import Requirement, TestCase


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode()).hexdigest()


def build_manifest(requirements: list[Requirement], cases: list[TestCase]) -> dict:
    requirement_rows = [
        {"id": item.id, "text": item.text,
         "fingerprint": requirement_fingerprint(item)}
        for item in sorted(requirements, key=lambda item: item.id)
    ]
    case_rows = [case.to_dict() for case in sorted(cases, key=lambda item: item.id)]
    body = {"schema_version": 1, "generator": "deterministic-grid-v2",
            "requirements": requirement_rows, "cases": case_rows}
    return {**body, "suite_digest": _digest(body)}


def validate_manifest(manifest: dict) -> dict:
    required = {"schema_version", "generator", "requirements", "cases", "suite_digest"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("manifest has unsupported or missing fields")
    if manifest["schema_version"] != 1 or manifest["generator"] != "deterministic-grid-v2":
        raise ValueError("unsupported manifest version or generator")
    body = {key: manifest[key] for key in required - {"suite_digest"}}
    if manifest["suite_digest"] != _digest(body):
        raise ValueError("manifest digest does not match its contents")
    requirements = manifest["requirements"]
    cases = manifest["cases"]
    if not isinstance(requirements, list) or not isinstance(cases, list):
        raise ValueError("manifest requirements and cases must be lists")
    by_id = {}
    for row in requirements:
        if not isinstance(row, dict) or set(row) != {"id", "text", "fingerprint"}:
            raise ValueError("invalid requirement lineage row")
        if row["id"] in by_id:
            raise ValueError("duplicate requirement in manifest")
        requirement = Requirement(row["id"], row["text"])
        if row["fingerprint"] != requirement_fingerprint(requirement):
            raise ValueError("requirement fingerprint does not match text")
        by_id[row["id"]] = row
    case_fields = {item.name for item in fields(TestCase)}
    seen_cases = set()
    for row in cases:
        if not isinstance(row, dict) or set(row) != case_fields:
            raise ValueError("invalid case lineage row")
        if row["id"] in seen_cases:
            raise ValueError("duplicate case in manifest")
        seen_cases.add(row["id"])
        requirement = by_id.get(row["requirement_id"])
        if requirement is None or row["requirement_fingerprint"] != requirement["fingerprint"]:
            raise ValueError("case lineage does not match a manifest requirement")
        if row["evidence"] != requirement["text"]:
            raise ValueError("case evidence does not match its requirement")
    return manifest


def regenerate_impacted(previous: dict, requirements: list[Requirement]) -> tuple[list[TestCase], dict, dict, list[TestCase]]:
    validate_manifest(previous)
    old_requirements = {row["id"]: row for row in previous["requirements"]}
    old_cases = [TestCase(**row) for row in previous["cases"]]
    old_by_requirement: dict[str, list[TestCase]] = {}
    for case in old_cases:
        old_by_requirement.setdefault(case.requirement_id, []).append(case)

    cases: list[TestCase] = []
    added: list[TestCase] = []
    retained: list[TestCase] = []
    changes = []
    new_ids = {requirement.id for requirement in requirements}
    for requirement in requirements:
        fingerprint = requirement_fingerprint(requirement)
        previous_row = old_requirements.get(requirement.id)
        if previous_row and previous_row["fingerprint"] == fingerprint:
            current = sorted(old_by_requirement.get(requirement.id, []), key=lambda item: item.id)
            retained.extend(current)
            cases.extend(current)
            status = "unchanged"
        else:
            current = generate_for(requirement)
            added.extend(current)
            cases.extend(current)
            status = "changed" if previous_row else "added"
        changes.append({"requirement_id": requirement.id, "status": status,
                        "previous_fingerprint": previous_row["fingerprint"] if previous_row else None,
                        "current_fingerprint": fingerprint})
    for requirement_id, row in sorted(old_requirements.items()):
        if requirement_id not in new_ids:
            changes.append({"requirement_id": requirement_id, "status": "removed",
                            "previous_fingerprint": row["fingerprint"],
                            "current_fingerprint": None})

    impacted_ids = {row["requirement_id"] for row in changes if row["status"] in {"changed", "removed"}}
    retired = [case for case in old_cases if case.requirement_id in impacted_ids]
    manifest = build_manifest(requirements, cases)
    audit = {
        "schema_version": 1,
        "previous_suite_digest": previous["suite_digest"],
        "current_suite_digest": manifest["suite_digest"],
        "requirement_changes": changes,
        "regenerated_requirement_ids": sorted({case.requirement_id for case in added}),
        "retained_case_ids": sorted(case.id for case in retained),
        "added_case_ids": sorted(case.id for case in added),
        "retired_case_ids": sorted(case.id for case in retired),
        "counts": {"retained": len(retained), "added": len(added), "retired": len(retired)},
    }
    audit["audit_digest"] = _digest(audit)
    return cases, manifest, audit, added
