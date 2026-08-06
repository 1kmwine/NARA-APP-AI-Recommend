from app.services.bracket import (
    build_bracket,
    build_candidate_pool,
    exclude_used,
    pick_acidity_match,
    pick_aroma_match,
    pick_philosophy_match,
    pick_story_match,
)


def _candidate(item_cd: str, acidity: int, brand: str = "브랜드") -> dict:
    return {"itemCd": item_cd, "brandName": brand, "taste": {"acidity": acidity}}


def test_pick_acidity_match_picks_max_and_min():
    pool = [_candidate("A", 1), _candidate("B", 5), _candidate("C", 3)]
    high, low = pick_acidity_match(pool)
    assert high["itemCd"] == "B"
    assert low["itemCd"] == "A"


def test_pick_acidity_match_returns_none_when_pool_too_small():
    pool = [_candidate("A", 3)]
    assert pick_acidity_match(pool) is None


def test_pick_acidity_match_returns_none_for_empty_pool():
    assert pick_acidity_match([]) is None


def test_pick_acidity_match_treats_missing_taste_as_neutral():
    pool = [_candidate("A", 5), {"itemCd": "B", "brandName": "브랜드2", "taste": None}]
    high, low = pick_acidity_match(pool)
    assert high["itemCd"] == "A"
    assert low["itemCd"] == "B"


def test_pick_aroma_match_picks_one_fruit_one_floral():
    pool = [
        {"itemCd": "A", "pdataId": "P1"},
        {"itemCd": "B", "pdataId": "P2"},
        {"itemCd": "C", "pdataId": "P3"},
    ]
    aroma_by_pdata_id = {
        "P1": ["Cherry", "Plum"],  # fruit
        "P2": ["Violet", "Leather"],  # floral_tertiary
        "P3": ["Blackberry"],  # fruit
    }
    fruit, floral = pick_aroma_match(pool, aroma_by_pdata_id)
    assert fruit["itemCd"] == "A"
    assert floral["itemCd"] == "B"


def test_pick_aroma_match_returns_none_when_only_one_side_available():
    pool = [{"itemCd": "A", "pdataId": "P1"}, {"itemCd": "B", "pdataId": "P2"}]
    aroma_by_pdata_id = {"P1": ["Cherry"], "P2": ["Blackberry"]}  # 둘 다 fruit
    assert pick_aroma_match(pool, aroma_by_pdata_id) is None


def test_pick_aroma_match_skips_candidates_without_aroma_data():
    pool = [
        {"itemCd": "A", "pdataId": "P1"},
        {"itemCd": "B", "pdataId": None},
        {"itemCd": "C", "pdataId": "P3"},
    ]
    aroma_by_pdata_id = {"P1": ["Cherry"], "P3": ["Violet"]}
    fruit, floral = pick_aroma_match(pool, aroma_by_pdata_id)
    assert fruit["itemCd"] == "A"
    assert floral["itemCd"] == "C"


def test_exclude_used_removes_matched_item_cds():
    pool = [{"itemCd": "A"}, {"itemCd": "B"}, {"itemCd": "C"}]
    used = {"A", "C"}
    result = exclude_used(pool, used)
    assert [c["itemCd"] for c in result] == ["B"]


def test_exclude_used_with_empty_used_set_returns_pool_unchanged():
    pool = [{"itemCd": "A"}, {"itemCd": "B"}]
    assert exclude_used(pool, set()) == pool


def test_pick_story_match_picks_two_distinct_brands_with_verified_mentions():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
        {"itemCd": "C", "brandName": "브랜드1"},  # 브랜드1과 중복이라 스킵돼야 함
    ]
    articles_by_brand = {
        "브랜드1": [{"title": "t1", "excerpt": "레이건 대통령 만찬", "url": "u1"}],
        "브랜드2": [{"title": "t2", "excerpt": "올림픽 만찬주", "url": "u2"}],
    }

    def fake_verify(text: str) -> str | None:
        return "검증된 인용구: " + text[:5]

    result = pick_story_match(pool, articles_by_brand, verify_fn=fake_verify)

    assert result is not None
    (card_a, quote_a, url_a), (card_b, quote_b, url_b) = result
    assert card_a["itemCd"] == "A"
    assert card_b["itemCd"] == "B"
    assert quote_a is not None and quote_a.startswith("검증된 인용구")
    assert url_a == "u1"
    assert url_b == "u2"


