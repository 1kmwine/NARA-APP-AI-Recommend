from typing import Callable

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


StoryVerifyFn = Callable[[str], str | None]


def pick_story_match(
    pool: list[dict], articles_by_brand: dict[str, list[dict]], verify_fn: StoryVerifyFn
) -> tuple[tuple[dict, str | None, str | None], tuple[dict, str | None, str | None]] | None:
    """기사가 있는 브랜드 중 실제 인물/행사 언급이 검증된 후보를 우선으로 찾는다.
    검증된 후보가 2개 미만이면, 브랜드만 다른 나머지 후보로 남은 자리를 채운다
    (quote/url은 None — 없는 이야기를 지어내지 않는다, 대신 경기 자체는 후보만
    있으면 항상 채운다). 서로 다른 브랜드가 풀에 2개 미만이면 그때만 None(경기
    자체를 못 만듦)."""
    verified: list[tuple[dict, str, str]] = []
    tried_brands: set[str] = set()
    unverified_candidates: list[dict] = []
    for candidate in pool:
        brand = candidate.get("brandName")
        if not brand or brand in tried_brands:
            continue
        articles = articles_by_brand.get(brand)
        if not articles:
            unverified_candidates.append(candidate)
            tried_brands.add(brand)
            continue
        tried_brands.add(brand)
        quote = verify_fn(articles[0]["excerpt"] or articles[0]["title"])
        if quote is None:
            unverified_candidates.append(candidate)
            continue
        verified.append((candidate, quote, articles[0]["url"]))
        if len(verified) == 2:
            return verified[0], verified[1]

    fallback: list[tuple[dict, str | None, str | None]] = list(verified)
    for candidate in unverified_candidates:
        fallback.append((candidate, None, None))
        if len(fallback) == 2:
            break

    if len(fallback) < 2:
        return None
    return fallback[0], fallback[1]


PhilosophySummarizeFn = Callable[[str], str | None]


def pick_philosophy_match(
    pool: list[dict], intro_by_brand: dict[str, str], summarize_fn: PhilosophySummarizeFn
) -> tuple[tuple[dict, str], tuple[dict, str]] | None:
    """소개글 있는 브랜드 중 요약 생성에 성공한 후보 2개(서로 다른 브랜드)를 찾는다.
    각 결과는 (카드, 철학 문구) 튜플."""
    found: list[tuple[dict, str]] = []
    seen_brands: set[str] = set()
    for candidate in pool:
        brand = candidate.get("brandName")
        if not brand or brand in seen_brands:
            continue
        intro = intro_by_brand.get(brand)
        if not intro:
            continue
        summary = summarize_fn(intro)
        if summary is None:
            continue
        found.append((candidate, summary))
        seen_brands.add(brand)
        if len(found) == 2:
            return found[0], found[1]
    return None
