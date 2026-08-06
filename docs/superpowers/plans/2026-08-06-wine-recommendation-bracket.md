# 이상형 월드컵 브라켓 추천 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 다이얼+카드2장 결과화면을, 4경기(산도/아로마/스토리/철학) 8강 → 준결승 → 결승
토너먼트 브라켓으로 대체한다. 최종 승자 와인 1병이 최종 추천이다.

**Architecture:** 새 백엔드 엔드포인트 `GET /api/bracket`가 후보 풀을 조회하고 4경기 매치업을
한 번에 구성해 응답한다(1·2경기는 로컬 데이터, 3·4경기는 Gemini 호출). 프론트는 이 응답 하나로
8강→준결승→결승을 전부 로컬 상태만으로 진행한다(추가 API 호출 없음).

**Tech Stack:** FastAPI/SQLAlchemy(backend), Next.js/React(frontend), Gemini 2.0 Flash REST API.

**설계 문서:** [`docs/superpowers/specs/2026-08-06-wine-recommendation-bracket-design.md`](../specs/2026-08-06-wine-recommendation-bracket-design.md)

---

## 사전 준비: 이 코드베이스에 대해 알아야 할 것

- 백엔드 진입점: `backend/app/main.py` (FastAPI, 라우터 등록)
- DB 접근 2계통:
  - `app.db.get_session()` → `ai_recommend_app` 계정, `ai_recommend`(전체권한) +
    `wine_info.integrated_item_info`/`wine_notes`(SELECT)만 접근 가능. `wine_info.*` 테이블은
    세션에서 스키마 명시(`wine_info.table_name`)로 크로스스키마 쿼리한다.
  - `app.db.pos_engine` → `ai_recommend_pos_ro` 계정, `pos.tb_product`/`pos.v_daily_sale`(SELECT)만
    접근 가능. Session이 아니라 raw `engine.connect()`로 씀(`etl/sync_price.py` 참고 패턴).
- 기존 추천 로직(`backend/app/services/recommend.py`)의 `query_candidates()`가 후보 풀 조회의
  핵심 — `wine_info.integrated_item_info` + `ai_recommend.wine_price_cache` JOIN, Python에서
  country/region 후필터링 + itemCd dedupe.
- `backend/app/services/region_cache.py`의 `region_cache.get(session, wine_type)`이 타입별
  지역 순서(SKU 많은 순)를 캐싱해서 준다 — 지역 자동 확장에 재사용한다.
- `backend/app/services/pairing.py`의 `_call_gemini()` 패턴(Gemini REST 직접 호출,
  `httpx.post` + `responseMimeType: application/json`)을 새 Gemini 호출에도 그대로 재사용한다.
- 프론트 기존 화면: `frontend/app/page.tsx`(다이얼+카드2장, 인트로 3단계), 스타일은
  `frontend/app/wine-recommend.module.css`(CSS Module, `design-system.css` 토큰 사용).
- 테스트: `backend/tests/conftest.py`가 `region_cache`를 자동으로 시딩해서(France/부르고뉴)
  실DB 안 타게 해준다 — 새 wine_type을 테스트에서 쓰면 이 fixture에도 추가해야 함.
- 배포: 로컬에서 코드 수정 → `rsync`로 `192.168.47.105:/var/www/NARA-APP-AI-Recommend/`에
  동기화 → SSH로 `docker compose up -d --build`. 이 세션 안에서 실제로 여러 번 한 절차라
  마지막 검증 태스크에 그대로 명시해뒀다.

---

## Task 0: DB 권한 추가 (인프라, 코드 아님)

이 태스크는 서버에 SSH로 접속해 SQL을 직접 실행하는 인프라 작업이다 — 코드 파일을 안 건드린다.
새로 필요한 테이블 3개(`wine_info.wine_article_brands`, `wine_info.wine_articles`,
`wine_info.brand_intro`)와 `pos.tb_pdata`(아로마)에 대한 SELECT 권한이 현재 없다(2026-08-06
확인, `SHOW GRANTS` 결과 첨부):

```
-- 확인된 현재 권한 (2026-08-06)
-- ai_recommend_app@%: ai_recommend.*(전체), wine_info.wine_notes, wine_info.integrated_item_info
-- ai_recommend_pos_ro@%: pos.tb_product, pos.v_daily_sale
```

- [ ] **Step 1: 서버에 SSH로 접속해 root로 GRANT 실행**

```bash
ssh root@192.168.47.105
mysql -u root -p'{{DB_ROOT_PW — docs/CREDENTIALS.local.md 참고}}'
```

MySQL 프롬프트에서:

```sql
GRANT SELECT ON wine_info.wine_article_brands TO 'ai_recommend_app'@'%';
GRANT SELECT ON wine_info.wine_articles TO 'ai_recommend_app'@'%';
GRANT SELECT ON wine_info.brand_intro TO 'ai_recommend_app'@'%';
GRANT SELECT ON pos.tb_pdata TO 'ai_recommend_pos_ro'@'%';
FLUSH PRIVILEGES;
```

- [ ] **Step 2: 권한 반영 확인**

```sql
SHOW GRANTS FOR 'ai_recommend_app'@'%';
SHOW GRANTS FOR 'ai_recommend_pos_ro'@'%';
```

Expected: `ai_recommend_app`에 `wine_article_brands`/`wine_articles`/`brand_intro` SELECT 3줄,
`ai_recommend_pos_ro`에 `tb_pdata` SELECT 1줄이 추가로 보임.

- [ ] **Step 3: 로컬에서 실제 접속 검증**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -c "
from app.db import engine, pos_engine
from sqlalchemy import text
with engine.connect() as c:
    print('wine_articles:', c.execute(text('SELECT COUNT(*) FROM wine_info.wine_articles')).scalar())
    print('brand_intro:', c.execute(text('SELECT COUNT(*) FROM wine_info.brand_intro')).scalar())
with pos_engine.connect() as c:
    print('tb_pdata:', c.execute(text('SELECT COUNT(*) FROM tb_pdata')).scalar())
