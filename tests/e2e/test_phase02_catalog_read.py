# tests/e2e/test_phase02_catalog_read.py
"""Phase 2: Catalog read-only commands.

Captures photo_id for later phases. All commands are read-only.

Commands tested:
  - catalog get-selected (stores photo_id, photo_ids)
  - catalog list --limit 5
  - catalog get-info <photo_id>
  - catalog search "test"
  - catalog find --rating 0 --rating-op ">="
  - catalog collections
  - catalog keywords
  - catalog folders
  - catalog get-view-filter
  - catalog batch-metadata <photo_id>
"""
import pytest


@pytest.mark.e2e
class TestCatalogGetSelected:
    """Test 5: catalog get-selected — capture photo_id for subsequent phases."""

    def test_get_selected(self, run, e2e_state):
        r = run("catalog", "get-selected")
        assert r["exit_code"] == 0, f"get-selected failed: {r['output']}"
        assert r["data"] is not None, f"get-selected returned no JSON: {r['output']}"

        # Extract photo_id from the response
        data = r["data"]
        if isinstance(data, list) and len(data) > 0:
            # List of photos — take the first one
            first = data[0]
            if isinstance(first, dict) and "id" in first:
                e2e_state.photo_id = str(first["id"])
                e2e_state.photo_ids = [str(p["id"]) for p in data if isinstance(p, dict) and "id" in p]
            elif isinstance(first, (str, int)):
                e2e_state.photo_id = str(first)
                e2e_state.photo_ids = [str(p) for p in data]
        elif isinstance(data, dict):
            if "photos" in data and isinstance(data["photos"], list) and len(data["photos"]) > 0:
                first = data["photos"][0]
                if isinstance(first, dict) and "id" in first:
                    e2e_state.photo_id = str(first["id"])
                    e2e_state.photo_ids = [str(p["id"]) for p in data["photos"] if isinstance(p, dict) and "id" in p]
                elif isinstance(first, (str, int)):
                    e2e_state.photo_id = str(first)
                    e2e_state.photo_ids = [str(p) for p in data["photos"]]
            elif "id" in data:
                e2e_state.photo_id = str(data["id"])
                e2e_state.photo_ids = [e2e_state.photo_id]

        assert e2e_state.photo_id is not None, (
            f"Could not extract photo_id from get-selected response: {r['data']}"
        )


@pytest.mark.e2e
class TestCatalogList:
    """Test 6: catalog list --limit 5."""

    def test_list_photos(self, run):
        r = run("catalog", "list", "--limit", "5")
        assert r["exit_code"] == 0, f"list failed: {r['output']}"
        assert r["data"] is not None, f"list returned no JSON: {r['output']}"


@pytest.mark.e2e
class TestCatalogGetInfo:
    """Test 7: catalog get-info <photo_id>."""

    def test_get_info(self, run, e2e_state):
        assert e2e_state.photo_id is not None, "photo_id not set (Phase 2 depends on get-selected)"
        r = run("catalog", "get-info", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"get-info failed: {r['output']}"
        assert r["data"] is not None, f"get-info returned no JSON: {r['output']}"


@pytest.mark.e2e
class TestCatalogSearch:
    """Test 8: catalog search "test" — may return empty, that's OK."""

    def test_search(self, run):
        r = run("catalog", "search", "test")
        assert r["exit_code"] == 0, f"search failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogFind:
    """Test 9: catalog find --rating 0 --rating-op ">="."""

    def test_find_by_rating(self, run):
        r = run("catalog", "find", "--rating", "0", "--rating-op", ">=")
        assert r["exit_code"] == 0, f"find failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogCollections:
    """Test 10: catalog collections."""

    def test_collections(self, run):
        r = run("catalog", "collections")
        assert r["exit_code"] == 0, f"collections failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogKeywords:
    """Test 11: catalog keywords."""

    def test_keywords(self, run):
        r = run("catalog", "keywords")
        assert r["exit_code"] == 0, f"keywords failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogFolders:
    """Test 12: catalog folders."""

    def test_folders(self, run):
        r = run("catalog", "folders")
        assert r["exit_code"] == 0, f"folders failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogGetViewFilter:
    """Test 13: catalog get-view-filter."""

    def test_get_view_filter(self, run):
        r = run("catalog", "get-view-filter")
        assert r["exit_code"] == 0, f"get-view-filter failed: {r['output']}"


@pytest.mark.e2e
class TestCatalogBatchMetadata:
    """Test 14: catalog batch-metadata <photo_id>."""

    def test_batch_metadata(self, run, e2e_state):
        assert e2e_state.photo_id is not None, "photo_id not set"
        r = run("catalog", "batch-metadata", e2e_state.photo_id)
        assert r["exit_code"] == 0, f"batch-metadata failed: {r['output']}"
        assert r["data"] is not None, f"batch-metadata returned no JSON: {r['output']}"
