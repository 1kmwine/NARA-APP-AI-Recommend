from app.services.aroma import classify_aroma_tags


def _acidity(candidate: dict) -> int:
    taste = candidate.get("taste") or {}
    return taste.get("acidity", 2)


def pick_acidity_match(pool: list[dict]) -> tuple[dict, dict] | None:
    """산도 최댓값/최솟값 후보 한 쌍을 뽑는다. 풀에 서로 다른 후보가 2개 미만이면
    None(1경기 자체를 못 만든다는 뜻 — 호출 측이 브라켓 전체를 4경기 미만으로
    줄이거나 에러 처리한다)."""
    if len(pool) < 2:
        return None
    sorted_pool = sorted(pool, key=_acidity)
    return sorted_pool[-1], sorted_pool[0]


def pick_aroma_match(pool: list[dict], aroma_by_pdata_id: dict[str, list[str]]) -> tuple[dict, dict] | None:
    """과일향 후보 하나, 꽃·2,3차향 후보 하나를 뽑는다. 아로마 데이터가 없는
    후보(pdataId 없음 또는 조회 결과에 없음)는 건너뛴다. 둘 중 한쪽이라도 없으면
    None."""
    fruit_candidates = []
    floral_candidates = []
    for c in pool:
        pdata_id = c.get("pdataId")
        if not pdata_id or pdata_id not in aroma_by_pdata_id:
            continue
        tags = aroma_by_pdata_id[pdata_id]
        if classify_aroma_tags(tags) == "fruit":
            fruit_candidates.append(c)
        else:
            floral_candidates.append(c)
    if not fruit_candidates or not floral_candidates:
        return None
    return fruit_candidates[0], floral_candidates[0]


def exclude_used(pool: list[dict], used_item_cds: set[str]) -> list[dict]:
    return [c for c in pool if c["itemCd"] not in used_item_cds]