"
```

Expected: 세 줄 다 에러 없이 숫자 출력(`wine_articles: 2598`, `brand_intro: 1131`,
`tb_pdata: 32613` 근처 — 정확한 값은 그때그때 데이터에 따라 다를 수 있음, 0이 아니고
"Access denied"가 안 뜨면 됨).

---

## Task 1: `query_candidates`에 brandName 포함

**Files:**
- Modify: `backend/app/services/recommend.py:60-67` (SELECT 절)

3·4경기(스토리/철학)가 후보의 브랜드명으로 `wine_article_brands`/`brand_intro`를 조회해야
하는데, 지금 `query_candidates()`의 SELECT 절에 `brandName`이 없다.

- [ ] **Step 1: SELECT 절에 `i.brandName` 추가**

`backend/app/services/recommend.py`에서 이 블록을:

```python
        text(
            f"""
            SELECT i.itemCd, i.nameKo, i.type, i.producer, i.variety, i.country,
                   i.place, i.countryName, i.taste AS taste_raw, i.desc1, i.pdataId,
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
```

이렇게 바꾼다(`i.brandName` 추가):

```python
        text(
            f"""
            SELECT i.itemCd, i.nameKo, i.type, i.producer, i.variety, i.country,
                   i.place, i.countryName, i.taste AS taste_raw, i.desc1, i.pdataId,
                   i.reviews, i.wishes, i.brandName,
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
```

- [ ] **Step 2: 기존 테스트가 안 깨지는지 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_recommend.py tests/test_recommend_router.py -q
```

Expected: 전부 PASS (이 SELECT는 `query_candidates` 유닛테스트 대상이 아니라고 그 함수
docstring에 명시돼있음 — 순수 로직 테스트들은 이 변경과 무관).

- [ ] **Step 3: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/recommend.py
git commit -m "feat: query_candidates에 brandName 포함 (브라켓 스토리/철학 경기용)"
```

---

## Task 2: 아로마 분류 (순수 함수, TDD)

**Files:**
- Create: `backend/app/services/aroma.py`
- Test: `backend/tests/test_aroma.py`

`pos.tb_pdata.aroma`는 영어 아로마 태그 배열(예: `["Blackcurrant","Cloves","Vanilla"]`)이다.
이걸 "과일향 위주"/"꽃·2,3차향 위주" 둘 중 하나로 분류하는 순수 함수를 고정 키워드 매핑으로
만든다. Gemini 불필요.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_aroma.py` 새 파일:

```python
from app.services.aroma import classify_aroma_tags


def test_classify_aroma_tags_fruit_dominant():
    tags = ["Blackcurrant", "Raspberry", "Cherry", "Vanilla"]
    assert classify_aroma_tags(tags) == "fruit"


def test_classify_aroma_tags_floral_tertiary_dominant():
    tags = ["Violet", "Leather", "Tobacco", "Mushroom"]
    assert classify_aroma_tags(tags) == "floral_tertiary"


def test_classify_aroma_tags_tie_breaks_to_fruit():
    # 과일 2개, 비과일 2개로 동점이면 "fruit"로 정한다(임의지만 결정적이어야 함)
    tags = ["Cherry", "Plum", "Leather", "Smoke"]
    assert classify_aroma_tags(tags) == "fruit"


def test_classify_aroma_tags_empty_list_defaults_to_fruit():
    assert classify_aroma_tags([]) == "fruit"


def test_classify_aroma_tags_unknown_tags_ignored():
    # 매핑에 없는 태그는 무시하고, 알려진 태그만으로 판단
    tags = ["SomeUnknownTag123", "Rose", "Violet"]
    assert classify_aroma_tags(tags) == "floral_tertiary"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_aroma.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.aroma'`

- [ ] **Step 3: 구현**

`backend/app/services/aroma.py` 새 파일:

```python
from typing import Literal

# tb_pdata.aroma에 실제로 나오는 영어 태그(2026-08-06 샘플 확인) 기준 분류.
# 과일류(1차 향)는 fruit, 꽃/오크/숙성/향신료 등 2·3차 향은 floral_tertiary.
FRUIT_TAGS = {
    "blackcurrant", "blackberry", "raspberry", "strawberry", "cherry", "plum",
    "prune", "fig", "pineapple", "banana", "grapefruit", "orange peel", "peach",
    "apple", "lemon", "lime", "apricot", "melon", "grape", "citrus", "tropical fruit",
    "red fruit", "black fruit", "stone fruit",
}
FLORAL_TERTIARY_TAGS = {
    "violet", "rose", "jasmine", "vanilla", "leather", "tobacco", "mushroom",
    "cloves", "nutmeg", "cedar", "smoke", "toast", "chocolate", "coffee", "earth",
    "mineral", "herb", "pepper", "licorice", "liquorice", "honey", "butter",
    "oak", "truffle", "game", "forest floor", "wet stone",
}

Aroma = Literal["fruit", "floral_tertiary"]


def classify_aroma_tags(tags: list[str]) -> Aroma:
    """아로마 태그 목록을 과일향/꽃·2,3차향 둘 중 하나로 분류한다.
    알려진 태그 수를 세어 많은 쪽으로 정하고, 동점이거나 알려진 태그가 없으면
    "fruit"으로 기본값을 준다(결정적 동작이 필요해서 임의 우선순위를 둠)."""
    fruit_count = 0
    floral_count = 0
    for tag in tags:
        normalized = tag.strip().lower()
        if normalized in FRUIT_TAGS:
            fruit_count += 1
        elif normalized in FLORAL_TERTIARY_TAGS:
            floral_count += 1
    if floral_count > fruit_count:
        return "floral_tertiary"
    return "fruit"
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_aroma.py -v
```

Expected: 5개 PASS

- [ ] **Step 5: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/aroma.py backend/tests/test_aroma.py
git commit -m "feat: 아로마 태그를 과일향/꽃·2,3차향으로 분류하는 순수 함수 추가"
```

---

## Task 3: 후보 풀에서 아로마 태그 DB 조회

**Files:**
- Modify: `backend/app/services/aroma.py` (조회 함수 추가)
- Test: `backend/tests/test_aroma.py` (조회 함수 테스트 추가)

`pdata_id` 목록으로 `pos.tb_pdata.aroma`를 한 번에 조회하는 함수. `pos_engine`(raw connection)
사용 — `etl/sync_price.py`와 같은 패턴.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_aroma.py`에 추가:

```python
import json
from unittest.mock import MagicMock

from app.services.aroma import fetch_aroma_tags


def test_fetch_aroma_tags_returns_dict_keyed_by_pdata_id():
    fake_conn = MagicMock()
    fake_conn.execute.return_value.mappings.return_value.all.return_value = [
        {"pdata_id": "P1", "aroma": json.dumps(["Cherry", "Vanilla"])},
        {"pdata_id": "P2", "aroma": json.dumps(["Violet"])},
    ]
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_engine = MagicMock()
    fake_engine.connect.return_value = fake_conn

    result = fetch_aroma_tags(fake_engine, ["P1", "P2"])

    assert result == {"P1": ["Cherry", "Vanilla"], "P2": ["Violet"]}


def test_fetch_aroma_tags_empty_pdata_ids_returns_empty_dict_without_querying():
    fake_engine = MagicMock()
    result = fetch_aroma_tags(fake_engine, [])
    assert result == {}
    fake_engine.connect.assert_not_called()


def test_fetch_aroma_tags_skips_malformed_json():
    fake_conn = MagicMock()
    fake_conn.execute.return_value.mappings.return_value.all.return_value = [
        {"pdata_id": "P1", "aroma": "not valid json"},
        {"pdata_id": "P2", "aroma": json.dumps(["Rose"])},
    ]
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_engine = MagicMock()
    fake_engine.connect.return_value = fake_conn

    result = fetch_aroma_tags(fake_engine, ["P1", "P2"])

    assert result == {"P2": ["Rose"]}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_aroma.py -v -k fetch_aroma_tags
```

Expected: FAIL — `ImportError: cannot import name 'fetch_aroma_tags'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/aroma.py` 파일 끝에 추가:

```python
import json

from sqlalchemy import text
from sqlalchemy.engine import Engine


def fetch_aroma_tags(pos_engine: Engine, pdata_ids: list[str]) -> dict[str, list[str]]:
    """pos.tb_pdata.aroma를 pdata_id 목록으로 한 번에 조회한다. aroma가 JSON 배열이
    아니면(파싱 실패) 그 pdata_id는 결과에서 빠진다 — 호출 측이 "이 후보는 아로마
    정보 없음"으로 취급하면 된다."""
    if not pdata_ids:
        return {}
    with pos_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT pdata_id, aroma FROM tb_pdata WHERE pdata_id IN :pdata_ids").bindparams(
                pdata_ids=tuple(pdata_ids)
            )
        ).mappings().all()
    result: dict[str, list[str]] = {}
    for row in rows:
        try:
            tags = json.loads(row["aroma"])
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(tags, list):
            result[row["pdata_id"]] = tags
    return result
```

`json` import는 파일 상단으로 옮긴다 — `classify_aroma_tags` 위, 기존 `from typing import
Literal` 옆에 정리:

```python
import json
from typing import Literal

from sqlalchemy import text
from sqlalchemy.engine import Engine
```

(파일 끝에 추가했던 `import json`, `from sqlalchemy import text`, `from sqlalchemy.engine
import Engine`는 지우고 상단으로 합친다.)

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_aroma.py -v
```

Expected: 8개 PASS

- [ ] **Step 5: `bindparams` IN 절 실동작 로컬 검증**

Task 0에서 grant 받았으니 실제 DB로 확인:

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -c "
from app.db import pos_engine
from app.services.aroma import fetch_aroma_tags
r = fetch_aroma_tags(pos_engine, ['00000001_39d12755-169c-4c2f-abe9-3352d8aa7a65'])
print(r)
"
```

Expected: `{'00000001_39d12755-169c-4c2f-abe9-3352d8aa7a65': ['Blackcurrant', 'Cloves', 'Liquorice', 'Vanilla']}`
비슷한 형태(정확한 pdata_id가 이미 없어졌을 수도 있음 — 그러면 빈 dict `{}`가 나오는 것도
정상, 에러만 안 나면 됨).

- [ ] **Step 6: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/aroma.py backend/tests/test_aroma.py
git commit -m "feat: pos.tb_pdata에서 아로마 태그 일괄 조회하는 함수 추가"
```

---

## Task 4: 브랜드 기사(스토리) DB 조회

**Files:**
- Create: `backend/app/services/brand_content.py`
- Test: `backend/tests/test_brand_content.py`

`wine_article_brands`(article_id↔brand_name)로 후보 브랜드의 실제 기사를 찾고,
`wine_articles`에서 본문 발췌 + URL을 가져온다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_brand_content.py` 새 파일:

```python
from unittest.mock import MagicMock

from app.services.brand_content import fetch_brand_articles


def test_fetch_brand_articles_groups_by_brand_name():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "brand_name": "그르기치 힐스",
            "title": "미국 와인 추천 | 전설의 나파 명가",
            "excerpt": "레이건 대통령 방불 정상 만찬...",
            "external_url": "https://www.naracellar.com/bbs/board.php?wr_id=774",
        },
        {
            "brand_name": "몬테스",
            "title": "코스트코 와인 추천",
            "excerpt": "여름에 즐기는 데일리 와인 7선...",
            "external_url": "https://www.naracellar.com/bbs/board.php?wr_id=775",
        },
    ]

    result = fetch_brand_articles(session, ["그르기치 힐스", "몬테스", "매칭안됨브랜드"])

    assert set(result.keys()) == {"그르기치 힐스", "몬테스"}
    assert result["그르기치 힐스"][0]["title"] == "미국 와인 추천 | 전설의 나파 명가"
    assert result["그르기치 힐스"][0]["url"] == "https://www.naracellar.com/bbs/board.php?wr_id=774"


def test_fetch_brand_articles_empty_brand_list_returns_empty_dict_without_querying():
    session = MagicMock()
    result = fetch_brand_articles(session, [])
    assert result == {}
    session.execute.assert_not_called()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_brand_content.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.brand_content'`

- [ ] **Step 3: 구현**

`backend/app/services/brand_content.py` 새 파일:

```python
from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_brand_articles(session: Session, brand_names: list[str]) -> dict[str, list[dict]]:
    """wine_article_brands로 브랜드명↔기사 매칭을 찾고, 기사 제목/발췌/URL을 브랜드명
    기준으로 묶어서 반환한다. 매칭 기사가 없는 브랜드는 결과 dict에 키 자체가 없다
    (호출 측이 "이 브랜드는 스토리 없음"으로 취급하면 됨)."""
    if not brand_names:
        return {}
    rows = session.execute(
        text(
            """
            SELECT b.brand_name, a.title, a.excerpt, a.external_url
            FROM wine_info.wine_article_brands b
            JOIN wine_info.wine_articles a ON a.id = b.article_id
            WHERE b.brand_name IN :brand_names
            """
        ).bindparams(brand_names=tuple(brand_names))
    ).mappings().all()

    result: dict[str, list[dict]] = {}
    for row in rows:
        result.setdefault(row["brand_name"], []).append(
            {"title": row["title"], "excerpt": row["excerpt"], "url": row["external_url"]}
        )
    return result


def fetch_brand_intro(session: Session, brand_names: list[str]) -> dict[str, str]:
    """brand_intro.introText를 브랜드명 기준으로 조회한다."""
    if not brand_names:
        return {}
    rows = session.execute(
        text(
            "SELECT brandName, introText FROM wine_info.brand_intro WHERE brandName IN :brand_names"
        ).bindparams(brand_names=tuple(brand_names))
    ).mappings().all()
    return {row["brandName"]: row["introText"] for row in rows}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_brand_content.py -v
```

Expected: 2개 PASS

- [ ] **Step 5: `fetch_brand_intro` 테스트도 추가**

`backend/tests/test_brand_content.py`에 추가:

```python
from app.services.brand_content import fetch_brand_intro


def test_fetch_brand_intro_returns_dict_keyed_by_brand_name():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {"brandName": "그르기치 힐스", "introText": "나파 밸리의 전설..."},
    ]
    result = fetch_brand_intro(session, ["그르기치 힐스"])
    assert result == {"그르기치 힐스": "나파 밸리의 전설..."}


def test_fetch_brand_intro_empty_list_returns_empty_dict_without_querying():
    session = MagicMock()
    result = fetch_brand_intro(session, [])
    assert result == {}
    session.execute.assert_not_called()
```

Run: `cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend && .venv/bin/python -m pytest tests/test_brand_content.py -v`
Expected: 4개 PASS

- [ ] **Step 6: 실DB 검증**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -c "
from app.db import SessionLocal
from app.services.brand_content import fetch_brand_articles, fetch_brand_intro
s = SessionLocal()
print(fetch_brand_articles(s, ['그르기치 힐스']))
print(fetch_brand_intro(s, ['몬테스']))
"
```

Expected: 에러 없이 dict 출력(내용이 비어있어도 됨 — 브랜드명이 실제 DB 표기와 다를 수 있음,
중요한 건 "Access denied" 안 뜨는 것).

- [ ] **Step 7: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/brand_content.py backend/tests/test_brand_content.py
git commit -m "feat: 브랜드 기사/소개글 DB 조회 함수 추가 (브라켓 3·4경기용)"
```

---

## Task 5: Gemini로 스토리·철학 문구 생성

**Files:**
- Create: `backend/app/services/bracket_content.py`
- Test: `backend/tests/test_bracket_content.py`

3경기(실존 인물/행사 언급 판별+요약), 4경기(철학 문구 요약)를 Gemini로 생성. `pairing.py`의
`_call_gemini` 패턴 재사용(별도 함수, 같은 REST 호출 방식).

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_bracket_content.py` 새 파일:

```python
import json
from unittest.mock import patch

from app.services.bracket_content import summarize_philosophy, verify_story_mention


def test_summarize_philosophy_returns_gemini_text():
    with patch(
        "app.services.bracket_content._call_gemini_text",
        return_value="포도 본연의 생명력을 지키는 철학.",
    ):
        result = summarize_philosophy("나파 밸리의 전설로 불리는 그르기치 힐스는...")
    assert result == "포도 본연의 생명력을 지키는 철학."


def test_verify_story_mention_returns_parsed_result_when_found():
    fake_response = json.dumps({"has_mention": True, "quote": "레이건 대통령 방불 정상 만찬주로 선정됐어요"})
    with patch("app.services.bracket_content._call_gemini_text", return_value=fake_response):
        result = verify_story_mention("레이건 대통령 방불 정상 만찬...")
    assert result == "레이건 대통령 방불 정상 만찬주로 선정됐어요"


def test_verify_story_mention_returns_none_when_not_found():
    fake_response = json.dumps({"has_mention": False, "quote": None})
    with patch("app.services.bracket_content._call_gemini_text", return_value=fake_response):
        result = verify_story_mention("그냥 평범한 데일리 와인 소개글...")
    assert result is None


def test_verify_story_mention_returns_none_on_call_failure():
    with patch("app.services.bracket_content._call_gemini_text", side_effect=RuntimeError("network")):
        result = verify_story_mention("아무 텍스트")
    assert result is None


def test_verify_story_mention_returns_none_on_bad_json():
    with patch("app.services.bracket_content._call_gemini_text", return_value="이건 JSON 아님"):
        result = verify_story_mention("아무 텍스트")
    assert result is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket_content.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.bracket_content'`

- [ ] **Step 3: 구현**

`backend/app/services/bracket_content.py` 새 파일:

```python
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
    except json.JSONDecodeError as e:
        logger.warning("스토리 언급 판별 응답 파싱 실패: raw=%r error=%s", raw, e)
        return None

    if not data.get("has_mention"):
        return None
    return data.get("quote") or None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket_content.py -v
```

Expected: 5개 PASS

- [ ] **Step 5: 실제 Gemini 호출로 검증**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -c "
from app.services.bracket_content import summarize_philosophy, verify_story_mention
print(summarize_philosophy('나파 밸리의 전설로 불리는 그르기치 힐스는 100% 유기농법으로 재배한 포도만 사용하며 인위적인 조작을 배제한다.'))
print(verify_story_mention('레이건 대통령 방불 정상 만찬, 엘리자베스 2세 여왕의 자리 등 세계 정상들의 식탁에 오르는 영예를 누렸습니다.'))
print(verify_story_mention('부담 없이 즐기기 좋은 데일리 와인입니다.'))
"
```

Expected: 첫 줄은 철학 문구 텍스트, 둘째 줄은 인용구 텍스트, 셋째 줄은 `None` — **단,
GEMINI_API_KEY 쿼터가 지금 0인 상태로 확인됐던 적이 있음(이 세션 앞부분 기록 참고)이라
`429 Too Many Requests`가 나면 코드는 정상 동작한 것(에러 잡아서 None 반환)이니 그 자체는
막지 말고, 실제 텍스트 생성 확인은 쿼터 정상화 후 재검증으로 남겨둔다.**

- [ ] **Step 6: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/bracket_content.py backend/tests/test_bracket_content.py
git commit -m "feat: Gemini로 브랜드 철학 문구/스토리 언급 판별 생성하는 함수 추가"
```

---

## Task 6: 브라켓 스키마

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: `BracketCard`/`BracketMatch`/`BracketResponse` 추가**

`backend/app/schemas.py` 파일 끝에 추가:

```python
class BracketCard(WineCard):
    axis_label: str


class BracketMatch(BaseModel):
    round: str
    axis: str
    cards: list[BracketCard]


class BracketResponse(BaseModel):
    matches: list[BracketMatch]
```

- [ ] **Step 2: import 확인 및 타입체크**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -c "from app.schemas import BracketCard, BracketMatch, BracketResponse; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/schemas.py
git commit -m "feat: 브라켓 응답 스키마(BracketCard/BracketMatch/BracketResponse) 추가"
```

---

## Task 7: 브라켓 후보 선정 로직 (오케스트레이션)

**Files:**
- Create: `backend/app/services/bracket.py`
- Test: `backend/tests/test_bracket.py`

후보 풀에서 4경기(8명, item_cd 중복 없이) 뽑는 핵심 로직. Gemini/DB 호출부는 모두 함수
인자로 주입받아서(dependency injection) 순수하게 테스트 가능하게 만든다.

- [ ] **Step 1: 실패하는 테스트 작성 — 1경기(산도) 선정**

`backend/tests/test_bracket.py` 새 파일:

```python
from app.services.bracket import pick_acidity_match


def _candidate(item_cd: str, acidity: int, brand: str = "브랜드") -> dict:
    return {"itemCd": item_cd, "brandName": brand, "taste": {"acidity": acidity}}


def test_pick_acidity_match_picks_max_and_min():
    pool = [_candidate("A", 1), _candidate("B", 5), _candidate("C", 3)]
    high, low = pick_acidity_match(pool)
    assert high["itemCd"] == "B"
    assert low["itemCd"] == "A"


def test_pick_acidity_match_returns_none_when_pool_too_small():
    pool = [_candidate("A", 3)]
    assert pick_acidity_match(pool) is None


def test_pick_acidity_match_returns_none_for_empty_pool():
    assert pick_acidity_match([]) is None


def test_pick_acidity_match_treats_missing_taste_as_neutral():
    pool = [_candidate("A", 5), {"itemCd": "B", "brandName": "브랜드2", "taste": None}]
    high, low = pick_acidity_match(pool)
    assert high["itemCd"] == "A"
    assert low["itemCd"] == "B"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `pick_acidity_match` 구현**

`backend/app/services/bracket.py` 새 파일:

```python
def _acidity(candidate: dict) -> int:
    taste = candidate.get("taste") or {}
    return taste.get("acidity", 2)


def pick_acidity_match(pool: list[dict]) -> tuple[dict, dict] | None:
    """산도 최댓값/최솟값 후보 한 쌍을 뽑는다. 풀에 서로 다른 후보가 2개 미만이면
    None(1경기 자체를 못 만든다는 뜻 — 호출 측이 브라켓 전체를 4경기 미만으로
    줄이거나 에러 처리한다)."""
    if len(pool) < 2:
        return None
    sorted_pool = sorted(pool, key=_acidity)
    return sorted_pool[-1], sorted_pool[0]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: 4개 PASS

- [ ] **Step 5: 2경기(아로마) 선정 — 실패하는 테스트**

`backend/tests/test_bracket.py`에 추가:

```python
from app.services.bracket import pick_aroma_match


def test_pick_aroma_match_picks_one_fruit_one_floral():
    pool = [
        {"itemCd": "A", "pdataId": "P1"},
        {"itemCd": "B", "pdataId": "P2"},
        {"itemCd": "C", "pdataId": "P3"},
    ]
    aroma_by_pdata_id = {
        "P1": ["Cherry", "Plum"],  # fruit
        "P2": ["Violet", "Leather"],  # floral_tertiary
        "P3": ["Blackberry"],  # fruit
    }
    fruit, floral = pick_aroma_match(pool, aroma_by_pdata_id)
    assert fruit["itemCd"] == "A"
    assert floral["itemCd"] == "B"


def test_pick_aroma_match_returns_none_when_only_one_side_available():
    pool = [{"itemCd": "A", "pdataId": "P1"}, {"itemCd": "B", "pdataId": "P2"}]
    aroma_by_pdata_id = {"P1": ["Cherry"], "P2": ["Blackberry"]}  # 둘 다 fruit
    assert pick_aroma_match(pool, aroma_by_pdata_id) is None


def test_pick_aroma_match_skips_candidates_without_aroma_data():
    pool = [
        {"itemCd": "A", "pdataId": "P1"},
        {"itemCd": "B", "pdataId": None},
        {"itemCd": "C", "pdataId": "P3"},
    ]
    aroma_by_pdata_id = {"P1": ["Cherry"], "P3": ["Violet"]}
    fruit, floral = pick_aroma_match(pool, aroma_by_pdata_id)
    assert fruit["itemCd"] == "A"
    assert floral["itemCd"] == "C"
```

- [ ] **Step 6: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v -k aroma
```

Expected: FAIL — `ImportError: cannot import name 'pick_aroma_match'`

- [ ] **Step 7: `pick_aroma_match` 구현**

`backend/app/services/bracket.py`에 추가(파일 상단에 import 추가):

```python
from app.services.aroma import classify_aroma_tags


def pick_aroma_match(pool: list[dict], aroma_by_pdata_id: dict[str, list[str]]) -> tuple[dict, dict] | None:
    """과일향 후보 하나, 꽃·2,3차향 후보 하나를 뽑는다. 아로마 데이터가 없는
    후보(pdataId 없음 또는 조회 결과에 없음)는 건너뛴다. 둘 중 한쪽이라도 없으면
    None."""
    fruit_candidates = []
    floral_candidates = []
    for c in pool:
        pdata_id = c.get("pdataId")
        if not pdata_id or pdata_id not in aroma_by_pdata_id:
            continue
        tags = aroma_by_pdata_id[pdata_id]
        if classify_aroma_tags(tags) == "fruit":
            fruit_candidates.append(c)
        else:
            floral_candidates.append(c)
    if not fruit_candidates or not floral_candidates:
        return None
    return fruit_candidates[0], floral_candidates[0]
```

- [ ] **Step 8: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: 7개 PASS (앞 4개 + 새 3개)

- [ ] **Step 9: 중복 제외 헬퍼 — 실패하는 테스트**

`backend/tests/test_bracket.py`에 추가:

```python
from app.services.bracket import exclude_used


def test_exclude_used_removes_matched_item_cds():
    pool = [{"itemCd": "A"}, {"itemCd": "B"}, {"itemCd": "C"}]
    used = {"A", "C"}
    result = exclude_used(pool, used)
    assert [c["itemCd"] for c in result] == ["B"]


def test_exclude_used_with_empty_used_set_returns_pool_unchanged():
    pool = [{"itemCd": "A"}, {"itemCd": "B"}]
    assert exclude_used(pool, set()) == pool
```

- [ ] **Step 10: 테스트 실패 확인 후 구현**

Run: `.venv/bin/python -m pytest tests/test_bracket.py -v -k exclude_used`
Expected: FAIL

`backend/app/services/bracket.py`에 추가:

```python
def exclude_used(pool: list[dict], used_item_cds: set[str]) -> list[dict]:
    return [c for c in pool if c["itemCd"] not in used_item_cds]
```

Run: `.venv/bin/python -m pytest tests/test_bracket.py -v`
Expected: 9개 PASS

- [ ] **Step 11: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/bracket.py backend/tests/test_bracket.py
git commit -m "feat: 브라켓 1·2경기(산도/아로마) 후보 선정 순수 로직 추가"
```

---

## Task 8: 3·4경기 후보 선정 (브랜드 다양성 + Gemini 연동)

**Files:**
- Modify: `backend/app/services/bracket.py`
- Test: `backend/tests/test_bracket.py`

3경기는 브랜드별 기사에서 `verify_story_mention`으로 실제 언급 있는 후보 2개(서로 다른
브랜드)를 찾는다. 4경기는 브랜드 소개글 있는 후보 2개(서로 다른 브랜드)를 뽑아
`summarize_philosophy`로 문구를 만든다. 둘 다 Gemini 호출 함수를 인자로 주입받아 테스트에서
mock 가능하게 한다.

- [ ] **Step 1: 실패하는 테스트 작성 — 3경기**

`backend/tests/test_bracket.py`에 추가:

```python
from app.services.bracket import pick_story_match


def test_pick_story_match_picks_two_distinct_brands_with_verified_mentions():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
        {"itemCd": "C", "brandName": "브랜드1"},  # 브랜드1과 중복이라 스킵돼야 함
    ]
    articles_by_brand = {
        "브랜드1": [{"title": "t1", "excerpt": "레이건 대통령 만찬", "url": "u1"}],
        "브랜드2": [{"title": "t2", "excerpt": "올림픽 만찬주", "url": "u2"}],
    }

    def fake_verify(text: str) -> str | None:
        return "검증된 인용구: " + text[:5]

    result = pick_story_match(pool, articles_by_brand, verify_fn=fake_verify)

    assert result is not None
    (card_a, quote_a, url_a), (card_b, quote_b, url_b) = result
    assert card_a["itemCd"] == "A"
    assert card_b["itemCd"] == "B"
    assert quote_a is not None and quote_a.startswith("검증된 인용구")
    assert url_a == "u1"
    assert url_b == "u2"


