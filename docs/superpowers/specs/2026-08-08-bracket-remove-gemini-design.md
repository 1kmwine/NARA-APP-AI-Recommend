# 브라켓/페어링에서 Gemini 제거 — 설계 문서

## 배경

이상형 월드컵 브라켓 기능(3경기 스토리, 4경기 철학)과 페어링(음식-와인 매칭)이
Gemini API(`gemini-2.0-flash`)에 의존한다. 현재 API 키 quota가 0(429)이라 매
호출이 실패 → fail-safe 폴백만 계속 나가는 상태고, 성공하더라도 브랜드별 순차
호출 때문에 응답이 1~4분씩 걸렸다. 세 지점 모두 Gemini를 제거하고 결정적(순수
함수) 로직으로 대체한다.

Gemini를 쓰는 3곳:
1. `bracket_content.py::verify_story_mention` — 기사 발췌문에 실존 인물/행사
   언급이 있는지 판별 (3경기 스토리)
2. `bracket_content.py::summarize_philosophy` — 브랜드 소개글을 짧은 철학 문구로
   요약 (4경기 철학)
3. `pairing.py::infer_taste_target` — 음식 이름 → 이상적 와인 맛벡터 추론 (페어링)

## 1. 스토리(3경기) — 검증 제거, 발췌문 원문 그대로

**현재**: Gemini가 기사 발췌문을 읽고 "검증 가능한 실존 인물/행사 언급"이 있는지
판별, 있으면 quote를 생성. `pick_story_match`는 검증된 후보를 우선 채우고, 부족하면
브랜드만 다른 미검증 후보(quote/url=None)로 채운다.

**변경**: "언급이 있는지 판단" 자체를 없앤다. `wine_articles`에서 브랜드 기사가
있으면 그 발췌문(`excerpt`, 없으면 `title`)을 그대로 인용구로 쓴다. 지어내는 게
없으므로 검증이라는 개념 자체가 불필요해진다 — 원문을 그대로 보여주는 것보다
더 확실한 "검증"은 없다.

- `bracket_content.py`에 `excerpt_story(article_text: str) -> str` 추가: 발췌문이
  80자를 넘으면 앞 80자 + "..."로 자른다. 빈 문자열/None이면 그대로 반환(호출부가
  이미 "기사 없음"을 걸러내므로 여기선 방어적으로만 처리).
