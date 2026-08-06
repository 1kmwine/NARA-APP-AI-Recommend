from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session, pos_engine
from app.routers.recommend import _parse_json_field
from app.schemas import BracketResponse
from app.services.aroma import fetch_aroma_tags
from app.services.bracket import build_bracket, build_candidate_pool
from app.services.bracket_content import summarize_philosophy, verify_story_mention
from app.services.brand_content import fetch_brand_articles, fetch_brand_intro
from app.services.pairing import infer_taste_target, score_by_pairing
from app.services.price_tiers import widen_tier_ranges
from app.services.recommend import query_candidates
from app.services.region_cache import region_cache

router = APIRouter(prefix="/api")

POOL_MIN_SIZE = 24


@router.get("/bracket", response_model=BracketResponse)
def bracket(
    price_tier: int = Query(ge=0, le=9),
    country_index: int = Query(ge=0),
    region_index: int = Query(ge=0),
    wine_type: str = Query(...),
    pairing_text: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> BracketResponse:
    order = region_cache.get(session, wine_type)
    if not order:
        raise HTTPException(status_code=503, detail="지역 데이터 아직 준비 안 됨")

    price_min, price_max = widen_tier_ranges(price_tier)[0]

    def search(country: str, region: str, p_min: int, p_max: int | None) -> list[dict]:
        return query_candidates(session, wine_type, country, region, p_min, p_max)

    pool = build_candidate_pool(
        order=order,
        country_index=country_index,
        region_index=region_index,
        min_size=POOL_MIN_SIZE,
        search_fn=search,
        price_min=price_min,
        price_max=price_max,
    )
    if not pool:
        raise HTTPException(status_code=404, detail="추천할 와인을 찾지 못함")

    for c in pool:
        c["taste"] = _parse_json_field(c.get("notes_taste_raw")) or _parse_json_field(
            c.get("taste_raw")
        )

    if pairing_text:
        target = infer_taste_target(pairing_text)
        pool = score_by_pairing(pool, target)

    top_pool = pool[:30]

    pdata_ids = [c["pdataId"] for c in top_pool if c.get("pdataId")]
    aroma_by_pdata_id = fetch_aroma_tags(pos_engine, pdata_ids)

    brand_names = list({c["brandName"] for c in top_pool if c.get("brandName")})
    articles_by_brand = fetch_brand_articles(session, brand_names)
    intro_by_brand = fetch_brand_intro(session, brand_names)

    return build_bracket(
        pool=top_pool,
        aroma_by_pdata_id=aroma_by_pdata_id,
        articles_by_brand=articles_by_brand,
        intro_by_brand=intro_by_brand,
        verify_fn=verify_story_mention,
        summarize_fn=summarize_philosophy,
    )