def test_pick_story_match_fills_remaining_slot_with_unverified_candidate():
    """검증된 언급이 1개뿐이면, 남은 자리는 브랜드만 다른 후보로 채우고 quote/url은
    None으로 둔다 — 없는 이야기를 지어내지 않되, 경기는 항상 2장으로 채운다."""
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
        {"itemCd": "C", "brandName": "브랜드3"},
    ]
    articles_by_brand = {
        "브랜드1": [{"title": "t1", "excerpt": "레이건 대통령 만찬", "url": "u1"}],
        "브랜드2": [{"title": "t2", "excerpt": "그냥 홍보문구", "url": "u2"}],
    }

    def fake_verify(text: str) -> str | None:
        return "인용구" if "대통령" in text else None

    result = pick_story_match(pool, articles_by_brand, verify_fn=fake_verify)

    assert result is not None
    (card_a, quote_a, url_a), (card_b, quote_b, url_b) = result
    assert card_a["itemCd"] == "A"
    assert quote_a == "인용구"
    assert url_a == "u1"
    assert card_b["itemCd"] == "B"
    assert quote_b is None
    assert url_b is None


def test_pick_story_match_all_unverified_still_fills_two_slots():
    pool = [{"itemCd": "A", "brandName": "브랜드1"}, {"itemCd": "B", "brandName": "브랜드2"}]
    result = pick_story_match(pool, {}, verify_fn=lambda t: "인용구")
    assert result is not None
    (card_a, quote_a, _), (card_b, quote_b, _) = result
    assert {card_a["itemCd"], card_b["itemCd"]} == {"A", "B"}
    assert quote_a is None
    assert quote_b is None


