# 브라켓/페어링 Gemini 제거 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 브라켓 3경기(스토리)/4경기(철학)와 페어링(음식-와인 매칭)에서 Gemini API 호출을 전부 제거하고 순수 함수(원문 발췌·고정 테이블·키워드 휴리스틱)로 대체한다.

**Architecture:** 기존 `verify_fn`/`summarize_fn` 의존성 주입 구조(`bracket.py`의 `pick_story_match`/`pick_philosophy_match`)는 그대로 유지하고, 라우터에서 주입하는 실제 함수만 Gemini 호출 함수에서 순수 텍스트 처리 함수로 교체한다. `pairing.py`의 `infer_taste_target`도 시그니처는 그대로 두고 내부 구현만 교체한다. 호출부(라우터) 변경은 import/주입 두 줄뿐이다.

**Tech Stack:** Python 3.14, FastAPI, pytest — 새 의존성 없음(오히려 `httpx` 사용이 이 두 파일에서는 사라짐).

**Spec:** `docs/superpowers/specs/2026-08-08-bracket-remove-gemini-design.md`

---

### Task 1: `bracket_content.py`를 순수 함수로 교체

**Files:**
- Modify: `backend/app/services/bracket_content.py`
- Modify: `backend/tests/test_bracket_content.py`

- [ ] **Step 1: 실패하는 테스트부터 작성**

`backend/tests/test_bracket_content.py`를 통째로 아래 내용으로 교체한다(기존 Gemini 모킹 테스트 전부 삭제):

```python
from app.services.bracket_content import excerpt_philosophy, excerpt_story


def test_excerpt_story_returns_short_text_unchanged():
    assert excerpt_story("짧은 발췌문") == "짧은 발췌문"


def test_excerpt_story_truncates_long_text_to_80_chars():
    text = "가" * 100
    result = excerpt_story(text)
    assert result == "가" * 80 + "..."


def test_excerpt_story_handles_none_and_empty():
    assert excerpt_story(None) == ""
    assert excerpt_story("") == ""


def test_excerpt_philosophy_extracts_first_sentence():
    intro = "포도 본연의 생명력을 지킨다. 두번째 문장은 무시된다."
    result = excerpt_philosophy(intro)
    assert result == "포도 본연의 생명력을 지킨다."


def test_excerpt_philosophy_truncates_long_first_sentence_to_40_chars():
    intro = "가" * 60 + "."
    result = excerpt_philosophy(intro)
    assert result == "가" * 40 + "..."


def test_excerpt_philosophy_falls_back_to_truncated_text_when_no_punctuation():
    intro = "가" * 60
    result = excerpt_philosophy(intro)
    assert result == "가" * 40 + "..."


def test_excerpt_philosophy_splits_on_newline_when_no_period():
    intro = "첫줄 문구\n둘째줄은 무시"
    result = excerpt_philosophy(intro)
    assert result == "첫줄 문구"


def test_excerpt_philosophy_handles_none_and_empty():
    assert excerpt_philosophy(None) == ""
    assert excerpt_philosophy("") == ""
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_bracket_content.py -v`
Expected: FAIL — `ImportError: cannot import name 'excerpt_philosophy'` (아직 정의 안 됨)

- [ ] **Step 3: `bracket_content.py`를 순수 함수로 교체**

`backend/app/services/bracket_content.py`를 통째로 아래 내용으로 교체한다(기존 `httpx`/`json`/`logging`/`app.config` 의존 Gemini 호출 코드 전부 삭제):

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_bracket_content.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/bracket_content.py backend/tests/test_bracket_content.py
git commit -m "refactor: bracket_content의 Gemini 호출을 원문 발췌 순수함수로 교체"
```

---

### Task 2: 라우터가 새 함수를 주입하도록 교체

**Files:**
- Modify: `backend/app/routers/bracket.py:9,74-75`

- [ ] **Step 1: import 교체**

`backend/app/routers/bracket.py`에서:

```python
from app.services.bracket_content import summarize_philosophy, verify_story_mention
```

를 아래로 바꾼다:

```python
from app.services.bracket_content import excerpt_philosophy, excerpt_story
```

- [ ] **Step 2: `build_bracket` 호출부의 주입 함수 교체**

같은 파일에서:

```python
    return build_bracket(
        pool=top_pool,
        aroma_by_pdata_id=aroma_by_pdata_id,
        articles_by_brand=articles_by_brand,
        intro_by_brand=intro_by_brand,
        verify_fn=verify_story_mention,
        summarize_fn=summarize_philosophy,
    )
