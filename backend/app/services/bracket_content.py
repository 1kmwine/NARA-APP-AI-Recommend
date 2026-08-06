import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

PHILOSOPHY_SYSTEM_PROMPT = """너는 와인 카피라이터다. 주어진 브랜드 소개글을 읽고,
그 브랜드의 양조 철학이나 정체성을 한 문장(40자 이내)으로 요약해라. 소개글에 없는
내용을 지어내지 말고, 소개글에 실제로 나온 표현을 최대한 활용해라.
따옴표나 다른 텍스트 없이 요약 문장만 출력해라."""

STORY_SYSTEM_PROMPT = """너는 팩트체커다. 주어진 와인 기사 발췌문을 읽고, 그 안에
검증 가능한 실존 인물이나 유명 행사(예: 대통령/왕족 만찬, 올림픽, 국제 대회 수상 등)에
대한 구체적 언급이 있는지 판단해라. 브랜드 홍보 문구나 막연한 칭찬("최고의 와인")은
언급으로 치지 않는다 — 구체적 인물명이나 행사명이 나와야 한다.

아래 JSON 형식으로만 답해라. 다른 텍스트 금지:
{"has_mention": true/false, "quote": "언급이 있으면 한 문장 요약(없으면 null)"}
"""


def _call_gemini_text(system_prompt: str, user_text: str) -> str:
    response = httpx.post(
        GEMINI_URL,
        params={"key": settings.gemini_api_key},
        json={
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_text}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```")
        text = text.strip()
    return text


def summarize_philosophy(intro_text: str) -> str | None:
    """브랜드 소개글을 짧은 철학 문구로 요약한다. 실패하면 None(호출 측이 이 후보를
    4경기에서 제외하거나 소개글 원문 일부를 대신 쓰면 됨)."""
    try:
        raw = _call_gemini_text(PHILOSOPHY_SYSTEM_PROMPT, intro_text)
    except Exception as e:
        logger.warning("철학 문구 생성 실패: error=%s", e)
        return None
    return raw.strip() or None


def verify_story_mention(article_text: str) -> str | None:
    """기사 발췌문에 검증 가능한 인물/행사 언급이 있는지 Gemini로 판별한다. 있으면
    한 문장 인용구, 없거나 호출/파싱 실패하면 None을 반환한다 — 허위 언급을 만들지
    않기 위해 실패는 항상 "없음"으로 취급한다(fail-safe, fail-open 아님)."""
    try:
        raw = _call_gemini_text(STORY_SYSTEM_PROMPT, article_text)
    except Exception as e:
        logger.warning("스토리 언급 판별 실패: error=%s", e)
        return None

    raw = _strip_code_fence(raw)
    try:
        data = json.loads(raw)
        if not data.get("has_mention"):
            return None
        return data.get("quote") or None
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        logger.warning("스토리 언급 판별 응답 파싱 실패: raw=%r error=%s", raw, e)
        return None
