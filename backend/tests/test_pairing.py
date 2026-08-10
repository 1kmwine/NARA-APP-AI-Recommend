from app.services.pairing import (
    FOOD_TASTE_TABLE,
    NEUTRAL_TASTE,
    TasteVector,
    infer_taste_target,
    score_by_pairing,
    score_by_preference,
    taste_distance,
)


def test_taste_distance_zero_when_identical():
    v = TasteVector(sweetness=2, acidity=3, body=4, tannin=1)
    assert taste_distance(v, v) == 0.0


def test_taste_distance_positive_when_different():
    a = TasteVector(sweetness=0, acidity=0, body=0, tannin=0)
    b = TasteVector(sweetness=5, acidity=0, body=0, tannin=0)
    assert taste_distance(a, b) == 5.0


def test_score_by_pairing_ranks_closer_taste_first():
    target = TasteVector(sweetness=1, acidity=4, body=2, tannin=1)
    candidates = [
        {"itemCd": "far", "taste": {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5}},
        {"itemCd": "close", "taste": {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 2}},
    ]
    ranked = score_by_pairing(candidates, target)
    assert [c["itemCd"] for c in ranked] == ["close", "far"]


def test_score_by_pairing_treats_missing_taste_as_neutral():
    target = TasteVector(sweetness=0, acidity=0, body=0, tannin=0)
    candidates = [{"itemCd": "no-taste", "taste": None}]
    ranked = score_by_pairing(candidates, target)
    assert ranked[0]["itemCd"] == "no-taste"


def test_infer_taste_target_returns_table_value_for_known_food():
    result = infer_taste_target("초밥")
    assert result == FOOD_TASTE_TABLE["초밥"]


def test_infer_taste_target_matches_spicy_keyword():
    result = infer_taste_target("엄청 매운 마라탕")
    assert result.tannin == 1
    assert result.sweetness == 3


def test_infer_taste_target_matches_fried_keyword():
    result = infer_taste_target("바삭한 새우튀김")
    assert result.acidity == 4
    assert result.body == 4


def test_infer_taste_target_matches_raw_fish_keyword():
    result = infer_taste_target("연어 회 한 접시")
    assert result.acidity == 4
    assert result.body == 1


def test_infer_taste_target_falls_back_to_neutral_for_unknown_text():
    result = infer_taste_target("아무 의미 없는 텍스트")
    assert result == NEUTRAL_TASTE


def test_score_by_preference_returns_unchanged_when_no_signal():
    candidates = [{"itemCd": "a", "taste": None}, {"itemCd": "b", "taste": None}]
    assert score_by_preference(candidates, liked=None, disliked=None) == candidates


def test_score_by_preference_ranks_close_to_liked_first():
    liked = TasteVector(sweetness=1, acidity=4, body=2, tannin=1)
    candidates = [
        {"itemCd": "far", "taste": {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5}},
        {"itemCd": "close", "taste": {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 2}},
    ]
    ranked = score_by_preference(candidates, liked=liked, disliked=None)
    assert [c["itemCd"] for c in ranked] == ["close", "far"]


def test_score_by_preference_ranks_far_from_disliked_first():
    disliked = TasteVector(sweetness=1, acidity=4, body=2, tannin=1)
    candidates = [
        {"itemCd": "similar-to-disliked", "taste": {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 2}},
        {"itemCd": "different-from-disliked", "taste": {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5}},
    ]
    ranked = score_by_preference(candidates, liked=None, disliked=disliked)
    assert [c["itemCd"] for c in ranked] == ["different-from-disliked", "similar-to-disliked"]