```

를 아래로 바꾼다:

```python
    return build_bracket(
        pool=top_pool,
        aroma_by_pdata_id=aroma_by_pdata_id,
        articles_by_brand=articles_by_brand,
        intro_by_brand=intro_by_brand,
        verify_fn=excerpt_story,
        summarize_fn=excerpt_philosophy,
    )
```

- [ ] **Step 3: 기존 라우터 테스트가 여전히 통과하는지 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_bracket_router.py -v`
Expected: 3 passed (이 테스트들은 `query_candidates`/`fetch_brand_articles`/`fetch_brand_intro`를 모킹하고 `excerpt_story`/`excerpt_philosophy`는 실제로 호출하지만, 둘 다 예외를 던지지 않는 순수 함수라 그대로 통과한다)

- [ ] **Step 4: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/routers/bracket.py
git commit -m "feat: /api/bracket이 excerpt_story/excerpt_philosophy를 사용하도록 교체"
```

---

### Task 3: `bracket.py`에 빈 문자열 가드 추가

**Files:**
- Modify: `backend/app/services/bracket.py`

`excerpt_story`/`excerpt_philosophy`는 입력이 빈 문자열이면 빈 문자열(`""`)을 반환한다(더 이상 `None`을 반환할 일이 없다). 기존 `pick_story_match`/`pick_philosophy_match`의 가드는 `None`만 걸렀으므로, 빈 문자열이 "유효한 내용"으로 잘못 채택되지 않도록 falsy 체크로 넓힌다.

- [ ] **Step 1: `pick_story_match`의 가드 수정**

`backend/app/services/bracket.py`에서:

```python
        quote = verify_fn(articles[0]["excerpt"] or articles[0]["title"])
        if quote is None:
            unverified_candidates.append(candidate)
            continue
```

를 아래로 바꾼다:

```python
        quote = verify_fn(articles[0]["excerpt"] or articles[0]["title"])
        if not quote:
            unverified_candidates.append(candidate)
            continue
```

- [ ] **Step 2: `pick_philosophy_match`의 가드 수정**

같은 파일에서:

```python
        summary = summarize_fn(intro)
        if summary is None:
            continue
```

를 아래로 바꾼다:

```python
        summary = summarize_fn(intro)
        if not summary:
            continue
```

- [ ] **Step 3: 기존 `bracket.py` 테스트가 전부 통과하는지 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_bracket.py -v`
Expected: 전부 통과 (`is None` → `not x`로 넓힌 것뿐이라 기존에 `None`을 반환하던 테스트 케이스들은 그대로 falsy라 동일하게 동작한다)

- [ ] **Step 4: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/bracket.py
git commit -m "fix: pick_story_match/pick_philosophy_match가 빈 문자열도 없음으로 취급하게 함"
```

---

### Task 4: `pairing.py`를 고정 테이블 + 키워드 매칭으로 교체

**Files:**
- Modify: `backend/app/services/pairing.py`
- Modify: `backend/tests/test_pairing.py`

- [ ] **Step 1: 실패하는 테스트부터 작성**

`backend/tests/test_pairing.py`를 통째로 아래 내용으로 교체한다(Gemini 모킹 테스트 4개 삭제, `taste_distance`/`score_by_pairing`/`score_by_preference` 테스트는 그대로 유지, 새 테스트 5개 추가):

```python
from app.services.pairing import (
    FOOD_TASTE_TABLE,
    NEUTRAL_TASTE,
    TasteVector,
    infer_taste_target,
    score_by_pairing,
    score_by_preference,
    taste_distance,
)


