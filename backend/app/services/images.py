import re
from urllib.parse import urlencode

PDATA_ID_PATTERN = re.compile(r"^[0-9]{8}_[0-9a-f-]{36}$")

# nas-image.php의 $ALLOWED_VARIANTS 그대로 포팅.
ALLOWED_VARIANTS: dict[str, str] = {
    "origin": "",
    "thumb": "/thumb",
    "square": "/square",
    "removebg": "/removebg",
    "opengraph": "/opengraph",
}


class InvalidPdataId(ValueError):
    pass


class InvalidVariant(ValueError):
    pass


def validate_pdata_id(pdata_id: str) -> None:
    if not PDATA_ID_PATTERN.fullmatch(pdata_id):
        raise InvalidPdataId(f"invalid pdataId: {pdata_id!r}")


def build_nas1_url(pdata_id: str, variant: str, base_url: str, ssid: str) -> str:
    validate_pdata_id(pdata_id)
    if variant not in ALLOWED_VARIANTS:
        raise InvalidVariant(f"invalid variant: {variant!r}")

    path = ALLOWED_VARIANTS[variant]
    query = urlencode(
        {
            "ssid": ssid,
            "openfolder": "forcedownload",
            "ep": "",
            "fid": ssid,
            "filename": pdata_id,
            "path": path,
        }
    )
    return f"{base_url}?{query}"


import httpx

from app.config import settings

# QNAP 공유링크(share.cgi)는 항상 Content-Type: application/force-download로 내려준다
# (NAS-image.php 원본 코드 주석 참고 — QNAP 공유 링크의 고정 동작, 변경 불가). 그래서
# NAS 응답 헤더를 그대로 믿으면 <img>가 못 그린다 — PHP 원본은 finfo(매직바이트)로
# 실제 타입을 재감지해서 내려준다. 여기선 이 앱이 실제로 받는 포맷(PNG/JPEG/GIF/WEBP)
# 몇 개만 매직바이트로 직접 판별한다(python-magic 같은 libmagic 바인딩 새로 안 붙임).
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def _detect_image_mime(content: bytes) -> str:
    for signature, mime in _MAGIC_SIGNATURES:
        if content.startswith(signature):
            return mime
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


async def fetch_image_bytes(pdata_id: str, variant: str) -> tuple[bytes, str]:
    url = build_nas1_url(pdata_id, variant, settings.nas1_base_url, settings.nas1_share_ssid)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
    response.raise_for_status()
    content_type = _detect_image_mime(response.content)
    return response.content, content_type