def test_pick_story_match_returns_none_when_fewer_than_two_distinct_brands_in_pool():
    pool = [{"itemCd": "A", "brandName": "브랜드1"}, {"itemCd": "C", "brandName": "브랜드1"}]
    result = pick_story_match(pool, {}, verify_fn=lambda t: "인용구")
    assert result is None
```

- [ ] **Step 2: 테스트 실패 확인 후 `pick_story_match` 구현**

Run: `.venv/bin/python -m pytest tests/test_bracket.py -v -k story`
Expected: FAIL

`backend/app/services/bracket.py`에 추가:

```python
from typing import Callable

StoryVerifyFn = Callable[[str], str | None]


def pick_story_match(
    pool: list[dict], articles_by_brand: dict[str, list[dict]], verify_fn: StoryVerifyFn
) -> tuple[tuple[dict, str | None, str | None], tuple[dict, str | None, str | None]] | None:
    """기사가 있는 브랜드 중 실제 인물/행사 언급이 검증된 후보를 우선으로 찾는다.
    검증된 후보가 2개 미만이면, 브랜드만 다른 나머지 후보로 남은 자리를 채운다
    (quote/url은 None — 없는 이야기를 지어내지 않는다, 대신 경기 자체는 후보만
    있으면 항상 채운다). 서로 다른 브랜드가 풀에 2개 미만이면 그때만 None(경기
    자체를 못 만듦)."""
    verified: list[tuple[dict, str, str]] = []
    seen_brands: set[str] = set()
    for candidate in pool:
        brand = candidate.get("brandName")
        if not brand or brand in seen_brands:
            continue
        articles = articles_by_brand.get(brand)
        if not articles:
            continue
        quote = verify_fn(articles[0]["excerpt"] or articles[0]["title"])
        if quote is None:
            continue
        verified.append((candidate, quote, articles[0]["url"]))
        seen_brands.add(brand)
        if len(verified) == 2:
            return verified[0], verified[1]

    fallback: list[tuple[dict, str | None, str | None]] = list(verified)
    for candidate in pool:
        brand = candidate.get("brandName")
        if not brand or brand in seen_brands:
            continue
        fallback.append((candidate, None, None))
        seen_brands.add(brand)
        if len(fallback) == 2:
            break

    if len(fallback) < 2:
        return None
    return fallback[0], fallback[1]
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: 전부 PASS

- [ ] **Step 4: 실패하는 테스트 작성 — 4경기**

`backend/tests/test_bracket.py`에 추가:

```python
from app.services.bracket import pick_philosophy_match


def test_pick_philosophy_match_picks_two_distinct_brands_with_summaries():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
    ]
    intro_by_brand = {"브랜드1": "소개글1", "브랜드2": "소개글2"}

    def fake_summarize(text: str) -> str | None:
        return "요약: " + text

    result = pick_philosophy_match(pool, intro_by_brand, summarize_fn=fake_summarize)

    assert result is not None
    (card_a, summary_a), (card_b, summary_b) = result
    assert card_a["itemCd"] == "A"
    assert summary_a == "요약: 소개글1"
    assert card_b["itemCd"] == "B"
    assert summary_b == "요약: 소개글2"


def test_pick_philosophy_match_returns_none_when_fewer_than_two_intros_available():
    pool = [{"itemCd": "A", "brandName": "브랜드1"}]
    intro_by_brand = {"브랜드1": "소개글1"}
    result = pick_philosophy_match(pool, intro_by_brand, summarize_fn=lambda t: "요약")
    assert result is None


def test_pick_philosophy_match_skips_when_summarize_fails():
    pool = [
        {"itemCd": "A", "brandName": "브랜드1"},
        {"itemCd": "B", "brandName": "브랜드2"},
        {"itemCd": "C", "brandName": "브랜드3"},
    ]
    intro_by_brand = {"브랜드1": "x", "브랜드2": "y", "브랜드3": "z"}

    def fake_summarize(text: str) -> str | None:
        return None if text == "x" else "요약: " + text

    result = pick_philosophy_match(pool, intro_by_brand, summarize_fn=fake_summarize)
    assert result is not None
    (card_a, _), (card_b, _) = result
    assert {card_a["itemCd"], card_b["itemCd"]} == {"B", "C"}
```

