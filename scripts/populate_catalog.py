"""
populate_catalog.py
-------------------
Reads the raw SHL product catalog from data/raw_catalog.json,
normalizes the field names (link→url, job_levels→target_levels, etc.),
and writes the normalized version to data/catalog.json.

Usage:
    python scripts/populate_catalog.py [--raw data/raw_catalog.json] [--output data/catalog.json]
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Mapping from real catalog "keys" to internal test_type codes
# -------------------------------------------------------------------
_KEY_TO_TYPE: Dict[str, str] = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "SI",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}


def parse_duration(duration_str: str) -> int | None:
    """Parse strings like '30 minutes', '10', '1 hour' → minutes integer."""
    if not duration_str or duration_str.strip() in ("", "-", "N/A", "Variable", "Untimed", "TBC"):
        return None
    m = re.search(r"(\d+)", str(duration_str))
    if not m:
        return None
    val = int(m.group(1))
    lower = duration_str.lower()
    if "hour" in lower or "hr" in lower:
        val *= 60
    return val


def normalize_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw catalog entry into the schema the codebase expects."""
    keys = item.get("keys", [])
    test_type = "U"
    for k in keys:
        mapped = _KEY_TO_TYPE.get(k)
        if mapped:
            test_type = mapped
            break

    return {
        "name": item.get("name", ""),
        "url": item.get("link", ""),
        "test_type": test_type,
        "description": item.get("description", ""),
        "dimensions": [],
        "duration_minutes": parse_duration(item.get("duration", "")),
        "target_levels": [lv.lower() for lv in item.get("job_levels", [])],
        "use_cases": [k.lower() for k in keys],
        "scraped_at": item.get("scraped_at", ""),
        "_original": {"entity_id": item.get("entity_id")},
    }


def main():
    parser = argparse.ArgumentParser(description="Populate SHL assessment catalog")
    parser.add_argument("--raw", default="data/raw_catalog.json",
                        help="Path to raw catalog JSON")
    parser.add_argument("--output", default="data/catalog.json",
                        help="Output path for normalized catalog")
    args = parser.parse_args()

    raw_path = Path(args.raw)
    if not raw_path.exists():
        logger.error(f"Raw catalog file not found: {raw_path}")
        logger.info("Please save the raw SHL catalog dump to data/raw_catalog.json first.")
        sys.exit(1)

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    logger.info(f"Loaded {len(raw_data)} raw entries from {raw_path}")

    normalized = [normalize_entry(item) for item in raw_data]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(normalized)} normalized entries to {output_path}")


if __name__ == "__main__":
    main()
