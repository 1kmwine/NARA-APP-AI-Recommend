from app.services.price_tiers import widen_tier_ranges
from app.services.recommend import find_with_fallback, pick_top_candidates


def test_pick_top_candidates_sorts_by_wishes_desc():
    candidates = [
        {"itemCd": "A", "wishes": 3, "reviews": 1},
        {"itemCd": "B", "wishes": 10, "reviews": 0},
        {"itemCd": "C", "wishes": None, "reviews": 5},
    ]
    top = pick_top_candidates(candidates, limit=2)
    assert [c["itemCd"] for c in top] == ["B", "A"]


def test_pick_top_candidates_treats_missing_wishes_as_zero():
    candidates = [{"itemCd": "A", "wishes": None, "reviews": None}]
    top = pick_top_candidates(candidates, limit=1)
    assert top[0]["itemCd"] == "A"


def test_find_with_fallback_returns_first_non_empty_search():
    calls = []

    def search(price_min, price_max):
        calls.append((price_min, price_max))
        if price_max == 100_000:
            return [{"itemCd": "X"}]
        return []

    result = find_with_fallback(tier_index=5, search=search)
    assert result == [{"itemCd": "X"}]
    assert calls[0] == widen_tier_ranges(5)[0]


def test_find_with_fallback_returns_empty_when_all_ranges_exhausted():
    result = find_with_fallback(tier_index=0, search=lambda lo, hi: [])
    assert result == []