- [ ] **Step 5: 테스트 실패 확인 후 `pick_philosophy_match` 구현**

Run: `.venv/bin/python -m pytest tests/test_bracket.py -v -k philosophy`
Expected: FAIL

`backend/app/services/bracket.py`에 추가:

```python
PhilosophySummarizeFn = Callable[[str], str | None]


def pick_philosophy_match(
    pool: list[dict], intro_by_brand: dict[str, str], summarize_fn: PhilosophySummarizeFn
) -> tuple[tuple[dict, str], tuple[dict, str]] | None:
    """소개글 있는 브랜드 중 요약 생성에 성공한 후보 2개(서로 다른 브랜드)를 찾는다.
    각 결과는 (카드, 철학 문구) 튜플."""
    found: list[tuple[dict, str]] = []
    seen_brands: set[str] = set()
    for candidate in pool:
        brand = candidate.get("brandName")
        if not brand or brand in seen_brands:
            continue
        intro = intro_by_brand.get(brand)
        if not intro:
            continue
        summary = summarize_fn(intro)
        if summary is None:
            continue
        found.append((candidate, summary))
        seen_brands.add(brand)
        if len(found) == 2:
            return found[0], found[1]
    return None
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: 전부 PASS (15개)

- [ ] **Step 7: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/bracket.py backend/tests/test_bracket.py
git commit -m "feat: 브라켓 3·4경기(스토리/철학) 후보 선정 로직 추가"
```

---

## Task 9: 후보 풀 조회(지역 자동 확장) + 대진표 전체 조립

**Files:**
- Modify: `backend/app/services/bracket.py`
- Test: `backend/tests/test_bracket.py`

지역이 좁아서 후보가 부족하면 같은 타입 내 다른 지역까지 확장해서 풀을 채우는 함수, 그리고
1~4경기를 전부 조립해 `BracketResponse`를 만드는 최상위 함수.

- [ ] **Step 1: 실패하는 테스트 작성 — 지역 확장 풀 조회**

`backend/tests/test_bracket.py`에 추가:

```python
from app.services.bracket import build_candidate_pool


def test_build_candidate_pool_expands_regions_until_min_size_met():
    from app.services.region_cache import CountryRegions, RegionCount

    order = [
        CountryRegions(
            country="France",
            sku_count=10,
            regions=[
                RegionCount(label="보르도", sku_count=1),
                RegionCount(label="부르고뉴", sku_count=9),
            ],
        )
    ]

    call_log = []

    def fake_search(country: str, region: str, price_min: int, price_max):
        call_log.append(region)
        if region == "보르도":
            return [{"itemCd": "A", "brandName": "b1"}]
        return [{"itemCd": f"BG{i}", "brandName": f"bg{i}"} for i in range(10)]

    pool = build_candidate_pool(
        order=order, country_index=0, region_index=0, min_size=8, search_fn=fake_search
    )

    assert call_log == ["보르도", "부르고뉴"]
    assert len(pool) == 11  # 보르도 1개 + 부르고뉴 10개


def test_build_candidate_pool_dedupes_by_item_cd_across_regions():
    from app.services.region_cache import CountryRegions, RegionCount

    order = [
        CountryRegions(
            country="France",
            sku_count=5,
            regions=[RegionCount(label="R1", sku_count=1), RegionCount(label="R2", sku_count=1)],
        )
    ]

    def fake_search(country: str, region: str, price_min: int, price_max):
        return [{"itemCd": "DUP", "brandName": "b"}]

    pool = build_candidate_pool(
        order=order, country_index=0, region_index=0, min_size=8, search_fn=fake_search
    )

    assert len(pool) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v -k build_candidate_pool
```

Expected: FAIL

- [ ] **Step 3: `build_candidate_pool` 구현**

`backend/app/services/bracket.py`에 추가(상단에 import 추가):

```python
from typing import Callable

from app.services.price_tiers import widen_tier_ranges
from app.services.region_cache import CountryRegions

PoolSearchFn = Callable[[str, str, int, int | None], list[dict]]


def build_candidate_pool(
    order: list[CountryRegions],
    country_index: int,
    region_index: int,
    min_size: int,
    search_fn: PoolSearchFn,
    price_min: int = 0,
    price_max: int | None = None,
) -> list[dict]:
    """사용자가 고른 지역부터 시작해서, 후보가 min_size를 채울 때까지 같은 타입
    내 다른 지역을 순서대로 추가한다(region_cache 순서 재사용 — SKU 많은 지역
    순). item_cd 기준 dedupe."""
    country_entry = order[country_index % len(order)]
    n_regions = len(country_entry.regions)
    seen: set[str] = set()
    pool: list[dict] = []
    for offset in range(n_regions):
        region_entry = country_entry.regions[(region_index + offset) % n_regions]
        results = search_fn(country_entry.country, region_entry.label, price_min, price_max)
        for r in results:
            if r["itemCd"] in seen:
                continue
            seen.add(r["itemCd"])
            pool.append(r)
        if len(pool) >= min_size:
            break
    return pool
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: 전부 PASS (17개)

- [ ] **Step 5: 최상위 조립 함수 `build_bracket` — 실패하는 테스트**

`backend/tests/test_bracket.py`에 추가:

```python
from app.services.bracket import build_bracket


def test_build_bracket_assembles_up_to_four_matches():
    pool = [
        {"itemCd": "A", "brandName": "b1", "pdataId": "P1", "taste": {"acidity": 5}},
        {"itemCd": "B", "brandName": "b2", "pdataId": "P2", "taste": {"acidity": 0}},
        {"itemCd": "C", "brandName": "b3", "pdataId": "P3", "taste": {"acidity": 3}},
        {"itemCd": "D", "brandName": "b4", "pdataId": "P4", "taste": {"acidity": 3}},
        {"itemCd": "E", "brandName": "b5", "pdataId": None, "taste": {"acidity": 3}},
        {"itemCd": "F", "brandName": "b6", "pdataId": None, "taste": {"acidity": 3}},
    ]
    aroma_by_pdata_id = {"P3": ["Cherry"], "P4": ["Violet"]}
    articles_by_brand = {"b5": [{"title": "t", "excerpt": "레이건 대통령 만찬", "url": "u5"}]}
    intro_by_brand = {"b6": "소개글"}

    result = build_bracket(
        pool=pool,
        aroma_by_pdata_id=aroma_by_pdata_id,
        articles_by_brand=articles_by_brand,
        intro_by_brand=intro_by_brand,
        verify_fn=lambda t: "검증된 인용구" if "대통령" in t else None,
        summarize_fn=lambda t: "요약: " + t,
    )

    axes = [m.axis for m in result.matches]
    assert axes == ["acidity", "aroma", "story", "philosophy"]
    acidity_match = result.matches[0]
    assert {c.item_cd for c in acidity_match.cards} == {"A", "B"}
```

- [ ] **Step 6: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v -k build_bracket
```

Expected: FAIL

- [ ] **Step 7: `build_bracket` 구현**

`_to_card`(recommend.py에 있는 후보→WineCard 변환)를 재사용해서 `BracketCard`를 만든다.
`backend/app/services/bracket.py` 상단 import에 추가:

```python
from app.routers.recommend import _to_card
from app.schemas import BracketCard, BracketMatch, BracketResponse
```

`backend/app/services/bracket.py`에 추가:

```python
def _to_bracket_card(candidate: dict, axis_label: str) -> BracketCard:
    base = _to_card(candidate)
    return BracketCard(**base.model_dump(), axis_label=axis_label)


def build_bracket(
    pool: list[dict],
    aroma_by_pdata_id: dict[str, list[str]],
    articles_by_brand: dict[str, list[dict]],
    intro_by_brand: dict[str, str],
    verify_fn: StoryVerifyFn,
    summarize_fn: PhilosophySummarizeFn,
) -> BracketResponse:
    """4경기를 순서대로 조립한다. 각 경기는 이미 쓰인 item_cd를 제외한 풀에서
    후보를 뽑는다 — 경기 하나가 후보를 못 찾으면(None) 그 경기는 대진표에서
    빠진다(4경기 미만이 될 수 있음, 프론트가 이 경우도 처리해야 함)."""
    matches: list[BracketMatch] = []
    used: set[str] = set()
    remaining = pool

    acidity_pair = pick_acidity_match(remaining)
    if acidity_pair:
        high, low = acidity_pair
        used.update([high["itemCd"], low["itemCd"]])
        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="acidity",
                cards=[
                    _to_bracket_card(high, f"산도 {(high.get('taste') or {}).get('acidity', 2)}/5"),
                    _to_bracket_card(low, f"산도 {(low.get('taste') or {}).get('acidity', 2)}/5"),
                ],
            )
        )
    remaining = exclude_used(remaining, used)

    aroma_pair = pick_aroma_match(remaining, aroma_by_pdata_id)
    if aroma_pair:
        fruit, floral = aroma_pair
        used.update([fruit["itemCd"], floral["itemCd"]])
        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="aroma",
                cards=[
                    _to_bracket_card(fruit, "과일향 위주"),
                    _to_bracket_card(floral, "꽃·2,3차향 위주"),
                ],
            )
        )
    remaining = exclude_used(remaining, used)

    story_pair = pick_story_match(remaining, articles_by_brand, verify_fn)
    if story_pair:
        (card_a, quote_a, url_a), (card_b, quote_b, url_b) = story_pair
        used.update([card_a["itemCd"], card_b["itemCd"]])

        def _story_label(quote: str | None, url: str | None) -> str:
            if quote:
                return f"{quote} (출처: {url})"
            return "이 와인만의 알려진 이야기는 아직 없어요"

        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="story",
                cards=[
                    _to_bracket_card(card_a, _story_label(quote_a, url_a)),
                    _to_bracket_card(card_b, _story_label(quote_b, url_b)),
                ],
            )
        )
    remaining = exclude_used(remaining, used)

    philosophy_pair = pick_philosophy_match(remaining, intro_by_brand, summarize_fn)
    if philosophy_pair:
        (card_a, summary_a), (card_b, summary_b) = philosophy_pair
        matches.append(
            BracketMatch(
                round="quarterfinal",
                axis="philosophy",
                cards=[
                    _to_bracket_card(card_a, summary_a),
                    _to_bracket_card(card_b, summary_b),
                ],
            )
        )

    return BracketResponse(matches=matches)
```

