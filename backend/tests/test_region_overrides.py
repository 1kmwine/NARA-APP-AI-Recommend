from app.services.region_overrides import (
    canonical_country_from_votes,
    extract_raw_region,
    normalize_region_label,
    region_to_country,
)


def test_region_to_country_known_region():
    assert region_to_country("부르고뉴") == "France"


def test_region_to_country_unknown_region_returns_none():
    assert region_to_country("존재안함지역") is None


def test_normalize_region_label_applies_alias():
    assert normalize_region_label("나파밸리") == "캘리포니아"


def test_normalize_region_label_applies_expand_after_alias():
    assert normalize_region_label("라펠 밸리") == "센트럴 밸리"


def test_normalize_region_label_passthrough_when_no_mapping():
    assert normalize_region_label("피에몬테") == "피에몬테"


def test_extract_raw_region_from_place_json():
    assert extract_raw_region('{"ko": "보르도", "en": "Bordeaux"}') == "보르도"


def test_extract_raw_region_handles_missing_or_invalid_json():
    assert extract_raw_region(None) == ""
    assert extract_raw_region("") == ""
    assert extract_raw_region("not json") == ""


def test_canonical_country_from_votes_majority_wins():
    result = canonical_country_from_votes(["France", "France", "Germany"], "Korea")
    assert result == "France"


def test_canonical_country_from_votes_falls_back_when_no_votes():
    result = canonical_country_from_votes([None, None], "Italy")
    assert result == "Italy"


def test_canonical_country_from_votes_falls_back_to_기타_when_nothing():
    result = canonical_country_from_votes([None], None)
    assert result == "기타"