def test_taste_distance_zero_when_identical():
    v = TasteVector(sweetness=2, acidity=3, body=4, tannin=1)
    assert taste_distance(v, v) == 0.0


def test_taste_distance_positive_when_different():
    a = TasteVector(sweetness=0, acidity=0, body=0, tannin=0)
    b = TasteVector(sweetness=5, acidity=0, body=0, tannin=0)
    assert taste_distance(a, b) == 5.0


def test_score_by_pairing_ranks_closer_taste_first():
    target = TasteVector(sweetness=1, acidity=4, body=2, tannin=1)
    candidates = [
        {"itemCd": "far", "taste": {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5}},
        {"itemCd": "close", "taste": {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 2}},
    ]
    ranked = score_by_pairing(candidates, target)
    assert [c["itemCd"] for c in ranked] == ["close", "far"]


def test_score_by_pairing_treats_missing_taste_as_neutral():
    target = TasteVector(sweetness=0, acidity=0, body=0, tannin=0)
    candidates = [{"itemCd": "no-taste", "taste": None}]
    ranked = score_by_pairing(candidates, target)
    assert ranked[0]["itemCd"] == "no-taste"


def test_infer_taste_target_returns_table_value_for_known_food():
    result = infer_taste_target("초밥")
    assert result == FOOD_TASTE_TABLE["초밥"]


def test_infer_taste_target_matches_spicy_keyword():
    result = infer_taste_target("엄청 매운 마라탕")
    assert result.tannin == 1
    assert result.sweetness == 3


def test_infer_taste_target_matches_fried_keyword():
    result = infer_taste_target("바삭한 새우튀김")
    assert result.acidity == 4
    assert result.body == 4


def test_infer_taste_target_matches_raw_fish_keyword():
    result = infer_taste_target("연어 회 한 접시")
    assert result.acidity == 4
    assert result.body == 1


def test_infer_taste_target_falls_back_to_neutral_for_unknown_text():
    result = infer_taste_target("아무 의미 없는 텍스트")
    assert result == NEUTRAL_TASTE


def test_score_by_preference_returns_unchanged_when_no_signal():
    candidates = [{"itemCd": "a", "taste": None}, {"itemCd": "b", "taste": None}]
    assert score_by_preference(candidates, liked=None, disliked=None) == candidates


def test_score_by_preference_ranks_close_to_liked_first():
    liked = TasteVector(sweetness=1, acidity=4, body=2, tannin=1)
    candidates = [
        {"itemCd": "far", "taste": {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5}},
        {"itemCd": "close", "taste": {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 2}},
    ]
    ranked = score_by_preference(candidates, liked=liked, disliked=None)
    assert [c["itemCd"] for c in ranked] == ["close", "far"]


