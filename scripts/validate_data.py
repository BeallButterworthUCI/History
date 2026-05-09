"""Validate data/bbcomp.json and cross-check that years/ has matching markdown files.

Run locally:
    python scripts/validate_data.py

Exits with non-zero status on any failure so CI flags it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "bbcomp.json"
YEARS_DIR = REPO_ROOT / "years"

REQUIRED_TOP_KEYS = {
    "schema_version",
    "last_updated",
    "competition",
    "years",
    "pre_joint_editions",
    "cross_year_notes",
}

REQUIRED_AWARD_KEYS = {"track", "place", "team", "prize_text", "project"}
ALLOWED_TRACKS = {
    "Butterworth",
    "Beall",
    "Brazilian Collaboration",
    "International Collaboration",
}
ALLOWED_STATUSES = {
    "complete",
    "complete_unverified",
    "partial",
    "upcoming",
    "cancelled",
}


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def main() -> int:
    errors: list[str] = []

    if not DATA_PATH.exists():
        print(f"FATAL: {DATA_PATH} does not exist", file=sys.stderr)
        return 2

    with DATA_PATH.open(encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"FATAL: data/bbcomp.json is not valid JSON: {e}", file=sys.stderr)
            return 2

    missing_top = REQUIRED_TOP_KEYS - set(data.keys())
    if missing_top:
        fail(f"Top-level keys missing from data/bbcomp.json: {sorted(missing_top)}", errors)

    years_in_json = {entry.get("year") for entry in data.get("years", [])}
    pre_joint_years = {entry.get("year") for entry in data.get("pre_joint_editions", [])}

    for entry in data.get("years", []):
        year = entry.get("year")
        status = entry.get("status")

        if not isinstance(year, int):
            fail(f"years[]: missing or non-int 'year' field in entry: {entry!r}", errors)
            continue
        if status not in ALLOWED_STATUSES:
            fail(f"year {year}: status '{status}' not in {sorted(ALLOWED_STATUSES)}", errors)

        for award in entry.get("awards", []):
            missing = REQUIRED_AWARD_KEYS - set(award.keys())
            if missing:
                fail(
                    f"year {year}: award missing required keys {sorted(missing)} -> {award.get('team')!r}",
                    errors,
                )
            if "track" in award and award["track"] not in ALLOWED_TRACKS:
                fail(
                    f"year {year}: award track '{award['track']}' not in {sorted(ALLOWED_TRACKS)}",
                    errors,
                )
            if "prize_amount_usd" in award and award["prize_amount_usd"] is not None:
                if not isinstance(award["prize_amount_usd"], (int, float)):
                    fail(
                        f"year {year}: prize_amount_usd for {award.get('team')!r} is not numeric",
                        errors,
                    )

    all_years = years_in_json | pre_joint_years
    md_years = {int(p.stem) for p in YEARS_DIR.glob("*.md") if p.stem.isdigit()}

    only_in_json = all_years - md_years
    only_in_md = md_years - all_years

    if only_in_json:
        fail(
            f"Years present in data/bbcomp.json but missing from years/*.md: {sorted(only_in_json)}",
            errors,
        )
    if only_in_md:
        fail(
            f"Years present in years/*.md but missing from data/bbcomp.json: {sorted(only_in_md)}",
            errors,
        )

    if errors:
        print("Validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {DATA_PATH.name} is valid; {len(data['years'])} joint-era years and "
          f"{len(data['pre_joint_editions'])} pre-joint editions documented; "
          f"{len(md_years)} year markdown files present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
