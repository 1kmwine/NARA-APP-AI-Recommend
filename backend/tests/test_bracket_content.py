from app.services.bracket_content import excerpt_philosophy, excerpt_story


def test_excerpt_story_returns_short_text_unchanged():
    assert excerpt_story("짧은 발췌문") == "짧은 발췌문"


def test_excerpt_story_truncates_long_text_to_80_chars():
    text = "가" * 100
    result = excerpt_story(text)
    assert result == "가" * 80 + "..."


def test_excerpt_story_handles_none_and_empty():
    assert excerpt_story(None) == ""
    assert excerpt_story("") == ""


def test_excerpt_philosophy_extracts_first_sentence():
    intro = "포도 본연의 생명력을 지킨다. 두번째 문장은 무시된다."
    result = excerpt_philosophy(intro)
    assert result == "포도 본연의 생명력을 지킨다."


def test_excerpt_philosophy_truncates_long_first_sentence_to_40_chars():
    intro = "가" * 60 + "."
    result = excerpt_philosophy(intro)
    assert result == "가" * 40 + "..."


def test_excerpt_philosophy_falls_back_to_truncated_text_when_no_punctuation():
    intro = "가" * 60
    result = excerpt_philosophy(intro)
    assert result == "가" * 40 + "..."


def test_excerpt_philosophy_splits_on_newline_when_no_period():
    intro = "첫줄 문구\n둘째줄은 무시"
    result = excerpt_philosophy(intro)
    assert result == "첫줄 문구"


def test_excerpt_philosophy_handles_none_and_empty():
    assert excerpt_philosophy(None) == ""
    assert excerpt_philosophy("") == ""
