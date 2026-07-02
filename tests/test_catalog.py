"""
Unit tests for catalog management (Phase 2).
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.retrieval.catalog import CatalogManager

@pytest.fixture
def sample_catalog():
    return [
        {
            "name": "Test Assessment 1",
            "url": "https://www.shl.com/solutions/products/test-1/",
            "test_type": "P",
            "description": "Test personality assessment",
            "dimensions": ["Dimension1", "Dimension2"],
            "duration_minutes": 30,
            "target_levels": ["mid", "senior"],
            "use_cases": ["recruitment"],
            "scraped_at": "2026-07-01T00:00:00"
        },
        {
            "name": "Test Assessment 2",
            "url": "https://www.shl.com/solutions/products/test-2/",
            "test_type": "K",
            "description": "Test knowledge assessment",
            "dimensions": ["Skill1"],
            "duration_minutes": 45,
            "target_levels": ["senior"],
            "use_cases": ["recruitment", "assessment"],
            "scraped_at": "2026-07-01T00:00:00"
        }
    ]

@pytest.fixture
def temp_catalog_file(sample_catalog):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_catalog, f)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink()

class TestCatalogManager:

    def test_load_catalog(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert len(manager.catalog) == 2
        assert manager.catalog[0]['name'] == "Test Assessment 1"

    def test_get_assessment_by_name(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assessment = manager.get_assessment("Test Assessment 1")
        assert assessment is not None
        assert assessment['url'] == "https://www.shl.com/solutions/products/test-1/"
        assert manager.get_assessment("test assessment 1") is not None
        assert manager.get_assessment("Non-existent") is None

    def test_get_assessment_by_url(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assessment = manager.get_by_url("https://www.shl.com/solutions/products/test-1/")
        assert assessment is not None
        assert assessment['name'] == "Test Assessment 1"
        assert manager.get_by_url("HTTPS://WWW.SHL.COM/SOLUTIONS/PRODUCTS/TEST-1/") is not None
        assert manager.get_by_url("https://www.shl.com/solutions/products/fake/") is None

    def test_list_by_type(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        p_tests = manager.list_by_type("P")
        assert len(p_tests) == 1
        assert p_tests[0]['name'] == "Test Assessment 1"
        k_tests = manager.list_by_type("K")
        assert len(k_tests) == 1
        assert k_tests[0]['name'] == "Test Assessment 2"
        assert len(manager.list_by_type("U")) == 0

    def test_list_by_level(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert len(manager.list_by_level("senior")) == 2
        assert len(manager.list_by_level("mid")) == 1
        assert len(manager.list_by_level("entry")) == 0

    def test_search_by_keyword(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert len(manager.search_by_keyword("Test")) == 2
        results = manager.search_by_keyword("personality")
        assert len(results) == 1
        assert results[0]['name'] == "Test Assessment 1"
        assert len(manager.search_by_keyword("xyz")) == 0

    def test_verify_url(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert manager.verify_url("https://www.shl.com/solutions/products/test-1/")
        assert manager.verify_url("HTTPS://WWW.SHL.COM/SOLUTIONS/PRODUCTS/TEST-1/")
        assert not manager.verify_url("https://www.shl.com/solutions/products/fake/")

    def test_verify_name(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert manager.verify_name("Test Assessment 1")
        assert manager.verify_name("test assessment 1")
        assert not manager.verify_name("Non-existent Assessment")

    def test_get_all_test_types(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert set(manager.get_all_test_types()) == {"K", "P"}

    def test_get_all_levels(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        assert set(manager.get_all_levels()) == {"mid", "senior"}

    def test_validate_catalog(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        results = manager.validate_catalog()
        assert results['total_assessments'] == 2
        assert results['valid_assessments'] == 2
        assert results['validation_passed'] is True
        assert len(results['errors']) == 0

    def test_get_stats(self, temp_catalog_file):
        manager = CatalogManager(temp_catalog_file)
        stats = manager.get_stats()
        assert stats['total_assessments'] == 2
        assert 'P' in stats['test_types']
        assert 'K' in stats['test_types']
        assert 'mid' in stats['target_levels']
        assert 'senior' in stats['target_levels']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])