def test_pick_story_match_fills_remaining_slot_with_unverified_candidate():
    """검증된 언급이 1개뿐이면, 남은 자리는 브랜드만 다른 후보로 채우고 quote/url은
    None으로 둔다 — 없는 이야기를 지어내지 않되, 경기는 항상 2장으로 채운다."""
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
        {"itemCd": "C", "brandName": "브랜드3"},
    ]
    articles_by_brand = {
        "브랜드1": [{"title": "t1", "excerpt": "레이건 대통령 만찬", "url": "u1"}],
        "브랜드2": [{"title": "t2", "excerpt": "그냥 홍보문구", "url": "u2"}],
    }

    def fake_verify(text: str) -> str | None:
        return "인용구" if "대통령" in text else None

    result = pick_story_match(pool, articles_by_brand, verify_fn=fake_verify)

    assert result is not None
    (card_a, quote_a, url_a), (card_b, quote_b, url_b) = result
    assert card_a["itemCd"] == "A"
    assert quote_a == "인용구"
    assert url_a == "u1"
    assert card_b["itemCd"] == "B"
    assert quote_b is None
    assert url_b is None


def test_pick_story_match_all_unverified_still_fills_two_slots():
    pool = [{"itemCd": "A", "brandName": "브랜드1"}, {"itemCd": "B", "brandName": "브랜드2"}]
    result = pick_story_match(pool, {}, verify_fn=lambda t: "인용구")
    assert result is not None
    (card_a, quote_a, _), (card_b, quote_b, _) = result
    assert {card_a["itemCd"], card_b["itemCd"]} == {"A", "B"}
    assert quote_a is None
    assert quote_b is None


def test_pick_story_match_calls_verify_fn_at_most_once_per_brand():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "A2", "brandName": "브랜드1"},  # same brand, second item
        {"itemCd": "B", "brandName": "브랜드2"},
    ]
    articles_by_brand = {
        "브랜드1": [{"title": "t1", "excerpt": "그냥 홍보문구", "url": "u1"}],
        "브랜드2": [{"title": "t2", "excerpt": "그냥 홍보문구2", "url": "u2"}],
    }
    call_count = {"n": 0}

    def counting_verify(text: str) -> str | None:
        call_count["n"] += 1
        return None  # never verifies, forces fallback path

    result = pick_story_match(pool, articles_by_brand, verify_fn=counting_verify)

    assert result is not None
    assert call_count["n"] == 2  # once for 브랜드1, once for 브랜드2 — NOT 3 times


def test_pick_story_match_returns_none_when_fewer_than_two_distinct_brands_in_pool():
    pool = [{"itemCd": "A", "brandName": "브랜드1"}, {"itemCd": "C", "brandName": "브랜드1"}]
    result = pick_story_match(pool, {}, verify_fn=lambda t: "인용구")
    assert result is None


def test_pick_philosophy_match_picks_two_distinct_brands_with_summaries():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
    ]
    intro_by_brand = {"브랜드1": "소개글1", "브랜드2": "소개글2"}

    def fake_summarize(text: str) -> str | None:
        return "요약: " + text

    result = pick_philosophy_match(pool, intro_by_brand, summarize_fn=fake_summarize)

    assert result is not None
    (card_a, summary_a), (card_b, summary_b) = result
    assert card_a["itemCd"] == "A"
    assert summary_a == "요약: 소개글1"
    assert card_b["itemCd"] == "B"
    assert summary_b == "요약: 소개글2"


def test_pick_philosophy_match_returns_none_when_fewer_than_two_intros_available():
    pool = [{"itemCd": "A", "brandName": "브랜드1"}]
    intro_by_brand = {"브랜드1": "소개글1"}
    result = pick_philosophy_match(pool, intro_by_brand, summarize_fn=lambda t: "요약")
    assert result is None


