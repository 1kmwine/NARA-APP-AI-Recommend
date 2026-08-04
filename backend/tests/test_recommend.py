from app.services.price_tiers import widen_tier_ranges
from app.services.recommend import _matches_country_region, find_with_fallback, pick_top_candidates


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


def test_matches_country_region_true_when_both_match():
    assert _matches_country_region('{"ko": "부르고뉴"}', "France", "France", "부르고뉴") is True


def test_matches_country_region_false_when_region_differs():
    assert _matches_country_region('{"ko": "보르도"}', "France", "France", "부르고뉴") is False


def test_matches_country_region_false_when_country_differs():
    assert _matches_country_region('{"ko": "부르고뉴"}', "France", "USA", "부르고뉴") is False


def test_matches_country_region_falls_back_to_country_name_when_region_unmapped():
    # region_overrides.normalize_region_label()은 REGION_ALIAS/REGION_EXPAND에
    # 없는 지역은 "기타"가 아니라 원본 raw_region을 그대로 돌려준다 — "기타"는
    # extract_raw_region()이 빈 문자열일 때만 나온다(place_json 자체가 없을 때).
    assert (
        _matches_country_region('{"ko": "존재안함지역"}', "Georgia", "Georgia", "존재안함지역")
        is True
    )
