import json
from typing import Literal

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

# tb_pdata.aroma에 실제로 나오는 영어 태그(2026-08-06 샘플 확인) 기준 분류.
# 과일류(1차 향)는 fruit, 꽃/오크/숙성/향신료 등 2·3차 향은 floral_tertiary.
FRUIT_TAGS = {
    "blackcurrant", "blackberry", "raspberry", "strawberry", "cherry", "plum",
    "prune", "fig", "pineapple", "banana", "grapefruit", "orange peel", "peach",
    "apple", "lemon", "lime", "apricot", "melon", "grape", "citrus", "tropical fruit",
    "red fruit", "black fruit", "stone fruit",
}
FLORAL_TERTIARY_TAGS = {
    "violet", "rose", "jasmine", "vanilla", "leather", "tobacco", "mushroom",
    "cloves", "nutmeg", "cedar", "smoke", "toast", "chocolate", "coffee", "earth",
    "mineral", "herb", "pepper", "licorice", "liquorice", "honey", "butter",
    "oak", "truffle", "game", "forest floor", "wet stone",
}

Aroma = Literal["fruit", "floral_tertiary"]


def classify_aroma_tags(tags: list[str]) -> Aroma:
    """아로마 태그 목록을 과일향/꽃·2,3차향 둘 중 하나로 분류한다.
    알려진 태그 수를 세어 많은 쪽으로 정하고, 동점이거나 알려진 태그가 없으면
    "fruit"으로 기본값을 준다(결정적 동작이 필요해서 임의 우선순위를 둠)."""
    fruit_count = 0
    floral_count = 0
    for tag in tags:
        if not isinstance(tag, str):
            continue
        normalized = tag.strip().lower()
        if normalized in FRUIT_TAGS:
            fruit_count += 1
        elif normalized in FLORAL_TERTIARY_TAGS:
            floral_count += 1
    if floral_count > fruit_count:
        return "floral_tertiary"
    return "fruit"


def fetch_aroma_tags(pos_engine: Engine, pdata_ids: list[str]) -> dict[str, list[str]]:
    """pos.tb_pdata.aroma를 pdata_id 목록으로 한 번에 조회한다. aroma가 JSON 배열이
    아니면(파싱 실패) 그 pdata_id는 결과에서 빠진다 — 호출 측이 "이 후보는 아로마
    정보 없음"으로 취급하면 된다."""
    if not pdata_ids:
        return {}
    stmt = text("SELECT pdata_id, aroma FROM tb_pdata WHERE pdata_id IN :pdata_ids").bindparams(
        bindparam("pdata_ids", expanding=True)
    )
    with pos_engine.connect() as conn:
        rows = conn.execute(stmt, {"pdata_ids": list(pdata_ids)}).mappings().all()
    result: dict[str, list[str]] = {}
    for row in rows:
        try:
            tags = json.loads(row["aroma"])
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(tags, list):
            result[row["pdata_id"]] = tags
    return result