- [ ] **Step 8: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket.py -v
```

Expected: 전부 PASS (18개)

- [ ] **Step 9: 순환 import 확인**

`bracket.py`가 `recommend.py`의 `_to_card`를 가져오는데, `recommend.py`가 나중에 `bracket.py`를
가져오지 않는지 확인(순환 import 방지):

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -c "import app.services.bracket; import app.routers.recommend; print('ok')"
```

Expected: `ok` (에러 없이)

- [ ] **Step 10: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/services/bracket.py backend/tests/test_bracket.py
git commit -m "feat: 지역 자동확장 후보풀 조회 + 4경기 대진표 조립 함수 추가"
```

---

## Task 10: `/api/bracket` 라우터

**Files:**
- Create: `backend/app/routers/bracket.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_bracket_router.py`

기존 `/api/recommend`와 같은 파라미터로 후보 풀을 조회하고, `build_bracket`으로 조립해
응답한다. 3·4경기용 DB 조회(`fetch_brand_articles`/`fetch_brand_intro`)와 아로마 조회
(`fetch_aroma_tags`)를 여기서 호출한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_bracket_router.py` 새 파일:

```python
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _candidate(item_cd: str, acidity: int, brand: str, pdata_id: str | None = None) -> dict:
    import json

    return {
        "itemCd": item_cd,
        "nameKo": f"와인 {item_cd}",
        "type": "Red",
        "producer": "{}",
        "variety": "{}",
        "country": "{}",
        "place": "{}",
        "taste_raw": json.dumps({"sweetness": 2, "acidity": acidity, "body": 2, "tannin": 2}),
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": pdata_id,
        "price_krw": 30000,
        "reviews": 0,
        "wishes": 0,
        "brandName": brand,
    }


def test_bracket_endpoint_returns_matches():
    pool = [_candidate("A", 5, "b1"), _candidate("B", 0, "b2")]
    with (
        patch("app.routers.bracket.query_candidates", return_value=pool),
        patch("app.routers.bracket.fetch_aroma_tags", return_value={}),
        patch("app.routers.bracket.fetch_brand_articles", return_value={}),
        patch("app.routers.bracket.fetch_brand_intro", return_value={}),
    ):
        response = client.get(
            "/api/bracket",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["axis"] == "acidity"


def test_bracket_endpoint_returns_404_when_pool_empty():
    with (
        patch("app.routers.bracket.query_candidates", return_value=[]),
        patch("app.routers.bracket.fetch_aroma_tags", return_value={}),
        patch("app.routers.bracket.fetch_brand_articles", return_value={}),
        patch("app.routers.bracket.fetch_brand_intro", return_value={}),
    ):
        response = client.get(
            "/api/bracket",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 404
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket_router.py -v
```

Expected: FAIL — `404 Not Found`(라우터가 아직 없어서) 또는 import 에러

- [ ] **Step 3: 라우터 구현**

`backend/app/routers/bracket.py` 새 파일:

```python
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
```

`_parse_json_field`가 `recommend.py`에 `_` 붙은 private-style 이름이라 다른 모듈에서 import해
쓰는 게 어색하지만, 기존 코드베이스에 이미 이런 패턴이 없어서 새로 원칙을 만들기보다 그대로
재사용한다(중복 정의보다 낫다는 판단 — 나중에 `recommend.py`와 `bracket.py`가 공유하는 파싱
유틸이 더 늘어나면 그때 `app/services/parsing.py`로 뽑아도 됨).

- [ ] **Step 4: `main.py`에 라우터 등록**

`backend/app/main.py`를 이렇게 바꾼다:

```python
from fastapi import FastAPI

from app.routers.bracket import router as bracket_router
from app.routers.images import router as images_router
from app.routers.recommend import router as recommend_router

app = FastAPI(title="AI Wine Recommend API")
app.include_router(recommend_router)
app.include_router(bracket_router)
app.include_router(images_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest tests/test_bracket_router.py -v
```

Expected: 2개 PASS

- [ ] **Step 6: 전체 백엔드 테스트 스위트 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/python -m pytest -q
```

Expected: 전부 PASS, 에러 0.

- [ ] **Step 7: 실서버 데이터로 수동 검증**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/uvicorn app.main:app --reload --port 8000 &
sleep 2
curl -sS -G "http://127.0.0.1:8000/api/bracket" \
  --data-urlencode "price_tier=3" --data-urlencode "country_index=0" \
  --data-urlencode "region_index=0" --data-urlencode "wine_type=Red" | python3 -m json.tool | head -60
```

Expected: HTTP 200, `matches` 배열에 1~4개 경기. Gemini 쿼터 문제로 story/philosophy 경기가
안 나올 수 있음(그럼 `matches` 길이가 2가 됨) — 그 자체는 정상 동작(코드가 에러 없이 우아하게
줄어드는 것), 실제 콘텐츠 품질 확인은 쿼터 정상화 후.

- [ ] **Step 8: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add backend/app/routers/bracket.py backend/app/main.py backend/tests/test_bracket_router.py
git commit -m "feat: GET /api/bracket 엔드포인트 추가"
```

---

## Task 11: 프론트 — 타입 + API 클라이언트

**Files:**
- Modify: `frontend/app/api.ts`

- [ ] **Step 1: 브라켓 타입 + `fetchBracket` 추가**

`frontend/app/api.ts` 파일 끝에 추가:

```typescript
export interface BracketCard extends WineCard {
  axis_label: string;
}

export interface BracketMatch {
  round: "quarterfinal" | "semifinal" | "final";
  axis: string;
  cards: BracketCard[];
}

export interface BracketResponse {
  matches: BracketMatch[];
}

export interface BracketParams {
  priceTier: number;
  countryIndex: number;
  regionIndex: number;
  wineType: WineType;
  pairingText?: string;
}

export async function fetchBracket(params: BracketParams): Promise<BracketResponse> {
  const search = new URLSearchParams({
    price_tier: String(params.priceTier),
    country_index: String(params.countryIndex),
    region_index: String(params.regionIndex),
    wine_type: params.wineType,
  });
  if (params.pairingText) search.set("pairing_text", params.pairingText);

  const response = await fetch(`/api/bracket?${search.toString()}`);
  if (!response.ok) throw new Error(`bracket 요청 실패: ${response.status}`);
  return response.json();
}
```

- [ ] **Step 2: 타입체크**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend
npx tsc --noEmit
```

Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/app/api.ts
git commit -m "feat: 프론트 브라켓 타입 + fetchBracket API 클라이언트 추가"
```

---

## Task 12: 프론트 — 브라켓 진행 상태 훅

**Files:**
- Create: `frontend/app/useBracket.ts`

8강→준결승→결승 진행 상태를 관리하는 커스텀 훅. `page.tsx`에서 쓰기 쉽게 로직을 분리한다
(파일 하나에 다 몰아넣지 않기 위함 — page.tsx가 이미 400줄에 가까움).

- [ ] **Step 1: 구현**

`frontend/app/useBracket.ts` 새 파일:

```typescript
import { useState } from "react";
import type { BracketCard, BracketMatch, BracketResponse } from "./api";

export type BracketPhase = "quarterfinal" | "semifinal" | "final" | "done";

export interface CurrentMatch {
  phase: BracketPhase;
  axis: string;
  cards: BracketCard[];
}

export interface UseBracketResult {
  currentMatch: CurrentMatch | null;
  winner: BracketCard | null;
  pickWinner: (card: BracketCard) => void;
  reset: (data: BracketResponse) => void;
}

/** 8강(quarterfinal, 최대 4경기) → 준결승(semifinal, 2경기) → 결승(final, 1경기) 순서로
 * 진행한다. 8강 경기 수가 4보다 적으면(후보 부족으로 일부 경기가 빠진 경우) 그 수에 맞춰
 * 준결승/결승 규모도 자동으로 줄어든다 — 예: 8강 2경기만 있으면 승자 2명이 바로 결승으로. */
