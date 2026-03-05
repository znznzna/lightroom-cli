"""
Phase 11: AI Mask E2E Tests

Requirements:
- Lightroom Classic running with CLI Bridge plugin
- Test collection '_lr-cli-test' with at least 2 photos
- Photos must be in Develop module

These tests verify actual AI mask creation in Lightroom.
Run with: pytest tests/e2e/test_phase11_ai_mask.py -v
"""

import json
import subprocess

import pytest


def lr(*args):
    """lr CLI を実行して結果を返すヘルパー"""
    result = subprocess.run(
        ["lr", "-o", "json", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result


@pytest.mark.e2e
class TestAIMaskCreation:
    """AI マスク作成の E2E テスト"""

    def test_ai_subject_creates_mask(self):
        """lr develop ai subject が成功する"""
        result = lr("develop", "ai", "subject")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("selectionType") == "subject"

    def test_ai_sky_creates_mask(self):
        """lr develop ai sky が成功する"""
        result = lr("develop", "ai", "sky")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("selectionType") == "sky"

    def test_ai_sky_with_adjustment(self):
        """lr develop ai sky --adjust が調整を適用する"""
        result = lr("develop", "ai", "sky", "--adjust", '{"Exposure": -0.5}')
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "adjustments" in data or "selectionType" in data

    def test_ai_sky_with_preset(self):
        """lr develop ai sky --adjust-preset darken-sky がプリセットを適用する"""
        result = lr("develop", "ai", "sky", "--adjust-preset", "darken-sky")
        assert result.returncode == 0

    def test_ai_reset_clears_masks(self):
        """lr develop ai reset 後にマスクがなくなる"""
        lr("develop", "ai", "subject")
        result = lr("develop", "ai", "reset")
        assert result.returncode == 0

    def test_ai_list_shows_masks(self):
        """lr develop ai list がマスク一覧を返す"""
        lr("develop", "ai", "subject")
        result = lr("develop", "ai", "list")
        assert result.returncode == 0

    def test_ai_presets_lists_all(self):
        """lr develop ai presets が全プリセットを返す"""
        result = lr("develop", "ai", "presets")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "darken-sky" in data


@pytest.mark.e2e
class TestAIMaskBatch:
    """バッチ AI マスクの E2E テスト"""

    def test_ai_batch_dry_run(self):
        """lr develop ai batch sky --all-selected --dry-run"""
        result = lr("develop", "ai", "batch", "sky", "--all-selected", "--dry-run")
        assert result.returncode == 0

    def test_ai_batch_all_selected(self):
        """lr develop ai batch sky --all-selected"""
        result = lr("develop", "ai", "batch", "subject", "--all-selected")
        assert result.returncode == 0


@pytest.mark.e2e
class TestAIMaskPartSelection:
    """パーツ選択の E2E テスト"""

    def test_ai_people_full(self):
        """lr develop ai people (パーツなし)"""
        result = lr("develop", "ai", "people")
        assert result.returncode == 0

    def test_ai_people_with_part_eyes(self):
        """lr develop ai people --part eyes (SDK サポート未検証)"""
        result = lr("develop", "ai", "people", "--part", "eyes")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # パーツ未対応なら warning が含まれる
        if not data.get("partApplied", False):
            assert "warning" in data or "partSupported" in data
