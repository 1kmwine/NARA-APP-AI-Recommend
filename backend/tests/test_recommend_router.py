from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_recommend_returns_card_when_candidate_found():
    fake_candidate = {
        "itemCd": "ABC123",
        "nameKo": "테스트 와인",
        "type": "Red",
        "producer": '{"ko": "테스트 와이너리", "en": "Test Winery"}',
        "variety": '{"ko": "피노누아", "en": "Pinot Noir"}',
        "country": '{"ko": "프랑스", "en": "France"}',
        "place": '{"ko": "부르고뉴", "en": "Burgundy"}',
        "taste_raw": '{"sweetness": 1, "acidity": 3, "body": 3, "tannin": 3}',
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": "00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        "price_krw": 45000,
        "reviews": 2,
        "wishes": 5,
    }
    with patch("app.routers.recommend.query_candidates", return_value=[fake_candidate]):
        response = client.get(
            "/api/recommend",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["wine_name"] == "테스트 와인"
    assert body["region"] == "부르고뉴"
    assert body["price_krw"] == 45000


def test_recommend_returns_404_when_no_candidate_even_after_fallback():
    with patch("app.routers.recommend.query_candidates", return_value=[]):
        response = client.get(
            "/api/recommend",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 404


def test_recommend_price_desc_reflects_actual_candidate_price_not_requested_tier():
    """요청 티어(3, 검색 버킷 30001~50000원)에 후보가 없어서 폴백으로 그 버킷 밖
    가격(68000원)의 후보가 나왔을 때, price_desc는 검색 버킷 라벨이 아니라 실제
    가격의 만원 단위("6만원대")를 정직하게 보여줘야 한다."""
    fallback_candidate = {
        "itemCd": "XYZ789",
        "nameKo": "폴백 와인",
        "type": "Red",
        "producer": "{}",
        "variety": "{}",
        "country": "{}",
        "place": "{}",
        "taste_raw": None,
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": None,
        "price_krw": 68_000,
        "reviews": 0,
        "wishes": 0,
    }
    # widen_tier_ranges(3) == [(30001,50000), (20001,70000), ...] — 68000은 두번째
    # 범위(20001-70000)에 이미 들어가므로 첫 호출(정확한 티어)만 비고, 두번째 호출에서
    # 바로 후보가 반환된다.
    with patch(
        "app.routers.recommend.query_candidates",
        side_effect=[[], [fallback_candidate]],
    ):
        response = client.get(
            "/api/recommend",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["price_krw"] == 68_000
    assert body["price_desc"] == "6만원대"


def _candidate(item_cd: str, taste: dict, price_krw: int = 45000) -> dict:
    # 라우터가 taste_raw(JSON 문자열)를 파싱해서 candidate["taste"]를 직접 계산하므로
    # (recommend.py의 `c["taste"] = _parse_json_field(...)` 루프), 여기서 "taste" 키를
    # 바로 넣어도 라우터가 그걸 덮어써버린다 — taste_raw에 JSON으로 넣어야 실제로 반영됨.
    import json as _json

    return {
        "itemCd": item_cd,
        "nameKo": f"와인 {item_cd}",
        "type": "Red",
        "producer": "{}",
        "variety": "{}",
        "country": "{}",
        "place": "{}",
        "taste_raw": _json.dumps(taste),
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": None,
        "price_krw": price_krw,
        "reviews": 0,
        "wishes": 0,
    }


def test_recommend_response_includes_taste_vector():
    fake_candidate = {
        "itemCd": "ABC123",
        "nameKo": "테스트 와인",
        "type": "Red",
        "producer": "{}",
        "variety": "{}",
        "country": "{}",
        "place": "{}",
        "taste_raw": '{"sweetness": 1, "acidity": 3, "body": 4, "tannin": 2}',
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": None,
        "price_krw": 45000,
        "reviews": 0,
        "wishes": 0,
    }
    with patch("app.routers.recommend.query_candidates", return_value=[fake_candidate]):
        response = client.get(
            "/api/recommend",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 200
    assert response.json()["taste"] == {"sweetness": 1, "acidity": 3, "body": 4, "tannin": 2}


def test_recommend_excludes_item_cds_passed_in_exclude_param():
    excluded = _candidate("EXCLUDED", {"sweetness": 2, "acidity": 2, "body": 2, "tannin": 2})
    kept = _candidate("KEPT", {"sweetness": 2, "acidity": 2, "body": 2, "tannin": 2})
    with patch(
        "app.routers.recommend.query_candidates", return_value=[excluded, kept]
    ):
        response = client.get(
            "/api/recommend",
            params={
                "price_tier": 3,
                "country_index": 0,
                "region_index": 0,
                "wine_type": "Red",
                "exclude": "EXCLUDED",
                "slot": 0,
            },
        )
    assert response.status_code == 200
    assert response.json()["item_cd"] == "KEPT"


def test_recommend_returns_404_when_all_candidates_excluded_after_fallback_exhausted():
    excluded = _candidate("EXCLUDED", {"sweetness": 2, "acidity": 2, "body": 2, "tannin": 2})
    with patch("app.routers.recommend.query_candidates", return_value=[excluded]):
        response = client.get(
            "/api/recommend",
            params={
                "price_tier": 0,
                "country_index": 0,
                "region_index": 0,
                "wine_type": "Red",
                "exclude": "EXCLUDED",
            },
        )
    assert response.status_code == 404


def test_recommend_liked_taste_reorders_toward_liked_wine():
    close = _candidate("CLOSE", {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 1})
    far = _candidate("FAR", {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5})
    with patch(
        "app.routers.recommend.query_candidates", return_value=[far, close]
    ):
        response = client.get(
            "/api/recommend",
            params={
                "price_tier": 3,
                "country_index": 0,
                "region_index": 0,
                "wine_type": "Red",
                "liked_taste": "1,4,2,1",
                "slot": 0,
            },
        )
    assert response.status_code == 200
    assert response.json()["item_cd"] == "CLOSE"