export function useBracket(): UseBracketResult {
  const [quarterfinals, setQuarterfinals] = useState<BracketMatch[]>([]);
  const [quarterfinalIndex, setQuarterfinalIndex] = useState(0);
  const [quarterfinalWinners, setQuarterfinalWinners] = useState<BracketCard[]>([]);
  const [semifinals, setSemifinals] = useState<BracketCard[][]>([]);
  const [semifinalIndex, setSemifinalIndex] = useState(0);
  const [semifinalWinners, setSemifinalWinners] = useState<BracketCard[]>([]);
  const [phase, setPhase] = useState<BracketPhase>("quarterfinal");
  const [winner, setWinner] = useState<BracketCard | null>(null);

  function reset(data: BracketResponse) {
    setQuarterfinals(data.matches);
    setQuarterfinalIndex(0);
    setQuarterfinalWinners([]);
    setSemifinals([]);
    setSemifinalIndex(0);
    setSemifinalWinners([]);
    setWinner(null);
    setPhase(data.matches.length > 0 ? "quarterfinal" : "done");
  }

  function pairUp(cards: BracketCard[]): BracketCard[][] {
    const pairs: BracketCard[][] = [];
    for (let i = 0; i < cards.length; i += 2) {
      if (i + 1 < cards.length) pairs.push([cards[i], cards[i + 1]]);
      else pairs.push([cards[i]]); // 홀수면 마지막 하나는 부전승
    }
    return pairs;
  }

  function pickWinner(card: BracketCard) {
    if (phase === "quarterfinal") {
      const nextWinners = [...quarterfinalWinners, card];
      if (quarterfinalIndex + 1 < quarterfinals.length) {
        setQuarterfinalWinners(nextWinners);
        setQuarterfinalIndex((i) => i + 1);
        return;
      }
      // 8강 끝 — 준결승 구성
      if (nextWinners.length === 1) {
        setWinner(nextWinners[0]);
        setPhase("done");
        return;
      }
      const pairs = pairUp(nextWinners);
      setSemifinals(pairs);
      setSemifinalIndex(0);
      setSemifinalWinners([]);
      setPhase(pairs.length === 1 && pairs[0].length === 1 ? "final" : "semifinal");
      if (pairs.length === 1 && pairs[0].length === 1) {
        setWinner(pairs[0][0]);
        setPhase("done");
      }
      return;
    }

    if (phase === "semifinal") {
      const nextWinners = [...semifinalWinners, card];
      if (semifinalIndex + 1 < semifinals.length) {
        setSemifinalWinners(nextWinners);
        setSemifinalIndex((i) => i + 1);
        return;
      }
      if (nextWinners.length === 1) {
        setWinner(nextWinners[0]);
        setPhase("done");
        return;
      }
      setPhase("final");
      setSemifinalWinners(nextWinners);
      return;
    }

    if (phase === "final") {
      setWinner(card);
      setPhase("done");
    }
  }

  let currentMatch: CurrentMatch | null = null;
  if (phase === "quarterfinal" && quarterfinals[quarterfinalIndex]) {
    const m = quarterfinals[quarterfinalIndex];
    currentMatch = { phase, axis: m.axis, cards: m.cards };
  } else if (phase === "semifinal" && semifinals[semifinalIndex]) {
    currentMatch = { phase, axis: "semifinal", cards: semifinals[semifinalIndex] };
  } else if (phase === "final") {
    currentMatch = { phase, axis: "final", cards: semifinalWinners };
  }

  return { currentMatch, winner, pickWinner, reset };
}
```

- [ ] **Step 2: 타입체크**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend
npx tsc --noEmit
```

Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/app/useBracket.ts
git commit -m "feat: 8강-준결승-결승 진행 상태 관리하는 useBracket 훅 추가"
```

---

## Task 13: 프론트 — `page.tsx`를 브라켓으로 교체

**Files:**
- Modify: `frontend/app/page.tsx`

기존 다이얼+카드2장 결과화면 로직(`cardData`/`cards`/`toggleSave`/`exclude`/`priceUp` 등
`/api/recommend` 관련 부분)을 전부 브라켓으로 바꾼다. 인트로 3단계는 그대로 유지.

- [ ] **Step 1: import와 상단 유지되는 부분 확인**

`INTRO_STEPS`, `REAL_FOODS`/`FOODS`, `WINE_DETAIL_BASE`/`wineDetailUrl`은 그대로 재사용한다.
`fetchRecommendation`/`CardId`/`CardState`/`slotForCard`/`preferences.ts` import는 이번
브라켓 v1 스코프에서 안 쓴다(찜/배제는 브라켓에 연결 안 함 — 설계 문서 "비목표" 참고).

- [ ] **Step 2: 전체 파일 교체**

`frontend/app/page.tsx`를 통째로 이 내용으로 바꾼다:

```typescript
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "./wine-recommend.module.css";
import { fetchBracket, imageUrl, type BracketCard, type WineType } from "./api";
import { useBracket } from "./useBracket";

const REAL_FOODS = [
  { id: "삼겹살", label: "삼겹살" },
  { id: "치킨", label: "치킨" },
  { id: "스테이크", label: "스테이크" },
  { id: "파스타", label: "파스타" },
  { id: "초밥", label: "초밥" },
  { id: "치즈", label: "치즈 플래터" },
  { id: "매운탕", label: "매운탕" },
  { id: "피자", label: "피자" },
  { id: "디저트", label: "디저트" },
];
const FOODS = [...REAL_FOODS, { id: "custom", label: "직접 입력하기" }];
const WINE_DETAIL_BASE = "http://192.168.47.105/NID/wine-info/view.php";

const INTRO_STEPS: { question: string; options: { id: string | number; label: string }[] }[] = [
  {
    question: "오늘은 어떤 자리야?",
    options: [
      { id: "gift", label: "선물할 와인" },
      { id: "party", label: "파티, 다 같이" },
      { id: "solo", label: "혼자, 편하게" },
      { id: "anniversary", label: "기념일, 특별하게" },
    ],
  },
  {
    question: "가격대는 얼마쯤 생각해?",
    options: [
      { id: 0, label: "1만원 이하" }, { id: 1, label: "2만원대" }, { id: 2, label: "3만원대" },
      { id: 3, label: "5만원대" }, { id: 4, label: "7만원대" }, { id: 5, label: "10만원대" },
      { id: 6, label: "30만원대" }, { id: 7, label: "100만원대" }, { id: 8, label: "1000만원대" },
      { id: 9, label: "1000만원 이상" },
    ],
  },
  {
    question: "어떤 스타일이 끌려?",
    options: [
      { id: "Red", label: "레드" },
      { id: "White", label: "화이트" },
      { id: "Sparkling", label: "스파클링" },
    ],
  },
];

const AXIS_TITLE: Record<string, string> = {
  acidity: "산도가 다른 두 와인 — 뭐가 더 끌려?",
  aroma: "향이 다른 두 와인 — 뭐가 더 끌려?",
  story: "이야기가 있는 두 와인 — 뭐가 더 끌려?",
  philosophy: "철학이 다른 두 와인 — 뭐가 더 끌려?",
  semifinal: "준결승 — 뭐가 더 끌려?",
  final: "결승 — 최종 선택은?",
};

function wineDetailUrl(itemCd: string): string {
  return `${WINE_DETAIL_BASE}?itemCd=${encodeURIComponent(itemCd)}&cat=wine`;
}

