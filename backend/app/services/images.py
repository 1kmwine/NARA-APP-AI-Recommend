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
    if not PDATA_ID_PATTERN.match(pdata_id):
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
