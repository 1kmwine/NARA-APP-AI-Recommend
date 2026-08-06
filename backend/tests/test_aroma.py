from app.services.aroma import classify_aroma_tags


def test_classify_aroma_tags_fruit_dominant():
    tags = ["Blackcurrant", "Raspberry", "Cherry", "Vanilla"]
    assert classify_aroma_tags(tags) == "fruit"


def test_classify_aroma_tags_floral_tertiary_dominant():
    tags = ["Violet", "Leather", "Tobacco", "Mushroom"]
    assert classify_aroma_tags(tags) == "floral_tertiary"


def test_classify_aroma_tags_tie_breaks_to_fruit():
    # 과일 2개, 비과일 2개로 동점이면 "fruit"로 정한다(임의지만 결정적이어야 함)
    tags = ["Cherry", "Plum", "Leather", "Smoke"]
    assert classify_aroma_tags(tags) == "fruit"


def test_classify_aroma_tags_empty_list_defaults_to_fruit():
    assert classify_aroma_tags([]) == "fruit"


def test_classify_aroma_tags_unknown_tags_ignored():
    # 매핑에 없는 태그는 무시하고, 알려진 태그만으로 판단
    tags = ["SomeUnknownTag123", "Rose", "Violet"]
    assert classify_aroma_tags(tags) == "floral_tertiary"