export default function Home() {
  const [isIntro, setIsIntro] = useState(true);
  const [introStep, setIntroStep] = useState(0);
  const [typeAnswer, setTypeAnswer] = useState<WineType>("Red");
  const [regionIndex, setRegionIndex] = useState(0);
  const [countryIndex, setCountryIndex] = useState(0);
  const [tierIndex, setTierIndex] = useState(0);
  const [pairingText, setPairingText] = useState("");
  const [pairingChoice, setPairingChoice] = useState("");
  const [pairingCustom, setPairingCustom] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const bracket = useBracket();

  function selectIntro(stepIdx: number, value: string | number) {
    if (stepIdx === 1) setTierIndex(Number(value));
    if (stepIdx === 2) setTypeAnswer(value as WineType);
    if (stepIdx < 2) {
      setIntroStep(stepIdx + 1);
    } else {
      const pick = REAL_FOODS[Math.floor(Math.random() * REAL_FOODS.length)];
      setPairingChoice(pick.id);
      setPairingText(pick.id);
      setIsIntro(false);
    }
  }

  function goToStart() {
    setIsIntro(true);
    setIntroStep(0);
    setTierIndex(0);
    setRegionIndex(0);
    setCountryIndex(0);
    setPairingText("");
    setPairingChoice("");
    setPairingCustom("");
  }

  useEffect(() => {
    if (isIntro) return;
    let ignore = false;
    setLoading(true);
    setLoadError(false);
    fetchBracket({ priceTier: tierIndex, countryIndex, regionIndex, wineType: typeAnswer, pairingText })
      .then((data) => {
        if (!ignore) bracket.reset(data);
      })
      .catch(() => {
        if (!ignore) setLoadError(true);
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isIntro, typeAnswer, countryIndex, regionIndex, tierIndex, pairingText]);

  function priceUp() {
    if (tierIndex >= 9) return;
    setTierIndex((t) => t + 1);
  }
  function priceDown() {
    if (tierIndex <= 0) return;
    setTierIndex((t) => t - 1);
  }
  function regionNext() {
    setRegionIndex((r) => r + 1);
  }
  function countryNext() {
    setCountryIndex((c) => c + 1);
    setRegionIndex(0);
  }
  function submitCustom() {
    setPairingText(pairingCustom.trim());
  }
  function selectPairing(value: string) {
    setPairingChoice(value);
    if (value !== "custom") setPairingText(value);
  }
  function confirmPairing() {
    if (pairingChoice === "custom") {
      submitCustom();
      return;
    }
    const idx = REAL_FOODS.findIndex((f) => f.id === pairingChoice);
    const next = REAL_FOODS[(idx + 1 + REAL_FOODS.length) % REAL_FOODS.length];
    setPairingChoice(next.id);
    setPairingText(next.id);
  }

  function renderCard(card: BracketCard, showFullDetail: boolean) {
    return (
      <div
        key={card.item_cd}
        className={styles.card}
        onClick={() => bracket.pickWinner(card)}
      >
        <div className={styles.bottleWrap}>
          <div className={styles.bottleAnim}>
            {imageUrl(card.pdata_id) && (
              <img
                src={imageUrl(card.pdata_id)!}
                alt={card.wine_name}
                className={styles.bottleImg}
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                  e.currentTarget.nextElementSibling?.classList.remove(styles.hidden);
                }}
              />
            )}
            <div className={imageUrl(card.pdata_id) ? `${styles.labelPatch} ${styles.hidden}` : styles.labelPatch}>
              <div className={styles.labelRegion}>{card.region}</div>
              <div className={styles.labelGrape}>{card.grape}</div>
            </div>
          </div>
        </div>

        <div className={styles.wineName}>{card.wine_name}</div>
        <div className={styles.wineMeta}>{card.region}, {card.country} · {card.type_label_kr}</div>

        <div className={styles.priceRow}>
          <span className={styles.price}>₩{card.price_krw.toLocaleString()}</span>
          <span className={styles.priceDesc}>{card.price_desc}</span>
        </div>

        {!showFullDetail && <div className={styles.axisLabel}>{card.axis_label}</div>}

        {showFullDetail && (
          <>
            <div className={styles.note}>{card.note}</div>
            <div className={styles.personaBox}>
              <div className={styles.personaLine}>&ldquo;{card.persona_line}&rdquo;</div>
            </div>
            <a
              href={wineDetailUrl(card.item_cd)}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.resetLink}
              onClick={(e) => e.stopPropagation()}
            >
              상세 정보 보기 ↗
            </a>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div />
        <div className={styles.brand}>AI 와인 추천</div>
        <div className={styles.headerRight}>
          <div className={styles.tagline}>AI 소믈리에가 지금 이 순간에 맞는 와인을 골라줘요</div>
          <Link href="/liked" className={styles.backToStart}>
            찜한 와인
          </Link>
          {!isIntro && (
            <button type="button" onClick={goToStart} className={styles.backToStart}>
              처음으로
            </button>
          )}
        </div>
      </div>

      {isIntro ? (
        <div className={styles.introSection}>
          <div className={styles.dots}>
            {INTRO_STEPS.map((_, i) => (
              <div key={i} className={i <= introStep ? `${styles.dot} ${styles.dotActive}` : styles.dot} />
            ))}
          </div>
          <div key={introStep} className={styles.stepCard}>
            <div className={styles.stepHeader}>
              {introStep > 0 && (
                <button type="button" onClick={() => setIntroStep((s) => s - 1)} className={styles.stepBack}>
                  &#8592; 이전
                </button>
              )}
              <div className={styles.stepLabel}>Step {introStep + 1} / 3</div>
            </div>
            <div className={styles.question}>{INTRO_STEPS[introStep].question}</div>
            <div className={styles.options}>
              {INTRO_STEPS[introStep].options.map((opt) => (
                <button key={opt.id} type="button" className={styles.option} onClick={() => selectIntro(introStep, opt.id)}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className={styles.stage}>
          <div className={styles.priceUpWrap}>
            <button type="button" onClick={priceUp} disabled={tierIndex >= 9} className={tierIndex >= 9 ? `${styles.joyBtn} ${styles.joyBtnDisabled}` : styles.joyBtn}>
              <span className={styles.joyAccent}>&#9650;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyAccent}`}>가격 UP</div>
          </div>

          <div className={styles.regionWrap}>
            <button type="button" onClick={countryNext} className={styles.joyBtn}>
              <span className={styles.joyRegion}>&#9668;&#9668;</span>
            </button>
            <button type="button" onClick={regionNext} className={styles.joyBtn}>
              <span className={styles.joyRegion}>&#9664;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyRegion}`}>지역<br />변경</div>
          </div>

          <div className={styles.cardsRow}>
            {loading && <div className={styles.note}>추천 찾는 중...</div>}
            {!loading && loadError && <div className={styles.note}>추천을 못 찾았어요. 가격대나 지역을 바꿔보세요.</div>}
            {!loading && !loadError && bracket.currentMatch && (
              <>
                <div className={styles.bracketTitle}>{AXIS_TITLE[bracket.currentMatch.axis] ?? "뭐가 더 끌려?"}</div>
                <div className={styles.cardsRow}>
                  {bracket.currentMatch.cards.map((card) =>
                    renderCard(card, bracket.currentMatch!.phase === "final" || bracket.currentMatch!.phase === "semifinal")
                  )}
                </div>
              </>
            )}
            {!loading && !loadError && !bracket.currentMatch && bracket.winner && (
              <div className={styles.finalWrap}>
                <div className={styles.bracketTitle}>이 와인이야!</div>
                {renderCard(bracket.winner, true)}
              </div>
            )}
          </div>

          <div className={styles.pairingWrap}>
            <select
              value={pairingChoice}
              onChange={(e) => selectPairing(e.target.value)}
              className={styles.pairingSelect}
            >
              {FOODS.map((food) => (
                <option key={food.id} value={food.id}>{food.label}</option>
              ))}
            </select>
            {pairingChoice === "custom" && (
              <input
                type="text"
                value={pairingCustom}
                onChange={(e) => setPairingCustom(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitCustom()}
                placeholder="직접 입력"
                className={styles.pairingCustomInput}
              />
            )}
            <button type="button" onClick={confirmPairing} className={styles.joyBtn}>
              <span className={styles.joyPairing}>&#9654;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyPairing}`}>페어링<br />검색</div>
          </div>

          <div className={styles.priceDownWrap}>
            <button type="button" onClick={priceDown} disabled={tierIndex <= 0} className={tierIndex <= 0 ? `${styles.joyBtn} ${styles.joyBtnDisabled}` : styles.joyBtn}>
              <span className={styles.joyAccent}>&#9660;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyAccent}`}>가격 DOWN</div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 타입체크**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend
npx tsc --noEmit
```

Expected: 에러 없음 (다음 Task에서 `styles.axisLabel`/`styles.bracketTitle`/`styles.finalWrap`
CSS 클래스를 추가하기 전까지는, CSS Module은 존재하지 않는 클래스 참조에도 타입 에러를 안
내므로 이 단계 통과는 정상 — 시각 확인은 Task 14 이후).

- [ ] **Step 4: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/app/page.tsx
git commit -m "feat: 결과화면을 다이얼+카드2장에서 브라켓 진행으로 교체"
```

---

## Task 14: 프론트 — 브라켓 전용 스타일

**Files:**
- Modify: `frontend/app/wine-recommend.module.css`

- [ ] **Step 1: 클래스 추가**

`frontend/app/wine-recommend.module.css` 파일 끝에 추가:

```css
.bracketTitle {
  width: 100%;
  text-align: center;
  font-family: var(--font-serif-display);
  font-size: 22px;
  margin-bottom: 20px;
}
.axisLabel {
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--color-surface-tint);
  border-radius: var(--radius-lg);
  font-size: 12px;
  line-height: 1.5;
  color: color-mix(in srgb, var(--accent) 72%, #000);
  font-weight: 600;
  text-align: center;
}
.finalWrap {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
```

- [ ] **Step 2: 로컬에서 시각 확인**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/backend
.venv/bin/uvicorn app.main:app --reload --port 8000 &
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend
npm run dev &
sleep 3
```

브라우저(또는 `mcp__Claude_Browser__*` 도구)로 `http://localhost:3000` 열고:
1. 3단계 인트로 완료
2. 로딩 후 8강 첫 경기 카드 2장 + `axisLabel`(산도 표시) 보이는지 확인
3. 카드 클릭 → 다음 경기로 넘어가는지 확인
4. 4경기(또는 후보 부족으로 더 적은 경기) 다 끝나면 준결승/결승 진행되는지, 최종
   "이 와인이야!" 화면이 뜨는지 확인
5. 가격 UP/DOWN, 지역 변경, 페어링 변경 시 브라켓이 처음부터 다시 시작하는지 확인

- [ ] **Step 3: 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/app/wine-recommend.module.css
git commit -m "style: 브라켓 화면(경기 타이틀/축 라벨/최종화면) 스타일 추가"
```

---

## Task 15: 배포

**Files:** 없음(배포 작업)

- [ ] **Step 1: 서버로 소스 동기화**

```bash
rsync -az --delete \
  --exclude 'node_modules' --exclude '.next' --exclude '.git' \
  --exclude '__pycache__' --exclude '.venv' --exclude 'tsconfig.tsbuildinfo' \
  --exclude '.DS_Store' \
  -e "ssh -o StrictHostKeyChecking=no" \
  /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/ root@192.168.47.105:/var/www/NARA-APP-AI-Recommend/
```

- [ ] **Step 2: 컨테이너 재빌드**

```bash
ssh root@192.168.47.105 "cd /var/www/NARA-APP-AI-Recommend && docker compose up -d --build"
```

- [ ] **Step 3: 헬스체크 + 브라켓 엔드포인트 확인**

```bash
curl -sS "http://192.168.47.105:3005/" -o /dev/null -w "frontend:%{http_code}\n"
curl -sS -G "http://192.168.47.105:3005/api/bracket" \
  --data-urlencode "price_tier=3" --data-urlencode "country_index=0" \
  --data-urlencode "region_index=0" --data-urlencode "wine_type=Red" -w "\nHTTP:%{http_code}\n"
```

Expected: frontend 200, bracket 200(또는 후보 부족 시 404 — 그때는 다른 파라미터로 재시도).

- [ ] **Step 4: 허브 iframe에서 실제 화면 확인**

`192.168.47.105/NID/#/block/a2`에서 인트로부터 결승까지 한 번 실제로 진행해보고, 카드 클릭이
막힘없이 다음 경기로 넘어가는지, 최종 화면이 나오는지 확인.

---

## Self-Review 메모 (계획 작성자 확인용)

- **스펙 커버리지**: 설계 문서의 5개 섹션(전체 흐름/4경기 구성/기술구조/후보부족 처리/에러
  폴백) 전부 Task로 매핑됨 — 흐름(Task 11-13), 4경기(Task 2-9), 기술구조(Task 6,7,9,10),
  지역확장(Task 9 Step1-4), 3경기 폴백(Task 8의 `pick_story_match`가 검증된 언급이 2개 미만이면
  브랜드만 다른 후보로 남은 자리를 채움 — quote/url은 None, `build_bracket`이 그 경우 "이
  와인만의 알려진 이야기는 아직 없어요"로 표시. 설계 문서 원안대로 4경기를 항상 채우는 쪽으로
  확정, 사용자 확인 완료 — 2026-08-06).
- **placeholder 스캔**: "TBD"/"나중에" 패턴 없음, 모든 스텝에 실제 코드 포함.
- **타입 일관성**: `BracketCard`(스키마)와 `BracketCard`(프론트 interface)가 필드명 동일
  (`item_cd`/`axis_label` snake_case로 통일, 프론트도 API 응답 그대로 받아 씀 — camelCase
  변환 안 함, 기존 `WineCard`도 그렇게 하고 있어서 일관성 유지).
