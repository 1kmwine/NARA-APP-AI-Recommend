import pytest

from app.services.images import (
    InvalidPdataId,
    InvalidVariant,
    _detect_image_mime,
    build_nas1_url,
    validate_pdata_id,
)


def test_build_nas1_url_for_removebg_variant():
    url = build_nas1_url(
        pdata_id="00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        variant="removebg",
        base_url="http://el.naracellar.com/share.cgi",
        ssid="f654b5f10f3c4439bf8a19229f9bf8a7",
    )
    assert url.startswith("http://el.naracellar.com/share.cgi?")
    assert "ssid=f654b5f10f3c4439bf8a19229f9bf8a7" in url
    assert "path=%2Fremovebg" in url
    assert "filename=00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5" in url


def test_build_nas1_url_for_origin_variant_has_empty_path():
    url = build_nas1_url(
        pdata_id="00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        variant="origin",
        base_url="http://el.naracellar.com/share.cgi",
        ssid="abc",
    )
    assert "path=&" in url or url.endswith("path=")


def test_build_nas1_url_rejects_unknown_variant():
    with pytest.raises(InvalidVariant):
        build_nas1_url(
            pdata_id="00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
            variant="huge",
            base_url="http://x",
            ssid="x",
        )


def test_validate_pdata_id_accepts_correct_format():
    validate_pdata_id("00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5")  # 예외 없이 통과


def test_validate_pdata_id_rejects_bad_format():
    with pytest.raises(InvalidPdataId):
        validate_pdata_id("../../etc/passwd")


def test_validate_pdata_id_rejects_trailing_newline():
    with pytest.raises(InvalidPdataId):
        validate_pdata_id("00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5\n")


def test_detect_image_mime_recognizes_png():
    assert _detect_image_mime(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20) == "image/png"


def test_detect_image_mime_recognizes_jpeg():
    assert _detect_image_mime(b"\xff\xd8\xff" + b"\x00" * 20) == "image/jpeg"


def test_detect_image_mime_recognizes_webp():
    content = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 20
    assert _detect_image_mime(content) == "image/webp"


def test_detect_image_mime_falls_back_for_unknown_bytes():
    assert _detect_image_mime(b"not an image") == "application/octet-stream"
