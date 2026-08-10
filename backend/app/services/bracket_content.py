import re

_SENTENCE_END_RE = re.compile(r"[.\n]")


def excerpt_story(article_text: str) -> str:
    """기사 발췌문(또는 없으면 제목)을 그대로 인용구로 쓴다. 지어낸 판단 없이
    원문을 그대로 보여주는 게 가장 확실한 근거이므로 별도 검증 로직이 없다.
    80자 넘으면 잘라서 보여준다."""
    text = (article_text or "").strip()
    if len(text) > 80:
        return text[:80] + "..."
    return text


def excerpt_philosophy(intro_text: str) -> str:
    """브랜드 소개글에서 첫 문장만 뽑아 철학 문구로 쓴다. 마침표/개행 기준으로
    첫 조각을 자르고, 40자 넘으면 추가로 잘라낸다."""
    text = (intro_text or "").strip()
    if not text:
        return ""
    match = _SENTENCE_END_RE.search(text)
    first_sentence = text[: match.start() + 1].strip() if match else text
    if len(first_sentence) > 40:
        return first_sentence[:40] + "..."
    return first_sentence
