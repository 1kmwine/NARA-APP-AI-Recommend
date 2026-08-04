from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_images_returns_400_for_invalid_pdata_id():
    response = client.get("/api/images/not-valid", params={"variant": "thumb"})
    assert response.status_code == 400


def test_images_returns_400_for_invalid_variant():
    response = client.get(
        "/api/images/00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        params={"variant": "huge"},
    )
    assert response.status_code == 400


def test_images_streams_bytes_on_success():
    with patch("app.routers.images.fetch_image_bytes", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (b"\x89PNGfakebytes", "image/png")
        response = client.get(
            "/api/images/00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
            params={"variant": "removebg"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNGfakebytes"


def test_images_returns_502_when_nas_fetch_fails():
    with patch("app.routers.images.fetch_image_bytes", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = httpx.ConnectError("boom")
        response = client.get(
            "/api/images/00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
            params={"variant": "thumb"},
        )
    assert response.status_code == 502
