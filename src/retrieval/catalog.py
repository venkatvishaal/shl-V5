"""
CatalogManager
--------------
Loads the SHL assessment catalog from a JSON file and exposes
lookup / filter / verification helpers used by the agent and search layers.

Fully compatible with the Phase 2 CatalogManager API:
  - _load_catalog() (private, called from __init__)
  - validate_catalog() → errors list has keys: index, name, issues
                       → result has 'validation_passed' and 'issues_count'
  - search_by_keyword(keyword, fields=None) → searches name, description,
    dimensions, use_cases by default
  - list_all() → returns a copy
  - list_by_level() → case-insensitive on both sides
  - verify_url(url) / verify_name(name) → hallucination guards
  - get_stats() / get_all_use_cases()   → extra helpers
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CatalogManager:
    """Manages the in-memory SHL assessment catalog."""

    def __init__(self, catalog_path: str):
        self.catalog_path = catalog_path
        self.catalog: List[Dict[str, Any]] = []
        self.assessment_index: Dict[str, Dict] = {}  # lower(name) → assessment
        self.url_index: Dict[str, Dict] = {}          # lower(url)  → assessment
        self._load_catalog()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_catalog(self) -> None:
        """Load catalog from the JSON file and build lookup indices (private)."""
        path = Path(self.catalog_path)
        if not path.exists():
            logger.error(f"Catalog file not found: {self.catalog_path}")
            raise FileNotFoundError(f"Catalog not found: {self.catalog_path}")

        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in catalog: {e}")
            raise

        # Normalize the catalog: the real SHL data uses a different schema
        # (link, job_levels, keys, duration) than what the codebase expects
        # (url, target_levels, test_type, use_cases, duration_minutes, dimensions).
        self.catalog = [self._normalize_entry(item) for item in raw]

        self._build_indices()
        logger.info(f"Loaded {len(self.catalog)} assessments from {self.catalog_path}")

    _KEY_TO_TEST_TYPE = {
        "Ability & Aptitude": "A",
        "Assessment Exercises": "E",
        "Biodata & Situational Judgment": "SI",
        "Competencies": "C",
        "Development & 360": "D",
        "Knowledge & Skills": "K",
        "Personality & Behavior": "P",
        "Simulations": "S",
    }

    @staticmethod
    def _parse_duration(duration_str: str) -> int | None:
        """Parse a duration string like '30 minutes' or '10' into minutes integer."""
        if not duration_str:
            return None
        import re
        match = re.search(r"(\d+)", str(duration_str))
        if match:
            val = int(match.group(1))
            # If the string mentions hours, multiply by 60
            if "hour" in duration_str.lower() or "hr" in duration_str.lower():
                val *= 60
            return val
        return None

    def _normalize_entry(self, item: dict) -> dict:
        """
        Normalize a catalog entry to the internal schema.

        Two input formats are supported:
        1. The real SHL API schema (has 'link', 'job_levels', 'keys', 'duration')
        2. The internal schema (has 'url', 'target_levels', 'test_type', 'use_cases')

        Entries already in the internal format are passed through as-is.
        """
        # Detect which schema: if the entry has 'url' (not 'link'), it's already
        # in internal format and should be passed through as-is.
        if "url" in item and "link" not in item:
            # Already in internal format — just ensure required fields exist
            return {
                "name": item.get("name", ""),
                "url": item.get("url", ""),
                "test_type": item.get("test_type", "U"),
                "description": item.get("description", ""),
                "dimensions": item.get("dimensions", []),
                "duration_minutes": item.get("duration_minutes", None),
                "target_levels": [lv.lower() for lv in item.get("target_levels", [])],
                "use_cases": [uc.lower() for uc in item.get("use_cases", [])],
                "scraped_at": item.get("scraped_at", ""),
            }

        # Real SHL API schema — normalize from link/job_levels/keys/duration
        keys = item.get("keys", [])
        test_type = "U"  # unknown default
        for key in keys:
            mapped = self._KEY_TO_TEST_TYPE.get(key)
            if mapped:
                test_type = mapped
                break

        duration_str = item.get("duration", "")
        duration_minutes = self._parse_duration(duration_str)

        return {
            "name": item.get("name", ""),
            "url": item.get("link", ""),
            "test_type": test_type,
            "description": item.get("description", ""),
            "dimensions": [],  # Real data doesn't include dimensions
            "duration_minutes": duration_minutes,
            "target_levels": [lv.lower() for lv in item.get("job_levels", [])],
            "use_cases": [k.lower() for k in keys],
            "scraped_at": item.get("scraped_at", ""),
        }

    # Public alias so Phase 3 code that calls load_catalog() still works.
    def load_catalog(self) -> None:
        """Public alias for _load_catalog (reload from disk)."""
        self._load_catalog()

    def _build_indices(self) -> None:
        """Build name and URL indices for O(1) lookups."""
        self.assessment_index = {}
        self.url_index = {}

        for assessment in self.catalog:
            name = assessment.get("name", "").lower().strip()
            url = assessment.get("url", "").lower().strip()

            if name:
                self.assessment_index[name] = assessment
            if url:
                self.url_index[url] = assessment

        logger.debug(
            f"Built indices: {len(self.assessment_index)} by name, "
            f"{len(self.url_index)} by URL"
        )

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_catalog(self) -> Dict[str, Any]:
        """
        Validate catalog integrity.

        Returns a dict whose 'errors' list matches Phase 2 shape:
            [{"index": int, "name": str, "issues": [str]}, ...]
        Also includes 'validation_passed' and 'issues_count' keys.
        """
        results: Dict[str, Any] = {
            "total_assessments": len(self.catalog),
            "valid_assessments": 0,
            "missing_name": [],
            "missing_url": [],
            "invalid_url": [],
            "missing_description": [],
            "errors": [],
        }

        for idx, assessment in enumerate(self.catalog):
            issues: List[str] = []

            if not assessment.get("name"):
                results["missing_name"].append(idx)
                issues.append("missing_name")

            url = assessment.get("url", "")
            if not url:
                results["missing_url"].append(idx)
                issues.append("missing_url")
            elif not url.startswith("https://www.shl.com"):
                results["invalid_url"].append(idx)
                issues.append(f"invalid_url: {url}")

            if not assessment.get("description"):
                results["missing_description"].append(idx)

            if not issues:
                results["valid_assessments"] += 1
            else:
                results["errors"].append(
                    {
                        "index": idx,
                        "name": assessment.get("name", "UNKNOWN"),
                        "issues": issues,
                    }
                )

        results["issues_count"] = len(results["errors"])
        results["validation_passed"] = (
            results["valid_assessments"] == results["total_assessments"]
        )

        logger.info(
            f"Validation: {results['valid_assessments']}/{results['total_assessments']} valid"
        )
        return results

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_assessment(self, name: str) -> Optional[Dict]:
        """Get an assessment by exact name (case-insensitive)."""
        return self.assessment_index.get(name.lower().strip())

    def get_by_url(self, url: str) -> Optional[Dict]:
        """Get an assessment by URL (case-insensitive)."""
        return self.url_index.get(url.lower().strip())

    def list_all(self) -> List[Dict]:
        """Return a copy of all assessments (safe against external mutation)."""
        return self.catalog.copy()

    def list_by_type(self, test_type: str) -> List[Dict]:
        """Filter assessments by test_type code (e.g. 'P', 'K', 'A')."""
        wanted = test_type.upper()
        return [
            a for a in self.catalog
            if wanted in {code.strip().upper() for code in str(a.get("test_type", "")).split(",")}
        ]

    def list_by_level(self, level: str) -> List[Dict]:
        """Filter assessments by target level — both sides lowercased."""
        level_lower = level.lower()
        return [
            a
            for a in self.catalog
            if level_lower in [lv.lower() for lv in a.get("target_levels", [])]
        ]

    def search_by_keyword(
        self, keyword: str, fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Substring search across assessment fields.

        Args:
            keyword: Search term (case-insensitive).
            fields:  Fields to search. Defaults to
                     ['name', 'description', 'dimensions', 'use_cases'].
        """
        if fields is None:
            fields = ["name", "description", "dimensions", "use_cases"]

        kw = keyword.lower()
        results = []

        for assessment in self.catalog:
            matched = False
            for field in fields:
                value = assessment.get(field, "")
                if isinstance(value, str):
                    if kw in value.lower():
                        matched = True
                        break
                elif isinstance(value, list):
                    if any(kw in str(item).lower() for item in value):
                        matched = True
                        break
            if matched:
                results.append(assessment)

        return results

    # ── Aggregates ────────────────────────────────────────────────────────────

    def get_all_test_types(self) -> List[str]:
        """Return a sorted list of all unique test_type codes in the catalog."""
        return sorted({a.get("test_type", "") for a in self.catalog if a.get("test_type")})

    def get_all_levels(self) -> List[str]:
        """Return a sorted list of all unique target levels in the catalog."""
        levels: set = set()
        for assessment in self.catalog:
            levels.update(lv.lower() for lv in assessment.get("target_levels", []))
        return sorted(levels)

    def get_all_use_cases(self) -> List[str]:
        """Return a sorted list of all unique use cases in the catalog."""
        use_cases: set = set()
        for assessment in self.catalog:
            use_cases.update(uc.lower() for uc in assessment.get("use_cases", []))
        return sorted(use_cases)

    # ── Hallucination guards ──────────────────────────────────────────────────

    def verify_url(self, url: str) -> bool:
        """Return True if the URL exists in the catalog (case-insensitive)."""
        return url.lower().strip() in self.url_index

    def verify_name(self, name: str) -> bool:
        """Return True if the assessment name exists in the catalog (case-insensitive)."""
        return name.lower().strip() in self.assessment_index

    # ── Statistics ────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics about the catalog."""
        return {
            "total_assessments": len(self.catalog),
            "test_types": self._count_by_field("test_type"),
            "target_levels": self._count_by_field("target_levels"),
            "avg_duration_minutes": self._avg_duration(),
            "assessments_with_dimensions": len(
                [a for a in self.catalog if a.get("dimensions")]
            ),
            "assessments_with_use_cases": len(
                [a for a in self.catalog if a.get("use_cases")]
            ),
        }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count occurrences of each value in a catalog field."""
        counts: Dict[str, int] = {}
        for assessment in self.catalog:
            value = assessment.get(field)
            if isinstance(value, str):
                counts[value] = counts.get(value, 0) + 1
            elif isinstance(value, list):
                for item in value:
                    counts[item] = counts.get(item, 0) + 1
        return counts

    def _avg_duration(self) -> Optional[float]:
        """Return the mean duration (minutes) across assessments that have one."""
        durations = [
            a["duration_minutes"]
            for a in self.catalog
            if a.get("duration_minutes") is not None
        ]
        return sum(durations) / len(durations) if durations else None


# ── CLI validation helper ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import json as _json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    manager = CatalogManager("data/catalog.json")
    report = manager.validate_catalog()
    print(_json.dumps(report, indent=2))
