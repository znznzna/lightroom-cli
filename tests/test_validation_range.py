"""Tests for min/max range validation in _coerce_type()."""

import pytest

from cli.validation import ValidationError, validate_params


class TestRangeValidation:
    def test_integer_below_min_raises(self):
        with pytest.raises(ValidationError, match="below minimum"):
            validate_params("catalog.setRating", {"photoId": "123", "rating": -1})

    def test_integer_above_max_raises(self):
        with pytest.raises(ValidationError, match="above maximum"):
            validate_params("catalog.setRating", {"photoId": "123", "rating": 6})

    def test_integer_at_min_boundary_passes(self):
        result = validate_params("catalog.setRating", {"photoId": "123", "rating": 0})
        assert result["rating"] == 0

    def test_integer_at_max_boundary_passes(self):
        result = validate_params("catalog.setRating", {"photoId": "123", "rating": 5})
        assert result["rating"] == 5

    def test_no_min_max_skips_check(self):
        result = validate_params("develop.setValue", {"parameter": "Exposure", "value": 999.0})
        assert result["value"] == 999.0

    def test_suggestions_include_valid_range(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_params("catalog.setRating", {"photoId": "123", "rating": 10})
        assert "0" in str(exc_info.value.suggestions)
        assert "5" in str(exc_info.value.suggestions)
