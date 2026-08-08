from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _candidate(item_cd: str, acidity: int, brand: str, pdata_id: str | None = None) -> dict:
    import json

    return {
        "itemCd": item_cd,
        "nameKo": f"와인 {item_cd}",
        "type": "Red",
        "producer": "{}",
        "variety": "{}",
        "country": "{}",
        "place": "{}",
        "taste_raw": json.dumps({"sweetness": 2, "acidity": acidity, "body": 2, "tannin": 2}),
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": pdata_id,
        "price_krw": 30000,
        "reviews": 0,
        "wishes": 0,
        "brandName": brand,
    }


def test_bracket_endpoint_returns_matches():
    pool = [_candidate("A", 5, "b1"), _candidate("B", 0, "b2")]
    with (
        patch("app.routers.bracket.query_candidates", return_value=pool),
        patch("app.routers.bracket.fetch_aroma_tags", return_value={}),
        patch("app.routers.bracket.fetch_brand_articles", return_value={}),
        patch("app.routers.bracket.fetch_brand_intro", return_value={}),
    ):
        response = client.get(
            "/api/bracket",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["axis"] == "acidity"


def test_bracket_endpoint_returns_404_when_pool_empty():
    with (
        patch("app.routers.bracket.query_candidates", return_value=[]),
        patch("app.routers.bracket.fetch_aroma_tags", return_value={}),
        patch("app.routers.bracket.fetch_brand_articles", return_value={}),
        patch("app.routers.bracket.fetch_brand_intro", return_value={}),
    ):
        response = client.get(
            "/api/bracket",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 404


def test_bracket_endpoint_returns_404_when_pool_has_only_one_candidate():
    """후보 1개뿐이면 어떤 pick_*_match도 매치를 못 만들어 matches: []인 200이
    나가버린다 — 프론트가 이걸 에러로 인식 못 해 빈 화면만 뜨므로, 매치 성립이
    애초에 불가능한 크기(<2)는 여기서 바로 404 처리한다."""
    with (
        patch("app.routers.bracket.query_candidates", return_value=[_candidate("A", 5, "b1")]),
        patch("app.routers.bracket.fetch_aroma_tags", return_value={}),
        patch("app.routers.bracket.fetch_brand_articles", return_value={}),
        patch("app.routers.bracket.fetch_brand_intro", return_value={}),
    ):
        response = client.get(
            "/api/bracket",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 404
