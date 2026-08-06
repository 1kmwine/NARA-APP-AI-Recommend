import json
from unittest.mock import MagicMock, patch

from app.services.pairing import (
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


@patch("app.services.pairing._call_gemini")
def test_infer_taste_target_parses_llm_json_response(mock_call):
    mock_call.return_value = json.dumps(
        {"sweetness": 2, "acidity": 4, "body": 3, "tannin": 1}
    )
    result = infer_taste_target("훈제 연어")
    assert result == TasteVector(sweetness=2, acidity=4, body=3, tannin=1)


@patch("app.services.pairing._call_gemini")
def test_infer_taste_target_falls_back_to_neutral_on_bad_response(mock_call):
    mock_call.return_value = "이건 JSON이 아님"
    result = infer_taste_target("아무 음식")
    assert result == TasteVector(sweetness=2, acidity=2, body=2, tannin=2)


def test_infer_taste_target_falls_back_to_neutral_when_call_raises():
    with patch("app.services.pairing._call_gemini", side_effect=RuntimeError("network down")):
        result = infer_taste_target("아무 음식")
    assert result == NEUTRAL_TASTE


@patch("app.services.pairing._call_gemini")
def test_infer_taste_target_strips_markdown_code_fence(mock_call):
    mock_call.return_value = '```json\n{"sweetness": 1, "acidity": 3, "body": 2, "tannin": 4}\n```'
    result = infer_taste_target("매운 음식")
    assert result == TasteVector(sweetness=1, acidity=3, body=2, tannin=4)


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
