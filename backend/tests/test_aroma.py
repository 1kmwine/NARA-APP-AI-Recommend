import json
from unittest.mock import MagicMock

from app.services.aroma import classify_aroma_tags, fetch_aroma_tags


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


def test_fetch_aroma_tags_returns_dict_keyed_by_pdata_id():
    fake_conn = MagicMock()
    fake_conn.execute.return_value.mappings.return_value.all.return_value = [
        {"pdata_id": "P1", "aroma": json.dumps(["Cherry", "Vanilla"])},
        {"pdata_id": "P2", "aroma": json.dumps(["Violet"])},
    ]
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_engine = MagicMock()
    fake_engine.connect.return_value = fake_conn

    result = fetch_aroma_tags(fake_engine, ["P1", "P2"])

    assert result == {"P1": ["Cherry", "Vanilla"], "P2": ["Violet"]}


def test_fetch_aroma_tags_empty_pdata_ids_returns_empty_dict_without_querying():
    fake_engine = MagicMock()
    result = fetch_aroma_tags(fake_engine, [])
    assert result == {}
    fake_engine.connect.assert_not_called()


def test_fetch_aroma_tags_skips_malformed_json():
    fake_conn = MagicMock()
    fake_conn.execute.return_value.mappings.return_value.all.return_value = [
        {"pdata_id": "P1", "aroma": "not valid json"},
        {"pdata_id": "P2", "aroma": json.dumps(["Rose"])},
    ]
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_engine = MagicMock()
    fake_engine.connect.return_value = fake_conn

    result = fetch_aroma_tags(fake_engine, ["P1", "P2"])

    assert result == {"P2": ["Rose"]}
