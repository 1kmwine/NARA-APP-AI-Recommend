import pytest

from app.services.price_tiers import (
    PRICE_TIERS,
    format_price_desc,
    tier_bounds,
    widen_tier_ranges,
)


def test_ten_tiers_defined():
    assert len(PRICE_TIERS) == 10


def test_tier_bounds_first_tier():
    assert tier_bounds(0) == (0, 10_000)


def test_tier_bounds_last_tier_has_no_upper_bound():
    assert tier_bounds(9) == (10_000_001, None)


def test_tier_bounds_middle_tier():
    assert tier_bounds(6) == (100_001, 300_000)


def test_widen_tier_ranges_starts_with_exact_tier():
    ranges = widen_tier_ranges(5)
    assert ranges[0] == (70_001, 100_000)


def test_widen_tier_ranges_expands_both_directions_and_clamps():
    ranges = widen_tier_ranges(0)
    # tier 0은 아래로 넓힐 수 없으니 위로만 넓어지고, 끝엔 전체 범위(0, None)에 도달
    assert ranges[-1] == (0, None)


def test_widen_tier_ranges_covers_all_ten_tiers_eventually():
    ranges = widen_tier_ranges(9)
    assert ranges[-1] == (0, None)


def test_tier_bounds_rejects_negative_index():
    with pytest.raises(ValueError):
        tier_bounds(-1)


def test_tier_bounds_rejects_out_of_range_index():
    with pytest.raises(ValueError):
        tier_bounds(10)


def test_format_price_desc_uses_actual_leading_manwon_digit():
    # 47,426원은 검색 버킷("5만원대", 30001~50000)과 무관하게 "4만원대"로 보여야 함
    assert format_price_desc(47_426) == "4만원대"
    assert format_price_desc(68_000) == "6만원대"


def test_format_price_desc_low_boundary():
    assert format_price_desc(10_000) == "1만원 이하"
    assert format_price_desc(10_001) == "1만원대"


def test_format_price_desc_high_boundary():
    assert format_price_desc(9_999_999) == "999만원대"
    assert format_price_desc(10_000_000) == "1000만원 이상"
