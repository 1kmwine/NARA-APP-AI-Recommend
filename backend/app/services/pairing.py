import json
import logging
import math
from dataclasses import dataclass

from anthropic import Anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# Wine Folly(winefolly.com) 페어링 방법론 요약(우리 말로 재정리, 원문 인용 아님) —
# 음식의 6대 기본맛(짠맛/산미/단맛/쓴맛/지방/매운맛) 중 지배적 요소를 파악해
# congruent(향 공명)/complementary(대비) 매칭 원칙으로 이상적 와인 맛벡터를 추론한다.
PAIRING_SYSTEM_PROMPT = """너는 소믈리에다. 사용자가 입력한 음식 이름을 보고,
그 음식과 어울리는 와인의 이상적인 맛 구조를 0~5 정수로만 추론해라.

원칙:
- 지방이 많은 음식(구이, 튀김, 크림소스)은 산도(acidity)나 타닌(tannin)이 있는 와인이
  기름기를 상쇄한다.
- 매운 음식은 타닌이 낮고 약간의 단맛(sweetness)이 있는 와인이 매운맛을 눌러준다.
- 산미 있는 음식(회, 신 음식)은 산도 높은 와인과 맞춘다.
- 향신료 향과 와인의 아로마가 겹치면(congruent) 좋은 매칭이다.

아래 JSON 형식으로만 답해라. 다른 텍스트 금지:
{"sweetness": 0-5, "acidity": 0-5, "body": 0-5, "tannin": 0-5}
"""


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


def score_by_pairing(candidates: list[dict], target: TasteVector) -> list[dict]:
    def to_vector(taste: dict | None) -> TasteVector:
        if not taste:
            return NEUTRAL_TASTE
        return TasteVector(
            sweetness=taste.get("sweetness", 2),
            acidity=taste.get("acidity", 2),
            body=taste.get("body", 2),
            tannin=taste.get("tannin", 2),
        )

    return sorted(
        candidates, key=lambda c: taste_distance(to_vector(c.get("taste")), target)
    )


def _call_anthropic(food_text: str) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=100,
        system=PAIRING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": food_text}],
    )
    return message.content[0].text


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```")
        text = text.strip()
    return text


def infer_taste_target(food_text: str) -> TasteVector:
    try:
        raw = _call_anthropic(food_text)
    except Exception as e:
        logger.warning("페어링 LLM 호출 실패: food_text=%s error=%s", food_text, e)
        return NEUTRAL_TASTE

    raw = _strip_code_fence(raw)
    try:
        data = json.loads(raw)
        return TasteVector(
            sweetness=int(data["sweetness"]),
            acidity=int(data["acidity"]),
            body=int(data["body"]),
            tannin=int(data["tannin"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("페어링 LLM 응답 파싱 실패: food_text=%s raw=%r error=%s", food_text, raw, e)
        return NEUTRAL_TASTE