- `verify_story_mention`(Gemini 호출) 삭제.
- `pick_story_match`(`bracket.py`)의 시그니처(`StoryVerifyFn = Callable[[str], str | None]`)는
  유지 — 이제 이 함수는 "검증"이 아니라 "발췌 추출"을 하고, 입력이 있으면 항상
  문자열을 반환한다(더 이상 None을 반환할 이유가 없으므로 실질적으로 verified/
  unverified 2단계 분기가 무의미해지지만, 코드 변경 최소화를 위해 함수 구조는
  그대로 둔다 — `unverified_candidates`로 빠지는 경로는 이제 "기사 자체가 없는
  브랜드"만 타게 된다).
- 라우터에서 주입하는 함수만 `verify_story_mention` → `excerpt_story`로 교체.

## 2. 철학(4경기) — 요약 대신 첫 문장 추출

**현재**: Gemini가 브랜드 소개글(`brand_intro.introText`)을 40자 이내 철학
문구로 요약.

**변경**: 소개글에서 첫 문장만 추출한다. 문장 구분자(`.`, `다.`, `요.`, 개행)
기준으로 첫 조각을 뽑고, 40자를 넘으면 40자 + "..."로 자른다. 문장 구분이
안 되면(구두점 없음) 그냥 앞 40자 + "..."로 자른다.

- `bracket_content.py`에 `excerpt_philosophy(intro_text: str) -> str` 추가.
- `summarize_philosophy`(Gemini 호출) 삭제.
- `pick_philosophy_match` 시그니처(`PhilosophySummarizeFn`)는 그대로 유지, 라우터
  주입 함수만 교체. 이 함수는 입력(소개글)이 있으면 항상 문자열을 반환하므로
  `pick_philosophy_match`가 `summarize_fn`이 None을 반환하는 경우를 처리하던
  분기는 이제 사실상 도달하지 않지만, 방어적으로 그대로 둔다(빈 소개글이면
  빈 문자열 반환 → 호출부의 "빈 문자열도 유효한 후보로 안 침" 판단은 별도
  가드 필요 — 아래 "빈 결과 처리" 참고).

## 3. 페어링 — 고정 테이블 + 키워드 휴리스틱

**현재**: Gemini가 자유 텍스트 음식 이름을 보고 맛벡터(sweetness/acidity/body/
tannin, 0~5)를 추론.

**변경**:
- 프론트 `REAL_FOODS` 9종(삼겹살/치킨/스테이크/파스타/초밥/치즈 플래터/매운탕/
  피자/디저트)은 `pairing.py`에 고정 딕셔너리로 맛벡터를 미리 정의한다(기존
  Gemini 프롬프트에 문서화된 원칙 — 지방↔산도/타닌, 매운맛↔낮은타닌+약간단맛,
  산미↔산도 — 을 사람이 손으로 적용한 값).
- "직접 입력하기"(자유 텍스트)는 키워드 부분매치 휴리스틱으로 처리:
  - "맵"/"매운" 포함 → 타닌 낮음, 단맛 약간
  - "튀김"/"구이"/"크림"/"기름" 포함 → 산도·타닌 높음
  - "회"/"새콤"/"신맛" 포함 → 산도 높음, 바디 낮음
  - 여러 키워드가 겹치면 먼저 매치되는 것 하나만 적용(우선순위: 매운 > 튀김/구이
    > 회, 이유: 매운맛 상쇄가 가장 뚜렷한 페어링 원칙)
  - 아무 것도 안 걸리면 기존과 동일하게 `NEUTRAL_TASTE(2,2,2,2)` 폴백
- `infer_taste_target(food_text: str) -> TasteVector` 함수 시그니처와 반환 타입은
  그대로 유지 — 내부 구현만 Gemini 호출에서 테이블 조회+키워드 매칭으로 교체.
  호출부(라우터) 변경 불필요.
- `_call_gemini`, `PAIRING_SYSTEM_PROMPT`, `httpx` import 삭제.

## 빈 결과 처리

`excerpt_story`/`excerpt_philosophy`가 빈 문자열을 반환하는 경우(기사/소개글
텍스트 자체가 빈 문자열인 DB 데이터 이상 케이스)는 "내용 없음"으로 취급해야
하므로, `pick_story_match`/`pick_philosophy_match` 호출부에서 반환값이 빈
문자열이면 None과 동일하게 처리하도록 가드를 추가한다(`if not quote:` /
`if not summary:` — 기존 `if quote is None:`에서 `if not quote:`로 변경).

## 영향 범위

**삭제**:
- `bracket_content.py`: `_call_gemini_text`, `PHILOSOPHY_SYSTEM_PROMPT`,
  `STORY_SYSTEM_PROMPT`, `summarize_philosophy`, `verify_story_mention`, `httpx`/
  `json`/`app.config.settings` import(다른 용도로 안 쓰면)
- `pairing.py`: `_call_gemini`, `PAIRING_SYSTEM_PROMPT`, `GEMINI_MODEL`,
  `GEMINI_URL`, `httpx` import, `_strip_code_fence`(다른 곳에서 안 쓰면)
- `app/config.py`의 `gemini_api_key` 설정 — 다른 곳에서 참조 안 하면 제거,
  참조하는 곳 있으면 유지(확인 필요)

**추가**:
- `bracket_content.py`: `excerpt_story`, `excerpt_philosophy`
- `pairing.py`: `FOOD_TASTE_TABLE`(딕셔너리), `_infer_from_keywords`(또는 동등한
  헬퍼), `infer_taste_target` 재구현

**수정**:
- `bracket.py`: `pick_story_match`/`pick_philosophy_match`의 `if x is None`
  가드를 `if not x`로 변경 (빈 문자열도 "없음" 취급)
- `routers/bracket.py`: 주입 함수를 `verify_story_mention`→`excerpt_story`,
  `summarize_philosophy`→`excerpt_philosophy`로 교체
- `test_bracket_content.py`: Gemini 모킹 테스트 삭제, `excerpt_story`/
  `excerpt_philosophy` 순수함수 테스트로 교체
- `test_pairing.py`: Gemini 모킹 테스트 삭제, 테이블 조회/키워드 매칭 테스트로
  교체

**응답속도**: 브랜드별 순차 Gemini 호출이 사라지므로 `/api/bracket` 응답이
DB 조회 시간만으로 즉시 나온다(기존 1~4분 → 수 초).

**비목표**: 자유 텍스트 페어링의 키워드 매칭 정확도를 Gemini 수준으로 끌어올리는
것은 목표가 아니다 — 고정 9종 음식은 정확하고, 자유입력은 몇 가지 뚜렷한
케이스만 잡고 나머지는 중립값으로 폴백하는 것으로 충분하다(기존 Gemini 실패시
동작과 동일한 수준).
