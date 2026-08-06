from typing import Callable

from app.routers.recommend import _to_card
from app.schemas import BracketCard, BracketMatch, BracketResponse
from app.services.aroma import classify_aroma_tags
from app.services.region_cache import CountryRegions


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


PoolSearchFn = Callable[[str, str, int, int | None], list[dict]]


def build_candidate_pool(
    order: list[CountryRegions],
    country_index: int,
    region_index: int,
    min_size: int,
    search_fn: PoolSearchFn,
    price_min: int = 0,
    price_max: int | None = None,
) -> list[dict]:
    """사용자가 고른 지역부터 시작해서, 후보가 min_size를 채울 때까지 같은 타입
    내 다른 지역을 순서대로 추가한다(region_cache 순서 재사용 — SKU 많은 지역
    순). item_cd 기준 dedupe."""
    country_entry = order[country_index % len(order)]
    n_regions = len(country_entry.regions)
    seen: set[str] = set()
    pool: list[dict] = []
    for offset in range(n_regions):
        region_entry = country_entry.regions[(region_index + offset) % n_regions]
        results = search_fn(country_entry.country, region_entry.label, price_min, price_max)
        for r in results:
            if r["itemCd"] in seen:
                continue
            seen.add(r["itemCd"])
            pool.append(r)
        if len(pool) >= min_size:
            break
    return pool


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


def _to_bracket_card(candidate: dict, axis_label: str) -> BracketCard:
    base = _to_card(candidate)
    return BracketCard(**base.model_dump(), axis_label=axis_label)


def build_bracket(
    pool: list[dict],
    aroma_by_pdata_id: dict[str, list[str]],
    articles_by_brand: dict[str, list[dict]],
    intro_by_brand: dict[str, str],
    verify_fn: StoryVerifyFn,
    summarize_fn: PhilosophySummarizeFn,
) -> BracketResponse:
    """4경기를 순서대로 조립한다. 각 경기는 이미 쓰인 item_cd를 제외한 풀에서
    후보를 뽑는다 — 경기 하나가 후보를 못 찾으면(None) 그 경기는 대진표에서
    빠진다(4경기 미만이 될 수 있음, 프론트가 이 경우도 처리해야 함)."""
    matches: list[BracketMatch] = []
    used: set[str] = set()
    remaining = pool

    acidity_pair = pick_acidity_match(remaining)
    if acidity_pair:
        high, low = acidity_pair
        used.update([high["itemCd"], low["itemCd"]])
        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="acidity",
                cards=[
                    _to_bracket_card(high, f"산도 {(high.get('taste') or {}).get('acidity', 2)}/5"),
                    _to_bracket_card(low, f"산도 {(low.get('taste') or {}).get('acidity', 2)}/5"),
                ],
            )
        )
    remaining = exclude_used(remaining, used)

    aroma_pair = pick_aroma_match(remaining, aroma_by_pdata_id)
    if aroma_pair:
        fruit, floral = aroma_pair
        used.update([fruit["itemCd"], floral["itemCd"]])
        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="aroma",
                cards=[
                    _to_bracket_card(fruit, "과일향 위주"),
                    _to_bracket_card(floral, "꽃·2,3차향 위주"),
                ],
            )
        )
    remaining = exclude_used(remaining, used)

    story_pair = pick_story_match(remaining, articles_by_brand, verify_fn)
    if story_pair:
        (card_a, quote_a, url_a), (card_b, quote_b, url_b) = story_pair
        used.update([card_a["itemCd"], card_b["itemCd"]])

        def _story_label(quote: str | None, url: str | None) -> str:
            if quote:
                return f"{quote} (출처: {url})"
            return "이 와인만의 알려진 이야기는 아직 없어요"

        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="story",
                cards=[
                    _to_bracket_card(card_a, _story_label(quote_a, url_a)),
                    _to_bracket_card(card_b, _story_label(quote_b, url_b)),
                ],
            )
        )
    remaining = exclude_used(remaining, used)

    philosophy_pair = pick_philosophy_match(remaining, intro_by_brand, summarize_fn)
    if philosophy_pair:
        (card_a, summary_a), (card_b, summary_b) = philosophy_pair
        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="philosophy",
                cards=[
                    _to_bracket_card(card_a, summary_a),
                    _to_bracket_card(card_b, summary_b),
                ],
            )
        )

    return BracketResponse(matches=matches)
