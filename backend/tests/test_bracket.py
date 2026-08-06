from app.services.bracket import exclude_used, pick_acidity_match, pick_aroma_match


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
