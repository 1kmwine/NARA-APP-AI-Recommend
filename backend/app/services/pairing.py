import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TasteVector:
    sweetness: int
    acidity: int
    body: int
    tannin: int


NEUTRAL_TASTE = TasteVector(sweetness=2, acidity=2, body=2, tannin=2)


def taste_distance(a: TasteVector, b: TasteVector) -> float:
    return math.sqrt(
        (a.sweetness - b.sweetness) ** 2
        + (a.acidity - b.acidity) ** 2
        + (a.body - b.body) ** 2
        + (a.tannin - b.tannin) ** 2
    )


def _taste_from_dict(taste: dict | None) -> TasteVector:
    if not taste:
        return NEUTRAL_TASTE
    return TasteVector(
        sweetness=taste.get("sweetness", 2),
        acidity=taste.get("acidity", 2),
        body=taste.get("body", 2),
        tannin=taste.get("tannin", 2),
    )


def score_by_pairing(candidates: list[dict], target: TasteVector) -> list[dict]:
    return sorted(
        candidates, key=lambda c: taste_distance(_taste_from_dict(c.get("taste")), target)
    )


def score_by_preference(
    candidates: list[dict], liked: TasteVector | None, disliked: TasteVector | None
) -> list[dict]:
    """♡/X로 쌓인 취향 벡터로 후보를 재정렬한다. liked에 가깝고 disliked에서 먼
    후보가 앞으로 온다. 둘 다 없으면(신규 사용자) 원래 순서 그대로 둔다."""
    if liked is None and disliked is None:
        return candidates

    def score(c: dict) -> float:
        v = _taste_from_dict(c.get("taste"))
        s = 0.0
        if liked is not None:
            s += taste_distance(v, liked)
        if disliked is not None:
            s -= taste_distance(v, disliked)
        return s

    return sorted(candidates, key=score)


# 프론트 REAL_FOODS(page.tsx) 9종 고정 맛벡터 — Wine Folly 페어링 원칙(지방↔산도/
# 타닌, 매운맛↔낮은타닌+약간단맛, 산미↔산도)을 사람이 직접 적용한 값.
FOOD_TASTE_TABLE: dict[str, TasteVector] = {
    "삼겹살": TasteVector(sweetness=1, acidity=2, body=4, tannin=4),
    "치킨": TasteVector(sweetness=1, acidity=3, body=3, tannin=2),
    "스테이크": TasteVector(sweetness=0, acidity=2, body=5, tannin=5),
    "파스타": TasteVector(sweetness=1, acidity=3, body=3, tannin=2),
    "초밥": TasteVector(sweetness=1, acidity=4, body=1, tannin=0),
    "치즈": TasteVector(sweetness=2, acidity=2, body=3, tannin=3),
    "매운탕": TasteVector(sweetness=3, acidity=2, body=2, tannin=1),
    "피자": TasteVector(sweetness=1, acidity=3, body=3, tannin=3),
    "디저트": TasteVector(sweetness=5, acidity=1, body=2, tannin=0),
}

# 매운맛 상쇄가 가장 뚜렷한 페어링 원칙이라 우선순위 최상단에 둔다.
_KEYWORD_RULES: list[tuple[tuple[str, ...], TasteVector]] = [
    (("맵", "매운"), TasteVector(sweetness=3, acidity=2, body=2, tannin=1)),
    (("튀김", "구이", "크림", "기름"), TasteVector(sweetness=1, acidity=4, body=4, tannin=4)),
    (("회", "새콤", "신맛"), TasteVector(sweetness=1, acidity=4, body=1, tannin=0)),
]


def _infer_from_keywords(food_text: str) -> TasteVector:
    for keywords, vector in _KEYWORD_RULES:
        if any(k in food_text for k in keywords):
            return vector
    return NEUTRAL_TASTE


def infer_taste_target(food_text: str) -> TasteVector:
    """음식 이름 → 이상적 와인 맛벡터. REAL_FOODS 9종은 고정 테이블에서 바로
    찾고, 그 외 자유 텍스트는 키워드 매칭으로 추론한다(둘 다 안 걸리면 중립값)."""
    if food_text in FOOD_TASTE_TABLE:
        return FOOD_TASTE_TABLE[food_text]
    return _infer_from_keywords(food_text)
