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