def test_score_by_preference_ranks_far_from_disliked_first():
    disliked = TasteVector(sweetness=1, acidity=4, body=2, tannin=1)
    candidates = [
        {"itemCd": "similar-to-disliked", "taste": {"sweetness": 1, "acidity": 4, "body": 2, "tannin": 2}},
        {"itemCd": "different-from-disliked", "taste": {"sweetness": 5, "acidity": 0, "body": 5, "tannin": 5}},
    ]
    ranked = score_by_preference(candidates, liked=None, disliked=disliked)
    assert [c["itemCd"] for c in ranked] == ["different-from-disliked", "similar-to-disliked"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_pairing.py -v`
Expected: FAIL — `ImportError: cannot import name 'FOOD_TASTE_TABLE'`

- [ ] **Step 3: `pairing.py`를 고정 테이블 + 키워드 매칭으로 교체**

`backend/app/services/pairing.py`를 통째로 아래 내용으로 교체한다(기존 `httpx`/`json`/Gemini 호출 코드 전부 삭제):

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_pairing.py -v`
Expected: 11 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/pairing.py backend/tests/test_pairing.py
git commit -m "refactor: pairing의 Gemini 호출을 고정테이블+키워드 매칭으로 교체"
```

---

### Task 5: 미사용 `gemini_api_key` 설정 제거

**Files:**
- Modify: `backend/app/config.py`

Task 1·4에서 `bracket_content.py`/`pairing.py`의 Gemini 호출 코드를 지웠으므로,
`settings.gemini_api_key`를 참조하는 곳이 더 이상 없다.

- [ ] **Step 1: 다른 참조가 없는지 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && grep -rn "gemini_api_key" app/`
Expected: `app/config.py`의 정의 줄 하나만 남아있어야 함(다른 파일에서 참조 없음)

- [ ] **Step 2: 설정 필드 제거**

`backend/app/config.py`에서:

```python
    nas1_base_url: str = "http://el.naracellar.com/share.cgi"
    nas1_share_ssid: str

    gemini_api_key: str = ""
```

를 아래로 바꾼다:

```python
    nas1_base_url: str = "http://el.naracellar.com/share.cgi"
    nas1_share_ssid: str
```

- [ ] **Step 3: 백엔드가 여전히 기동하는지 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -c "from app.config import settings; print('ok')"`
Expected: `ok` (pydantic-settings가 `.env`의 미사용 `GEMINI_API_KEY` 줄은 기본적으로 무시하므로 에러 없음)

- [ ] **Step 4: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/config.py
git commit -m "chore: 미사용 gemini_api_key 설정 제거"
```

---

### Task 6: 전체 테스트 재확인 + 배포

**Files:** 없음(검증·배포 작업)

- [ ] **Step 1: 백엔드 전체 테스트 스위트 실행**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest -q`
Expected: 전부 통과 (Task 1 이전 기준 120개에서, Gemini 모킹 테스트 9개(bracket_content 5개+pairing 4개) 삭제하고 순수함수 테스트 13개(bracket_content 8개+pairing 5개)가 새로 들어가서 총 124개 정도 — 정확한 숫자보다 "0 failed"가 중요)

- [ ] **Step 2: httpx/Gemini 관련 코드가 실제로 다 빠졌는지 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && grep -rn "generativelanguage\|_call_gemini\b" app/`
Expected: 아무 결과 없음(전부 제거됨)

- [ ] **Step 3: 서버로 소스 동기화**

```bash
rsync -az --delete \
  --exclude 'node_modules' --exclude '.next' --exclude '.git' \
  --exclude '__pycache__' --exclude '.venv' --exclude 'tsconfig.tsbuildinfo' \
  --exclude '.DS_Store' \
  -e "ssh -o StrictHostKeyChecking=no" \
  /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/ root@192.168.47.105:/var/www/NARA-APP-AI-Recommend/
```

- [ ] **Step 4: 백엔드 컨테이너 재빌드**

```bash
ssh root@192.168.47.105 "cd /var/www/NARA-APP-AI-Recommend && docker compose up -d --build backend"
```

- [ ] **Step 5: 헬스체크 + 브라켓 엔드포인트 확인 (응답속도 개선 체감)**

```bash
curl -sS "http://192.168.47.105:3005/" -o /dev/null -w "frontend:%{http_code}\n"
curl -sS -G "http://192.168.47.105:3005/api/bracket" \
  --data-urlencode "price_tier=5" --data-urlencode "country_index=0" \
  --data-urlencode "region_index=0" --data-urlencode "wine_type=Red" \
  -o /tmp/bracket_no_gemini.json -w "bracket_status:%{http_code} time:%{time_total}s\n"
```

Expected: `frontend:200`, `bracket_status:200`이고 `time_total`이 기존 1~4분이 아니라
수 초 이내로 나와야 한다(Gemini 순차 호출이 사라졌으므로).

- [ ] **Step 6: 응답 내용에 story/philosophy 매치가 실제로 채워졌는지 확인**

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend && python3 -c "import json; d=json.load(open('/tmp/bracket_no_gemini.json')); [print(m['axis'], [c['axis_label'] for c in m['cards']]) for m in d['matches']]"`
Expected: `story`/`philosophy` axis가 (풀에 해당 브랜드 기사/소개글이 있다면) 매치 목록에
나타나야 하고, 더 이상 "Gemini 실패로 항상 폴백"이 아니라 실제 발췌 내용이 채워진다.
