import json
from unittest.mock import patch

from app.services.bracket_content import summarize_philosophy, verify_story_mention


def test_summarize_philosophy_returns_gemini_text():
    with patch(
        "app.services.bracket_content._call_gemini_text",
        return_value="포도 본연의 생명력을 지키는 철학.",
    ):
        result = summarize_philosophy("나파 밸리의 전설로 불리는 그르기치 힐스는...")
    assert result == "포도 본연의 생명력을 지키는 철학."


def test_verify_story_mention_returns_parsed_result_when_found():
    fake_response = json.dumps({"has_mention": True, "quote": "레이건 대통령 방불 정상 만찬주로 선정됐어요"})
    with patch("app.services.bracket_content._call_gemini_text", return_value=fake_response):
        result = verify_story_mention("레이건 대통령 방불 정상 만찬...")
    assert result == "레이건 대통령 방불 정상 만찬주로 선정됐어요"


def test_verify_story_mention_returns_none_when_not_found():
    fake_response = json.dumps({"has_mention": False, "quote": None})
    with patch("app.services.bracket_content._call_gemini_text", return_value=fake_response):
        result = verify_story_mention("그냥 평범한 데일리 와인 소개글...")
    assert result is None


def test_verify_story_mention_returns_none_on_call_failure():
    with patch("app.services.bracket_content._call_gemini_text", side_effect=RuntimeError("network")):
        result = verify_story_mention("아무 텍스트")
    assert result is None


def test_verify_story_mention_returns_none_on_bad_json():
    with patch("app.services.bracket_content._call_gemini_text", return_value="이건 JSON 아님"):
        result = verify_story_mention("아무 텍스트")
    assert result is None


def test_verify_story_mention_returns_none_when_json_is_not_an_object():
    # responseMimeType: application/json only guarantees valid JSON, not an object shape —
    # Gemini could legally return `true`, `null`, a bare string, etc. This must not crash.
    with patch("app.services.bracket_content._call_gemini_text", return_value="true"):
        result = verify_story_mention("아무 텍스트")
    assert result is None
