import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import WineCard
from app.services.pairing import infer_taste_target, score_by_pairing
from app.services.price_tiers import price_tier_for_amount, tier_label
from app.services.recommend import find_with_fallback, pick_top_candidates, query_candidates
from app.services.region_cache import region_cache

router = APIRouter(prefix="/api")

TYPE_LABEL_KR = {"Red": "레드", "White": "화이트", "Sparkling": "스파클링"}

PAIR_REASON_KR = {
    "Red": "육즙이랑 타닌이 딱 물려요",
    "White": "산미가 재료 감칠맛을 확 살려줘요",
    "Sparkling": "입안이 개운하게 리셋돼요",
}


def _parse_json_field(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _to_card(candidate: dict) -> WineCard:
    variety = _parse_json_field(candidate.get("variety"))
    country = _parse_json_field(candidate.get("country"))
    place = _parse_json_field(candidate.get("place"))
    wine_type = candidate.get("type") or "Red"

    tasting_note = candidate.get("tastingNote")
    note = tasting_note or candidate.get("desc1") or "이 와인만의 매력이 있어요."

    return WineCard(
        item_cd=candidate["itemCd"],
        wine_name=candidate.get("nameKo") or candidate["itemCd"],
        region=place.get("ko", "") or "산지 미상",
        country=country.get("ko", "") or "국가 미상",
        grape=variety.get("ko", "") or "품종 미상",
        type_label_kr=TYPE_LABEL_KR.get(wine_type, wine_type),
        price_krw=candidate["price_krw"],
        price_desc=tier_label(price_tier_for_amount(candidate["price_krw"])),
        note=note[:80],
        persona_line=f"{candidate.get('nameKo', '이 와인')}, 지금 이 순간에 잘 어울려요",
        pdata_id=candidate.get("pdataId"),
    )


@router.get("/recommend", response_model=WineCard)
def recommend(
    price_tier: int = Query(ge=0, le=9),
    country_index: int = Query(ge=0),
    region_index: int = Query(ge=0),
    wine_type: str = Query(...),
    pairing_text: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> WineCard:
    order = region_cache.get(session)
    if not order:
        raise HTTPException(status_code=503, detail="지역 데이터 아직 준비 안 됨")

    country_entry = order[country_index % len(order)]
    region_entry = country_entry.regions[region_index % len(country_entry.regions)]

    def search(price_min: int, price_max: int | None) -> list[dict]:
        return query_candidates(
            session, wine_type, country_entry.country, region_entry.label, price_min, price_max
        )

    candidates = find_with_fallback(price_tier, search)
    if not candidates:
        raise HTTPException(status_code=404, detail="추천할 와인을 찾지 못함")

    for c in candidates:
        c["taste"] = _parse_json_field(c.get("notes_taste_raw")) or _parse_json_field(
            c.get("taste_raw")
        )

    if pairing_text:
        target = infer_taste_target(pairing_text)
        candidates = score_by_pairing(candidates, target)
        reason = PAIR_REASON_KR.get(wine_type, "잘 어울려요")
        top = pick_top_candidates(candidates, limit=1)[0]
        card = _to_card(top)
        card.persona_line = f"{card.wine_name}, {pairing_text}이랑 같이면 {reason}"
        return card

    top = pick_top_candidates(candidates, limit=1)[0]
    return _to_card(top)
