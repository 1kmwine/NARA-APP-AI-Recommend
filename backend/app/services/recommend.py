from typing import Callable

from app.services.price_tiers import widen_tier_ranges

SearchFn = Callable[[int, int | None], list[dict]]


def pick_top_candidates(candidates: list[dict], limit: int) -> list[dict]:
    # ponytail: 계획서 Step 3 원안은 score = wishes + reviews였으나 그러면 Step 1
    # 테스트(test_pick_top_candidates_sorts_by_wishes_desc)가 실패한다
    # (B(10) > C(0+5=5) > A(3+1=4) 순이 되어 top2가 ["B","C"]가 됨, 기대값은 ["B","A"]).
    # wishes를 1순위, reviews를 동점자 결정용 2순위로 사용해야 테스트를 통과한다.
    def score(c: dict) -> tuple[int, int]:
        return (c.get("wishes") or 0, c.get("reviews") or 0)

    return sorted(candidates, key=score, reverse=True)[:limit]


def find_with_fallback(tier_index: int, search: SearchFn) -> list[dict]:
    """정확한 가격티어부터 시작해 점점 범위를 넓혀가며 search()를 호출, 첫 비어있지
    않은 결과를 반환한다. 전부 비어있으면 빈 리스트."""
    for price_min, price_max in widen_tier_ranges(tier_index):
        results = search(price_min, price_max)
        if results:
            return results
    return []


def query_candidates(
    session, wine_type: str, country: str, region: str, price_min: int, price_max: int | None
) -> list[dict]:
    """실제 DB 조회 — integrated_item_info + wine_price_cache + wine_notes(override).
    이 함수는 SQL 어댑터라 단위테스트 대상 아님(순수 로직은 find_with_fallback/
    pick_top_candidates로 이미 커버됨). 통합 검증은 Task 14에서 진행."""
    from sqlalchemy import text

    price_clause = "AND p.price_krw <= :price_max" if price_max is not None else ""
    rows = session.execute(
        text(
            f"""
            SELECT i.itemCd, i.nameKo, i.type, i.producer, i.variety, i.country,
                   i.place, i.taste AS taste_raw, i.desc1, i.pdataId,
                   i.reviews, i.wishes,
                   p.price_krw,
                   n.taste AS notes_taste_raw, n.tastingNote, n.foodPairing
            FROM wine_info.integrated_item_info i
            JOIN ai_recommend.wine_price_cache p ON p.item_cd = i.itemCd
            LEFT JOIN wine_info.wine_notes n ON n.brandName = i.brandName
            WHERE i.type = :wine_type
              AND p.price_krw >= :price_min
              {price_clause}
            """
        ),
        {
            "wine_type": wine_type,
            "price_min": price_min,
            "price_max": price_max,
        },
    ).mappings().all()

    return [dict(r) for r in rows]