def test_pick_philosophy_match_skips_when_summarize_fails():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
        {"itemCd": "C", "brandName": "브랜드3"},
    ]
    intro_by_brand = {"브랜드1": "x", "브랜드2": "y", "브랜드3": "z"}

    def fake_summarize(text: str) -> str | None:
        return None if text == "x" else "요약: " + text

    result = pick_philosophy_match(pool, intro_by_brand, summarize_fn=fake_summarize)
    assert result is not None
    (card_a, _), (card_b, _) = result
    assert {card_a["itemCd"], card_b["itemCd"]} == {"B", "C"}


def test_build_candidate_pool_expands_regions_until_min_size_met():
    from app.services.region_cache import CountryRegions, RegionCount

    order = [
        CountryRegions(
            country="France",
            sku_count=10,
            regions=[
                RegionCount(label="보르도", sku_count=1),
                RegionCount(label="부르고뉴", sku_count=9),
            ],
        )
    ]

    call_log = []

    def fake_search(country: str, region: str, price_min: int, price_max):
        call_log.append(region)
        if region == "보르도":
            return [{"itemCd": "A", "brandName": "b1"}]
        return [{"itemCd": f"BG{i}", "brandName": f"bg{i}"} for i in range(10)]

    pool = build_candidate_pool(
        order=order, country_index=0, region_index=0, min_size=8, search_fn=fake_search
    )

    assert call_log == ["보르도", "부르고뉴"]
    assert len(pool) == 11  # 보르도 1개 + 부르고뉴 10개


def test_build_candidate_pool_dedupes_by_item_cd_across_regions():
    from app.services.region_cache import CountryRegions, RegionCount

    order = [
        CountryRegions(
            country="France",
            sku_count=5,
            regions=[RegionCount(label="R1", sku_count=1), RegionCount(label="R2", sku_count=1)],
        )
    ]

    def fake_search(country: str, region: str, price_min: int, price_max):
        return [{"itemCd": "DUP", "brandName": "b"}]

    pool = build_candidate_pool(
        order=order, country_index=0, region_index=0, min_size=8, search_fn=fake_search
    )

    assert len(pool) == 1


def test_build_bracket_assembles_up_to_four_matches():
    pool = [
        {"itemCd": "A", "brandName": "b1", "pdataId": "P1", "taste": {"acidity": 5}, "price_krw": 30000},
        {"itemCd": "B", "brandName": "b2", "pdataId": "P2", "taste": {"acidity": 0}, "price_krw": 30000},
        {"itemCd": "C", "brandName": "b3", "pdataId": "P3", "taste": {"acidity": 3}, "price_krw": 30000},
        {"itemCd": "D", "brandName": "b4", "pdataId": "P4", "taste": {"acidity": 3}, "price_krw": 30000},
        {"itemCd": "E", "brandName": "b5", "pdataId": None, "taste": {"acidity": 3}, "price_krw": 30000},
        {"itemCd": "F", "brandName": "b6", "pdataId": None, "taste": {"acidity": 3}, "price_krw": 30000},
        {"itemCd": "G", "brandName": "b7", "pdataId": None, "taste": {"acidity": 3}, "price_krw": 30000},
        {"itemCd": "H", "brandName": "b8", "pdataId": None, "taste": {"acidity": 3}, "price_krw": 30000},
    ]
    aroma_by_pdata_id = {"P3": ["Cherry"], "P4": ["Violet"]}
    # story axis consumes E(verified via b5's article) + F(unverified fallback),
    # leaving G/H (both with intros) for the philosophy axis — pick_philosophy_match
    # needs 2 distinct branded intros to return a match, and pick_story_match already
    # fills both its slots from whatever's left in the pool.
    articles_by_brand = {"b5": [{"title": "t", "excerpt": "레이건 대통령 만찬", "url": "u5"}]}
    intro_by_brand = {"b7": "소개글1", "b8": "소개글2"}

    result = build_bracket(
        pool=pool,
        aroma_by_pdata_id=aroma_by_pdata_id,
        articles_by_brand=articles_by_brand,
        intro_by_brand=intro_by_brand,
        verify_fn=lambda t: "검증된 인용구" if "대통령" in t else None,
        summarize_fn=lambda t: "요약: " + t,
    )

    axes = [m.axis for m in result.matches]
    assert axes == ["acidity", "aroma", "story", "philosophy"]
    acidity_match = result.matches[0]
    assert {c.item_cd for c in acidity_match.cards} == {"A", "B"}
