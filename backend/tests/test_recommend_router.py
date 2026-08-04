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
    """요청 티어(3="5만원대")에 후보가 없어서 폴백으로 다른 티어(68000원="7만원대")
    후보가 나왔을 때, price_desc는 실제 후보 가격 기준이어야 한다."""
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
    assert body["price_desc"] == "7만원대"
