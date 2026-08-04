import pytest

from app.services.price_tiers import PRICE_TIERS, tier_bounds, widen_tier_ranges


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
