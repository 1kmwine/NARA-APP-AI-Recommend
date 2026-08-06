import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import WineCard, WineTaste
from app.services.pairing import TasteVector, infer_taste_target, score_by_pairing, score_by_preference
from app.services.price_tiers import format_price_desc
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


def _parse_taste_param(raw: str | None) -> TasteVector | None:
    """프론트에서 "sweetness,acidity,body,tannin" 형태(예: "3,2,4,1")로 보내는
    좋아요/배제 평균 취향 벡터를 파싱한다. 형식이 안 맞으면 신호가 없는 것으로
    취급한다(없어도 추천 자체는 그냥 기존 순위로 동작해야 함)."""
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 4:
        return None
    try:
        sweetness, acidity, body, tannin = (int(p) for p in parts)
    except ValueError:
        return None
    return TasteVector(sweetness=sweetness, acidity=acidity, body=body, tannin=tannin)


def _to_card(candidate: dict) -> WineCard:
    variety = _parse_json_field(candidate.get("variety"))
    country = _parse_json_field(candidate.get("country"))
    place = _parse_json_field(candidate.get("place"))
    wine_type = candidate.get("type") or "Red"

    tasting_note = candidate.get("tastingNote")
    note = tasting_note or candidate.get("desc1") or "이 와인만의 매력이 있어요."

    taste_raw = candidate.get("taste") or {}

    return WineCard(
        item_cd=candidate["itemCd"],
        wine_name=candidate.get("nameKo") or candidate["itemCd"],
        region=place.get("ko", "") or "산지 미상",
        country=country.get("ko", "") or "국가 미상",
        grape=variety.get("ko", "") or "품종 미상",
        type_label_kr=TYPE_LABEL_KR.get(wine_type, wine_type),
        price_krw=candidate["price_krw"],
        price_desc=format_price_desc(candidate["price_krw"]),
        note=note[:80],
        persona_line=f"{candidate.get('nameKo', '이 와인')}, 지금 이 순간에 잘 어울려요",
        pdata_id=candidate.get("pdataId"),
        taste=WineTaste(
            sweetness=taste_raw.get("sweetness", 2),
            acidity=taste_raw.get("acidity", 2),
            body=taste_raw.get("body", 2),
            tannin=taste_raw.get("tannin", 2),
        ),
    )


@router.get("/recommend", response_model=WineCard)
def recommend(
    price_tier: int = Query(ge=0, le=9),
    country_index: int = Query(ge=0),
    region_index: int = Query(ge=0),
    wine_type: str = Query(...),
    pairing_text: str | None = Query(default=None),
    slot: int = Query(default=0, ge=0, le=1),
    exclude: str = Query(default=""),
    liked_taste: str | None = Query(default=None),
    disliked_taste: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> WineCard:
    order = region_cache.get(session, wine_type)
    if not order:
        raise HTTPException(status_code=503, detail="지역 데이터 아직 준비 안 됨")

    country_entry = order[country_index % len(order)]
    region_entry = country_entry.regions[region_index % len(country_entry.regions)]

    excluded_item_cds = {c.strip() for c in exclude.split(",") if c.strip()}

    def search(price_min: int, price_max: int | None) -> list[dict]:
        results = query_candidates(
            session, wine_type, country_entry.country, region_entry.label, price_min, price_max
        )
        return [c for c in results if c["itemCd"] not in excluded_item_cds]

    candidates = find_with_fallback(price_tier, search)
    if not candidates:
        raise HTTPException(status_code=404, detail="추천할 와인을 찾지 못함")

    for c in candidates:
        c["taste"] = _parse_json_field(c.get("notes_taste_raw")) or _parse_json_field(
            c.get("taste_raw")
        )

    persona_suffix: str | None = None
    if pairing_text:
        target = infer_taste_target(pairing_text)
        ranked = score_by_pairing(candidates, target)
        reason = PAIR_REASON_KR.get(wine_type, "잘 어울려요")
        persona_suffix = f"{pairing_text}이랑 같이면 {reason}"
        top_list = ranked[:2]
    else:
        liked = _parse_taste_param(liked_taste)
        disliked = _parse_taste_param(disliked_taste)
        if liked is not None or disliked is not None:
            # 취향 학습 신호가 있으면 그걸로 재정렬 — wishes/reviews로 다시 덮어쓰면
            # 애써 맞춘 취향 순위가 그대로 날아가니, 이 경로에선 pick_top_candidates를
            # 쓰지 않는다(페어링 경로도 마찬가지 이유로 안 씀).
            top_list = score_by_preference(candidates, liked, disliked)[:2]
        else:
            top_list = pick_top_candidates(candidates, limit=2)

    top = top_list[slot % len(top_list)]
    card = _to_card(top)
    if persona_suffix:
        card.persona_line = f"{card.wine_name}, {persona_suffix}"
    return card
