"""Audit the local SHL catalog used by the recommender.

This is intentionally offline and deterministic: it verifies that every
recommendation can be grounded to the bundled catalog artifact used by the API.
It does not claim the artifact is a fresh live scrape of shl.com.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "catalog.json"
OUT_DIR = ROOT / "evaluation"
OUT_PATH = OUT_DIR / "catalog_audit.json"


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    names = [item.get("name", "") for item in catalog]
    urls = [item.get("url", "") for item in catalog]
    types = [item.get("test_type", "") for item in catalog]

    report = {
        "catalog_path": str(CATALOG_PATH),
        "assessment_count": len(catalog),
        "unique_names": len(set(names)),
        "unique_urls": len(set(urls)),
        "duplicate_names": sorted([name for name, count in Counter(names).items() if count > 1]),
        "duplicate_urls": sorted([url for url, count in Counter(urls).items() if count > 1]),
        "missing_required_fields": [
            {
                "index": idx,
                "missing": [
                    field
                    for field in ("name", "url", "test_type", "description")
                    if not item.get(field)
                ],
            }
            for idx, item in enumerate(catalog)
            if any(not item.get(field) for field in ("name", "url", "test_type", "description"))
        ],
        "invalid_shl_urls": [
            item.get("url", "")
            for item in catalog
            if not (
                item.get("url", "").startswith("https://www.shl.com/products/product-catalog/view/")
                or item.get("url", "").startswith("https://www.shl.com/solutions/products/")
            )
        ],
        "test_type_counts": dict(sorted(Counter(types).items())),
        "duration_known_count": sum(1 for item in catalog if item.get("duration_minutes")),
        "duration_missing_count": sum(1 for item in catalog if not item.get("duration_minutes")),
        "live_catalog_freshness_note": (
            "This audit validates the local SHL catalog artifact used by the API."
        ),
    }

    OUT_DIR.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
