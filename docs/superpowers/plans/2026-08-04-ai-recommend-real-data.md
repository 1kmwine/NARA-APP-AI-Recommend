# AI 와인 추천 실데이터 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mock 데이터로 동작하는 `frontend/app/page.tsx`(SIP. 조이스틱 카드)를 실제 나라셀라 와인 DB(`wine_info`)·POS 가격·NAS1 이미지에 연결하는 FastAPI 백엔드를 만들고 프론트를 그 API에 붙인다.

**Architecture:** `backend/`에 FastAPI 신설. `ai_recommend_app` 계정 하나로 `ai_recommend`(우리 스키마, 가격 캐시) + `wine_info`(읽기전용) 크로스스키마 쿼리. 가격은 별도 ETL(`ai_recommend_pos_ro`)로 POS에서 가져와 우리 스키마에 캐시. 지역/국가 순서는 앱 기동 시 집계해 메모리 캐시. 페어링은 사전 스크래핑 DB 없이 자유텍스트 → LLM 추론(taste 벡터) → DB의 taste 벡터와 거리 매칭.

**Tech Stack:** FastAPI, SQLAlchemy(raw SQL 위주, ORM은 캐시 테이블 하나만), PyMySQL, pytest, httpx, Anthropic SDK(페어링 추론), Next.js(기존 프론트).

**참고 문서:** [설계 스펙](../specs/2026-08-04-ai-recommend-real-data-design.md), 자격증명은 `docs/CREDENTIALS.local.md`(커밋 안 됨, 로컬에서 직접 읽을 것).

---

## 사전 준비 (Task 1에서 검증)

이 플랜은 `ai_recommend_app`/`ai_recommend_pos_ro` 계정이 서버에 이미 생성돼 있고
`docs/CREDENTIALS.local.md`에 값이 있다는 전제로 시작한다(사용자 확인됨). `ai_recommend`
스키마 자체와 `wine_price_cache` 테이블은 아직 없을 수 있어 Task 1에서 직접 생성한다.

---

### Task 1: 백엔드 스캐폴드 + DB 접속 검증

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_main.py`
- Test: `backend/tests/__init__.py`

- [ ] **Step 1: 디렉터리/의존성 파일 작성**

`backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic-settings==2.6.0
sqlalchemy==2.0.36
pymysql==1.1.1
httpx==0.27.2
anthropic==0.39.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

`backend/.env.example`:
```
AI_RECOMMEND_DB_HOST=192.168.47.105
AI_RECOMMEND_DB_PORT=3306
AI_RECOMMEND_DB_USER=ai_recommend_app
AI_RECOMMEND_DB_PASSWORD=
AI_RECOMMEND_DB_NAME=ai_recommend
WINE_INFO_DB_NAME=wine_info

POS_DB_HOST=192.168.47.105
POS_DB_PORT=3306
POS_DB_USER=ai_recommend_pos_ro
POS_DB_PASSWORD=
POS_DB_NAME=pos

NAS1_BASE_URL=http://el.naracellar.com/share.cgi
NAS1_SHARE_SSID=

ANTHROPIC_API_KEY=
```

- [ ] **Step 2: 실제 값으로 `backend/.env` 만들기 (커밋 안 됨, 루트 .gitignore의 `.env` 패턴이 커버)**

`docs/CREDENTIALS.local.md`를 읽고 `backend/.env`에 `AI_RECOMMEND_DB_PASSWORD`, `POS_DB_PASSWORD`,
`NAS1_SHARE_SSID` 값을 채워 넣는다. `ANTHROPIC_API_KEY`는 사용자에게 확인.

- [ ] **Step 3: DB 접속 검증 (mysql 클라이언트, 코드 아님 — 인프라 확인용)**

Run:
```bash
mysql -h 192.168.47.105 -P 3306 -u ai_recommend_app -p'<PASSWORD>' -e "SELECT COUNT(*) FROM wine_info.integrated_item_info; SHOW DATABASES LIKE 'ai_recommend';"
```
Expected: `integrated_item_info` count ≈ 9214, `ai_recommend` 스키마가 안 보이면 아래로 만든다.

```bash
mysql -h 192.168.47.105 -P 3306 -u ai_recommend_app -p'<PASSWORD>' -e "CREATE DATABASE IF NOT EXISTS ai_recommend CHARACTER SET utf8mb4;"
```
권한 부족으로 실패하면 DBA(서버 관리자)에게 `ai_recommend` 스키마 생성을 요청하고 재시도.

- [ ] **Step 4: `app/config.py` 작성**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ai_recommend_db_host: str = "192.168.47.105"
    ai_recommend_db_port: int = 3306
    ai_recommend_db_user: str = "ai_recommend_app"
    ai_recommend_db_password: str
    ai_recommend_db_name: str = "ai_recommend"
    wine_info_db_name: str = "wine_info"

    pos_db_host: str = "192.168.47.105"
    pos_db_port: int = 3306
    pos_db_user: str = "ai_recommend_pos_ro"
    pos_db_password: str
    pos_db_name: str = "pos"

    nas1_base_url: str = "http://el.naracellar.com/share.cgi"
    nas1_share_ssid: str

    anthropic_api_key: str = ""


settings = Settings()
```

- [ ] **Step 5: `app/main.py` 작성 (health check만)**

```python
from fastapi import FastAPI

app = FastAPI(title="AI Wine Recommend API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: 실패하는 테스트 작성**

`backend/tests/__init__.py`: 빈 파일.

`backend/tests/test_main.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 7: 의존성 설치 후 테스트 실행**

Run:
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
AI_RECOMMEND_DB_PASSWORD=x POS_DB_PASSWORD=x NAS1_SHARE_SSID=x pytest tests/test_main.py -v
```
Expected: PASS (config.py는 `.env` 없어도 환경변수로 동작 — CI/테스트에서 더미값 주입)

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app/__init__.py backend/app/config.py backend/app/main.py backend/tests/
git commit -m "feat: FastAPI 백엔드 스캐폴드 + health check"
```

---

### Task 2: DB 엔진

**Files:**
- Create: `backend/app/db.py`
- Test: `backend/tests/test_db.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.db import build_db_url


def test_build_db_url_uses_pymysql_driver():
    url = build_db_url(
        host="192.168.47.105", port=3306, user="ai_recommend_app",
        password="p@ss", database="ai_recommend",
    )
    assert url == "mysql+pymysql://ai_recommend_app:p%40ss@192.168.47.105:3306/ai_recommend?charset=utf8mb4"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'` 혹은 `ImportError`

- [ ] **Step 3: `app/db.py` 구현**

```python
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def build_db_url(host: str, port: int, user: str, password: str, database: str) -> str:
    return (
        f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        "?charset=utf8mb4"
    )


# ai_recommend_app 계정은 ai_recommend(전체권한) + wine_info.integrated_item_info/wine_notes
# (SELECT)에 권한이 있어, 이 엔진 하나로 두 스키마를 크로스스키마 쿼리한다
# (쿼리에서 `wine_info.integrated_item_info` 처럼 스키마를 명시).
engine = create_engine(
    build_db_url(
        settings.ai_recommend_db_host,
        settings.ai_recommend_db_port,
        settings.ai_recommend_db_user,
        settings.ai_recommend_db_password,
        settings.ai_recommend_db_name,
    ),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


pos_engine = create_engine(
    build_db_url(
        settings.pos_db_host,
        settings.pos_db_port,
        settings.pos_db_user,
        settings.pos_db_password,
        settings.pos_db_name,
    ),
    pool_pre_ping=True,
)
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `AI_RECOMMEND_DB_PASSWORD=x POS_DB_PASSWORD=x NAS1_SHARE_SSID=x pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db.py backend/tests/test_db.py
git commit -m "feat: SQLAlchemy 엔진(ai_recommend + pos 크로스스키마)"
```

---

### Task 3: 가격 티어 모듈

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/price_tiers.py`
- Test: `backend/tests/test_price_tiers.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.services.price_tiers import PRICE_TIERS, tier_bounds, widen_tier_ranges


def test_ten_tiers_defined():
    assert len(PRICE_TIERS) == 10


def test_tier_bounds_first_tier():
    assert tier_bounds(0) == (0, 10_000)


def test_tier_bounds_last_tier_has_no_upper_bound():
    assert tier_bounds(9) == (10_000_001, None)


def test_tier_bounds_middle_tier():
    assert tier_bounds(6) == (100_001, 300_000)


def test_widen_tier_ranges_starts_with_exact_tier():
    ranges = widen_tier_ranges(5)
    assert ranges[0] == (70_001, 100_000)


def test_widen_tier_ranges_expands_both_directions_and_clamps():
    ranges = widen_tier_ranges(0)
    # tier 0은 아래로 넓힐 수 없으니 위로만 넓어지고, 끝엔 전체 범위(0, None)에 도달
    assert ranges[-1] == (0, None)


def test_widen_tier_ranges_covers_all_ten_tiers_eventually():
    ranges = widen_tier_ranges(9)
    assert ranges[-1] == (0, None)
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_price_tiers.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `app/services/price_tiers.py` 구현**

```python
PRICE_TIERS: list[tuple[str, int, int | None]] = [
    ("1만원 이하", 0, 10_000),
    ("2만원대", 10_001, 20_000),
    ("3만원대", 20_001, 30_000),
    ("5만원대", 30_001, 50_000),
    ("7만원대", 50_001, 70_000),
    ("10만원대", 70_001, 100_000),
    ("30만원대", 100_001, 300_000),
    ("100만원대", 300_001, 1_000_000),
    ("1000만원대", 1_000_001, 10_000_000),
    ("1000만원 이상", 10_000_001, None),
]


def tier_bounds(tier_index: int) -> tuple[int, int | None]:
    _, low, high = PRICE_TIERS[tier_index]
    return (low, high)


def tier_label(tier_index: int) -> str:
    label, _, _ = PRICE_TIERS[tier_index]
    return label


def widen_tier_ranges(tier_index: int) -> list[tuple[int, int | None]]:
    """정확한 티어부터 시작해서 점점 폭을 넓혀가며 (min, max) 범위를 반환한다.
    10단계라 정확한 티어에 SKU가 없는 경우가 흔해서, 호출 측이 순서대로 검색하다가
    결과가 나오면 멈추는 폴백에 쓴다."""
    n = len(PRICE_TIERS)
    ranges: list[tuple[int, int | None]] = [tier_bounds(tier_index)]
    widen = 1
    while True:
        lo_idx = max(0, tier_index - widen)
        hi_idx = min(n - 1, tier_index + widen)
        lo, _ = tier_bounds(lo_idx)
        _, hi = tier_bounds(hi_idx)
        candidate = (lo, hi)
        if candidate != ranges[-1]:
            ranges.append(candidate)
        if lo_idx == 0 and hi_idx == n - 1:
            break
        widen += 1
    return ranges
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_price_tiers.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/price_tiers.py backend/tests/test_price_tiers.py
git commit -m "feat: 가격 10단계 + 폴백 확장 범위 계산"
```

---

### Task 4: 지역/국가 보정 데이터 포팅

NARA-DATA-Wine-Info의 `quicklook/wine-info/helpers.php`를 Python으로 이식(실데이터 그대로,
2026-07-13 기준). 국가/지역 정규화 근거는 [설계 스펙](../specs/2026-08-04-ai-recommend-real-data-design.md) 참고.

**Files:**
- Create: `backend/app/services/region_overrides.py`
- Test: `backend/tests/test_region_overrides.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.services.region_overrides import (
    canonical_country_from_votes,
    extract_raw_region,
    normalize_region_label,
    region_to_country,
)


def test_region_to_country_known_region():
    assert region_to_country("부르고뉴") == "France"


def test_region_to_country_unknown_region_returns_none():
    assert region_to_country("존재안함지역") is None


def test_normalize_region_label_applies_alias():
    assert normalize_region_label("나파밸리") == "캘리포니아"


def test_normalize_region_label_applies_expand_after_alias():
    # 라펠 밸리는 REGION_ALIAS엔 없지만 REGION_EXPAND로 센트럴 밸리로 병합됨
    assert normalize_region_label("라펠 밸리") == "센트럴 밸리"


def test_normalize_region_label_passthrough_when_no_mapping():
    assert normalize_region_label("피에몬테") == "피에몬테"


def test_extract_raw_region_from_place_json():
    assert extract_raw_region('{"ko": "보르도", "en": "Bordeaux"}') == "보르도"


def test_extract_raw_region_handles_missing_or_invalid_json():
    assert extract_raw_region(None) == ""
    assert extract_raw_region("") == ""
    assert extract_raw_region("not json") == ""


def test_canonical_country_from_votes_majority_wins():
    result = canonical_country_from_votes(["France", "France", "Germany"], "Korea")
    assert result == "France"


def test_canonical_country_from_votes_falls_back_when_no_votes():
    result = canonical_country_from_votes([None, None], "Italy")
    assert result == "Italy"


def test_canonical_country_from_votes_falls_back_to_기타_when_nothing():
    result = canonical_country_from_votes([None], None)
    assert result == "기타"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_region_overrides.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `app/services/region_overrides.py` 구현**

```python
import json
from collections import Counter

# NARA-DATA-Wine-Info의 quicklook/wine-info/helpers.php REGION_COUNTRY_OVERRIDE를
# 그대로 이식(2026-07-13 기준 실데이터). place.ko(지역명, 자유텍스트)로 국가를
# 역산하기 위한 표 — integrated_item_info.countryName은 ERP 매핑 누락으로 상당수가
# "Korea"로 잘못 들어있어 신뢰할 수 없다.
REGION_COUNTRY_OVERRIDE: dict[str, str] = {
    "가스꼬뉴": "France", "가스코뉴": "France", "갈라시아": "Spain", "까딸루냐": "Spain",
    "까리레나": "Spain", "까스띨랴 이 레온": "Spain", "까오르": "France", "까탈루냐": "Spain",
    "꼬뜨 뒤 론": "France", "꼬뜨 드 가스꼬뉴": "France", "꼬뜨 드 본": "France",
    "끼안티": "Italy", "나바라": "Spain", "나이아가라 페닌슐라": "Canada", "나파밸리": "USA",
    "나헤": "Germany", "남 프랑스": "France", "네메아": "Greece", "노스 아일랜드": "New Zealand",
    "뉘른베르크": "Germany", "뉴 사우스 웨일즈": "Australia", "니더외스터라이히": "Austria",
    "니바라": "Spain", "도우로": "Portugal", "도우루": "Portugal", "라 만차": "Spain",
    "라인가우": "Germany", "라인하센": "Germany", "라치오": "Italy", "라펠": "Chile",
    "라펠 밸리": "Chile", "라펠밸리": "Chile", "랑그독": "France", "랑그독 루시옹": "France",
    "랑그독 루씨용": "France", "론": "France", "론 밸리": "France", "롬바르디아": "Italy",
    "루시용": "France", "루씨옹": "France", "루씨용": "France", "루아르": "France",
    "루아르 밸리": "France", "루에다": "Spain", "리베라 델 두에로": "Spain", "리스본": "Portugal",
    "리아스 바이사스": "Spain", "리오하": "Spain", "마가렛 리버": "Australia", "마데이라": "Portugal",
    "마드라드": "Spain", "마드리드": "Spain", "마르께": "Italy", "마르케": "Italy",
    "마울레 밸리": "Chile", "마이포 밸리": "Chile", "마틴로보": "New Zealand", "마틴보로": "New Zealand",
    "말보로": "New Zealand", "말보르": "New Zealand", "맥라렌 베일": "Australia", "멘도사": "Argentina",
    "멘도자": "Argentina", "모젤": "Germany", "모젤-자르-루버": "Germany", "몬탈치노": "Italy",
    "몰도바": "Moldova", "무르시아": "Spain", "미뉴": "Portugal", "바로사 밸리": "Australia",
    "바실리카타": "Italy", "바이에른": "Germany", "발데오라스": "Spain", "발렌시아": "Spain",
    "베네토": "Italy", "베어 리버": "USA", "베카 밸리": "Lebanon", "보드로": "France",
    "보르도": "France", "보졸레": "France", "부르게란트": "Austria", "부르겐란트": "Austria",
    "부르고뉴": "France", "비뉴 베르데": "Portugal", "비에조": "Spain", "비파바 밸리": "Slovenia",
    "빅토리아": "Australia", "뿔리아": "Italy", "사르데냐": "Italy", "사우스 아일랜드": "New Zealand",
    "사우스 오스트레일리아": "Australia", "사우스 웨스트 프랑스": "France",
    "사우스 이스턴 오스트레일리아": "Australia", "사우스웨스트 프랑스": "France",
    "산 후안": "Argentina", "살렌토": "Italy", "살타": "Argentina", "상파뉴": "France",
    "샴페인": "France", "샹파뉴": "France", "서던 프랑스": "France", "센터럴 밸리": "Chile",
    "센트럴 밸리": "Chile", "슈타이어마르크": "Austria", "스테판 보다": "Moldova",
    "스텔렌보쉬": "South Africa", "시칠리아": "Italy", "아라곤": "Spain", "아르곤": "Spain",
    "아부르쪼": "Italy", "아브루쪼": "Italy", "아콩카구아": "Chile", "알리칸테": "Spain",
    "알베르뉴": "France", "알자스": "France", "알토 아디제": "Italy", "애들레이드 힐즈": "Australia",
    "에밀리아 로마냐": "Italy", "예클라": "Spain", "오레곤": "USA", "오리건": "USA",
    "오리건주": "USA", "온타리오": "Canada", "움브리아": "Italy", "워싱턴": "USA",
    "워싱턴주": "USA", "웨스턴  오스트레일리아": "Australia", "웨스턴 오스트레일리아": "Australia",
    "웨스턴 케이프": "South Africa", "쥐라": "France", "지공다스": "France",
    "카사블랑카 밸리": "Chile", "카스티야": "Spain", "카스티야 이 레이온": "Spain",
    "카탈루냐": "Spain", "칼라타유드": "Spain", "캄파니아": "Italy", "캄프탈": "Austria",
    "캘리포니아": "USA", "캘리포니이": "USA", "켄터키": "USA", "코드루": "Moldova",
    "코르시": "France", "코르시카": "France", "코스탈 리전": "South Africa",
    "코스탈 리젼": "South Africa", "콜롬비아 밸리": "USA", "콜차구아 밸리": "Chile",
    "콜차구아밸리": "Chile", "쿠리코 밸리": "Chile", "타즈마니아": "Australia", "토로": "Spain",
    "토스카나": "Italy", "토카이": "Hungary", "트렌티노": "Italy", "팔츠": "Germany",
    "페네데스": "Spain", "페이독": "France", "펠로폰네소스": "Greece", "포르토": "Portugal",
    "포트": "Portugal", "풀리아": "Italy", "프로방스": "France", "프리모르예": "Slovenia",
    "프리오랏": "Spain", "프리울리 베네찌아 줄리아": "Italy", "플라 데 바제스": "Spain",
    "피에": "Italy", "피에몬테": "Italy", "헤레즈-헤레스-셰리": "Spain",
    "헤레즈헤레스셰리": "Spain",
}

# 표기 통일(오탈자/띄어쓰기) + 의도적 병합(나파밸리→캘리포니아 지역 그룹으로 표시).
REGION_ALIAS: dict[str, str] = {
    "가스꼬뉴": "가스코뉴", "까딸루냐": "카탈루냐", "까스띨랴 이 레온": "카스티야 이 레이온",
    "까탈루냐": "카탈루냐", "나파밸리": "캘리포니아", "니바라": "나바라", "도우로": "도우루",
    "라펠밸리": "라펠 밸리", "랑그독 루씨용": "랑그독 루시옹", "루씨옹": "루시용",
    "루씨용": "루시용", "마드라드": "마드리드", "마르께": "마르케", "마틴로보": "마틴보로",
    "말보르": "말보로", "뿔리아": "풀리아", "사우스웨스트 프랑스": "사우스 웨스트 프랑스",
    "상파뉴": "샴페인", "샹파뉴": "샴페인", "센터럴 밸리": "센트럴 밸리",
    "소노마 카운티": "소노마", "소노마 코스트": "소노마", "소노마 코스트ㅜ": "소노마",
    "소노마카운티": "소노마", "아르곤": "아라곤", "아부르쪼": "아브루쪼", "오레곤": "오리건",
    "오리건주": "오리건", "워싱턴주": "워싱턴", "웨스턴  오스트레일리아": "웨스턴 오스트레일리아",
    "캘리포니이": "캘리포니아", "코르시": "코르시카", "코스탈 리전": "코스탈 리젼",
    "콜차구아밸리": "콜차구아 밸리", "피에": "피에몬테", "헤레즈헤레스셰리": "헤레즈-헤레스-셰리",
}

# 칠레 AVA를 상위 지역으로 병합.
REGION_EXPAND: dict[str, str] = {
    "라펠 밸리": "센트럴 밸리", "라펠밸리": "센트럴 밸리", "콜차구아 밸리": "센트럴 밸리",
    "콜차구아밸리": "센트럴 밸리", "아콩카구아 밸리": "센트럴 밸리", "아콩카구아": "센트럴 밸리",
    "마이포 밸리": "센트럴 밸리", "카사블랑카 밸리": "센트럴 밸리", "쿠리코 밸리": "센트럴 밸리",
    "마울레 밸리": "센트럴 밸리",
}


def extract_raw_region(place_json: str | None) -> str:
    if not place_json:
        return ""
    try:
        data = json.loads(place_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("ko") or "").strip()


def region_to_country(raw_region: str) -> str | None:
    return REGION_COUNTRY_OVERRIDE.get(raw_region)


def normalize_region_label(raw_region: str) -> str:
    label = REGION_ALIAS.get(raw_region, raw_region)
    return REGION_EXPAND.get(label, REGION_EXPAND.get(raw_region, label))


def canonical_country_from_votes(
    row_countries: list[str | None], fallback_raw_country: str | None
) -> str:
    votes = Counter(c for c in row_countries if c is not None)
    if votes:
        return votes.most_common(1)[0][0]
    return fallback_raw_country if fallback_raw_country else "기타"
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_region_overrides.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/region_overrides.py backend/tests/test_region_overrides.py
git commit -m "feat: 지역/국가 보정 로직 포팅 (NARA-DATA-Wine-Info helpers.php 기반)"
```

---

### Task 5: 지역/국가 순회 캐시

**Files:**
- Create: `backend/app/services/region_cache.py`
- Test: `backend/tests/test_region_cache.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.services.region_cache import CountryRegions, build_region_order


def test_build_region_order_counts_and_sorts_by_sku_count_desc():
    # (place_json, country_name) 튜플 8행: 프랑스 5건(부르고뉴3, 보르도2), 미국 2건, 칠레 1건
    rows = [
        ('{"ko": "부르고뉴"}', "France"),
        ('{"ko": "부르고뉴"}', "France"),
        ('{"ko": "부르고뉴"}', "France"),
        ('{"ko": "보르도"}', "France"),
        ('{"ko": "보르도"}', "France"),
        ('{"ko": "나파밸리"}', "USA"),
        ('{"ko": "나파밸리"}', "USA"),
        ('{"ko": "라펠 밸리"}', "Chile"),
    ]
    order = build_region_order(rows)

    assert [c.country for c in order] == ["France", "USA", "Chile"]
    france = order[0]
    assert [r.label for r in france.regions] == ["부르고뉴", "보르도"]
    assert france.regions[0].sku_count == 3
    assert france.regions[1].sku_count == 2


def test_build_region_order_uses_row_country_when_region_unmapped():
    rows = [('{"ko": "존재안함지역"}', "Georgia")]
    order = build_region_order(rows)
    assert order[0].country == "Georgia"


def test_build_region_order_falls_back_to_기타_when_nothing_known():
    rows = [(None, None)]
    order = build_region_order(rows)
    assert order[0].country == "기타"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_region_cache.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `app/services/region_cache.py` 구현**

```python
import time
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.region_overrides import (
    extract_raw_region,
    normalize_region_label,
    region_to_country,
)

TTL_SECONDS = 3600


@dataclass
class RegionCount:
    label: str
    sku_count: int


@dataclass
class CountryRegions:
    country: str
    sku_count: int
    regions: list[RegionCount] = field(default_factory=list)


def build_region_order(rows: list[tuple[str | None, str | None]]) -> list[CountryRegions]:
    """(place_json, country_name) 행 리스트로부터 국가별/지역별 SKU 개수 집계 후
    국가는 총 SKU 개수 내림차순, 국가 내 지역도 SKU 개수 내림차순으로 정렬."""
    counts: Counter[tuple[str, str]] = Counter()
    for place_json, country_name in rows:
        raw_region = extract_raw_region(place_json)
        label = normalize_region_label(raw_region) if raw_region else "기타"
        country = region_to_country(raw_region) or country_name or "기타"
        counts[(country, label)] += 1

    country_totals: Counter[str] = Counter()
    by_country: dict[str, Counter[str]] = {}
    for (country, label), n in counts.items():
        country_totals[country] += n
        by_country.setdefault(country, Counter())[label] += n

    result: list[CountryRegions] = []
    for country, total in country_totals.most_common():
        regions = [
            RegionCount(label=label, sku_count=n)
            for label, n in by_country[country].most_common()
        ]
        result.append(CountryRegions(country=country, sku_count=total, regions=regions))
    return result


class RegionCache:
    def __init__(self) -> None:
        self._order: list[CountryRegions] = []
        self._fetched_at: float = 0.0

    def get(self, session: Session) -> list[CountryRegions]:
        now = time.time()
        if not self._order or now - self._fetched_at > TTL_SECONDS:
            rows = session.execute(
                text("SELECT place, countryName FROM wine_info.integrated_item_info")
            ).all()
            self._order = build_region_order([(r[0], r[1]) for r in rows])
            self._fetched_at = now
        return self._order


region_cache = RegionCache()
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_region_cache.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/region_cache.py backend/tests/test_region_cache.py
git commit -m "feat: 지역/국가 순회 순서 집계(SKU개수 내림차순) + TTL 캐시"
```

---

### Task 6: 가격 캐시 테이블 + POS ETL

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/etl/__init__.py`
- Create: `backend/etl/sync_price.py`
- Test: `backend/tests/test_sync_price.py`

- [ ] **Step 1: POS 실제 컬럼명 확인 (인프라 검증, 코드 아님)**

`tb_product`/`v_daily_sale`는 원래 3개 그랜트 테이블(`erp_item_info`/`pos_item`/`tb_pdata`) 밖이라
컬럼 스키마를 조사 단계에서 못 봤다. 아래로 실제 컬럼명을 확인하고, `price__original` /
`sale__amt` / `sales_qty`와 다르면 Step 3의 SQL을 맞게 고친다.

Run:
```bash
mysql -h 192.168.47.105 -P 3306 -u ai_recommend_pos_ro -p'<PASSWORD>' pos -e "DESCRIBE tb_product; DESCRIBE v_daily_sale;"
```

- [ ] **Step 2: 실패하는 테스트 작성 (순수 가격 계산 로직만)**

```python
from etl.sync_price import compute_price


def test_compute_price_prefers_tb_product_original_price():
    result = compute_price(
        tb_product_row={"price__original": 45000},
        daily_sales=[{"sale__amt": 40000, "sales_qty": 1}],
    )
    assert result == (45000, "tb_product")


def test_compute_price_falls_back_to_daily_sale_average():
    result = compute_price(
        tb_product_row=None,
        daily_sales=[
            {"sale__amt": 90000, "sales_qty": 2},
            {"sale__amt": 30000, "sales_qty": 1},
        ],
    )
    # (90000 + 30000) / (2 + 1) = 40000
    assert result == (40000, "v_daily_sale_calc")


def test_compute_price_ignores_zero_or_null_tb_product_price():
    result = compute_price(
        tb_product_row={"price__original": 0},
        daily_sales=[{"sale__amt": 20000, "sales_qty": 1}],
    )
    assert result == (20000, "v_daily_sale_calc")


def test_compute_price_returns_none_when_no_data():
    assert compute_price(tb_product_row=None, daily_sales=[]) is None


def test_compute_price_returns_none_when_daily_sale_qty_is_zero():
    result = compute_price(
        tb_product_row=None,
        daily_sales=[{"sale__amt": 10000, "sales_qty": 0}],
    )
    assert result is None
```

- [ ] **Step 3: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_sync_price.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: `app/models.py` 작성 (가격 캐시 테이블)**

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WinePriceCache(Base):
    __tablename__ = "wine_price_cache"

    item_cd: Mapped[str] = mapped_column(String(45), primary_key=True)
    price_krw: Mapped[int] = mapped_column(Integer)
    price_source: Mapped[str] = mapped_column(String(20))  # 'tb_product' | 'v_daily_sale_calc'
    synced_at: Mapped[datetime] = mapped_column(DateTime)
```

- [ ] **Step 5: `etl/sync_price.py` 작성 (순수 함수 + I/O 함수)**

```python
"""POS(tb_product/v_daily_sale) -> ai_recommend.wine_price_cache 가격 동기화.
수동 실행 또는 cron: `python -m etl.sync_price` (backend/ 에서).
"""
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal, pos_engine
from app.models import Base, WinePriceCache


def compute_price(
    tb_product_row: dict | None, daily_sales: list[dict]
) -> tuple[int, str] | None:
    """tb_product.price__original 우선, 없거나 0/null이면 v_daily_sale 평균단가.
    둘 다 없으면 None (해당 SKU는 가격 캐시에서 건너뜀)."""
    if tb_product_row and tb_product_row.get("price__original"):
        return (int(tb_product_row["price__original"]), "tb_product")

    total_amt = sum(row["sale__amt"] for row in daily_sales)
    total_qty = sum(row["sales_qty"] for row in daily_sales)
    if total_qty > 0:
        return (round(total_amt / total_qty), "v_daily_sale_calc")

    return None


def run_sync() -> int:
    """POS에서 전체 item_cd에 대해 가격을 계산해 wine_price_cache를 upsert한다.
    반환값: 갱신된 행 수."""
    Base.metadata.create_all(bind=pos_engine.connect().engine, tables=[])  # no-op, 스키마는 ai_recommend 쪽에

    with pos_engine.connect() as pos_conn:
        product_rows = pos_conn.execute(
            text("SELECT item_cd, price__original FROM tb_product")
        ).mappings().all()
        sale_rows = pos_conn.execute(
            text("SELECT item_cd, sale__amt, sales_qty FROM v_daily_sale")
        ).mappings().all()

    products_by_item: dict[str, dict] = {r["item_cd"]: dict(r) for r in product_rows}
    sales_by_item: dict[str, list[dict]] = {}
    for r in sale_rows:
        sales_by_item.setdefault(r["item_cd"], []).append(dict(r))

    all_item_cds = set(products_by_item) | set(sales_by_item)

    updated = 0
    session: Session = SessionLocal()
    try:
        for item_cd in all_item_cds:
            priced = compute_price(products_by_item.get(item_cd), sales_by_item.get(item_cd, []))
            if priced is None:
                continue
            price_krw, source = priced
            session.merge(
                WinePriceCache(
                    item_cd=item_cd,
                    price_krw=price_krw,
                    price_source=source,
                    synced_at=datetime.utcnow(),
                )
            )
            updated += 1
        session.commit()
    finally:
        session.close()

    return updated


if __name__ == "__main__":
    n = run_sync()
    print(f"[sync_price] {n}건 갱신")
```

- [ ] **Step 6: `ai_recommend.wine_price_cache` 테이블 실제 생성**

Run:
```bash
cd backend && source .venv/bin/activate
python -c "from app.db import engine; from app.models import Base; Base.metadata.create_all(engine)"
```
Expected: 에러 없이 종료. 확인: `mysql ... -e "DESCRIBE ai_recommend.wine_price_cache;"`

- [ ] **Step 7: 테스트 실행 (통과 확인 — 순수 함수만, DB 필요없음)**

Run: `pytest tests/test_sync_price.py -v`
Expected: PASS (5 passed)

- [ ] **Step 8: Commit**

```bash
git add backend/app/models.py backend/etl/__init__.py backend/etl/sync_price.py backend/tests/test_sync_price.py
git commit -m "feat: 가격 캐시 테이블 + POS ETL(tb_product 우선, v_daily_sale 폴백)"
```

---

### Task 7: 추천 후보 검색

**Files:**
- Create: `backend/app/services/recommend.py`
- Test: `backend/tests/test_recommend.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.services.price_tiers import widen_tier_ranges
from app.services.recommend import find_with_fallback, pick_top_candidates


def test_pick_top_candidates_sorts_by_wishes_desc():
    candidates = [
        {"itemCd": "A", "wishes": 3, "reviews": 1},
        {"itemCd": "B", "wishes": 10, "reviews": 0},
        {"itemCd": "C", "wishes": None, "reviews": 5},
    ]
    top = pick_top_candidates(candidates, limit=2)
    assert [c["itemCd"] for c in top] == ["B", "A"]


def test_pick_top_candidates_treats_missing_wishes_as_zero():
    candidates = [{"itemCd": "A", "wishes": None, "reviews": None}]
    top = pick_top_candidates(candidates, limit=1)
    assert top[0]["itemCd"] == "A"


def test_find_with_fallback_returns_first_non_empty_search():
    calls = []

    def search(price_min, price_max):
        calls.append((price_min, price_max))
        if price_max == 100_000:
            return [{"itemCd": "X"}]
        return []

    result = find_with_fallback(tier_index=5, search=search)
    assert result == [{"itemCd": "X"}]
    assert calls[0] == widen_tier_ranges(5)[0]


def test_find_with_fallback_returns_empty_when_all_ranges_exhausted():
    result = find_with_fallback(tier_index=0, search=lambda lo, hi: [])
    assert result == []
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_recommend.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `app/services/recommend.py` 구현**

```python
from typing import Callable

from app.services.price_tiers import widen_tier_ranges

SearchFn = Callable[[int, int | None], list[dict]]


def pick_top_candidates(candidates: list[dict], limit: int) -> list[dict]:
    def score(c: dict) -> int:
        return (c.get("wishes") or 0) + (c.get("reviews") or 0)

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
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_recommend.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/recommend.py backend/tests/test_recommend.py
git commit -m "feat: 추천 후보 폴백 검색 + wishes/reviews 랭킹"
```

---

### Task 8: 페어링 자유텍스트 매칭

**Files:**
- Create: `backend/app/services/pairing.py`
- Test: `backend/tests/test_pairing.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
import json
from unittest.mock import MagicMock, patch

from app.services.pairing import (
    TasteVector,
    infer_taste_target,
    score_by_pairing,
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


@patch("app.services.pairing._call_anthropic")
def test_infer_taste_target_parses_llm_json_response(mock_call):
    mock_call.return_value = json.dumps(
        {"sweetness": 2, "acidity": 4, "body": 3, "tannin": 1}
    )
    result = infer_taste_target("훈제 연어")
    assert result == TasteVector(sweetness=2, acidity=4, body=3, tannin=1)


@patch("app.services.pairing._call_anthropic")
def test_infer_taste_target_falls_back_to_neutral_on_bad_response(mock_call):
    mock_call.return_value = "이건 JSON이 아님"
    result = infer_taste_target("아무 음식")
    assert result == TasteVector(sweetness=2, acidity=2, body=2, tannin=2)
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_pairing.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `app/services/pairing.py` 구현**

```python
import json
import math
from dataclasses import dataclass

from anthropic import Anthropic

from app.config import settings

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
        model="claude-sonnet-4-5",
        max_tokens=100,
        system=PAIRING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": food_text}],
    )
    return message.content[0].text


def infer_taste_target(food_text: str) -> TasteVector:
    raw = _call_anthropic(food_text)
    try:
        data = json.loads(raw)
        return TasteVector(
            sweetness=int(data["sweetness"]),
            acidity=int(data["acidity"]),
            body=int(data["body"]),
            tannin=int(data["tannin"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return NEUTRAL_TASTE
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_pairing.py -v`
Expected: PASS (6 passed) — LLM 호출은 `_call_anthropic`을 mock해서 실제 API 안 부름

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pairing.py backend/tests/test_pairing.py
git commit -m "feat: 자유텍스트 페어링 매칭(LLM 맛벡터 추론 + 거리 랭킹)"
```

---

### Task 9: NAS1 이미지 프록시

**Files:**
- Create: `backend/app/services/images.py`
- Test: `backend/tests/test_images.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
import pytest

from app.services.images import InvalidPdataId, InvalidVariant, build_nas1_url, validate_pdata_id


def test_build_nas1_url_for_removebg_variant():
    url = build_nas1_url(
        pdata_id="00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        variant="removebg",
        base_url="http://el.naracellar.com/share.cgi",
        ssid="f654b5f10f3c4439bf8a19229f9bf8a7",
    )
    assert url.startswith("http://el.naracellar.com/share.cgi?")
    assert "ssid=f654b5f10f3c4439bf8a19229f9bf8a7" in url
    assert "path=%2Fremovebg" in url
    assert "filename=00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5" in url


def test_build_nas1_url_for_origin_variant_has_empty_path():
    url = build_nas1_url(
        pdata_id="00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        variant="origin",
        base_url="http://el.naracellar.com/share.cgi",
        ssid="abc",
    )
    assert "path=&" in url or url.endswith("path=")


def test_build_nas1_url_rejects_unknown_variant():
    with pytest.raises(InvalidVariant):
        build_nas1_url(
            pdata_id="00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
            variant="huge",
            base_url="http://x",
            ssid="x",
        )


def test_validate_pdata_id_accepts_correct_format():
    validate_pdata_id("00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5")  # 예외 없이 통과


def test_validate_pdata_id_rejects_bad_format():
    with pytest.raises(InvalidPdataId):
        validate_pdata_id("../../etc/passwd")
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_images.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `app/services/images.py` 구현 (NARA-DATA-Wine-Info의 `nas-image.php` 포팅)**

```python
import re
from urllib.parse import urlencode

PDATA_ID_PATTERN = re.compile(r"^[0-9]{8}_[0-9a-f-]{36}$")

# nas-image.php의 $ALLOWED_VARIANTS 그대로 포팅.
ALLOWED_VARIANTS: dict[str, str] = {
    "origin": "",
    "thumb": "/thumb",
    "square": "/square",
    "removebg": "/removebg",
    "opengraph": "/opengraph",
}


class InvalidPdataId(ValueError):
    pass


class InvalidVariant(ValueError):
    pass


def validate_pdata_id(pdata_id: str) -> None:
    if not PDATA_ID_PATTERN.match(pdata_id):
        raise InvalidPdataId(f"invalid pdataId: {pdata_id!r}")


def build_nas1_url(pdata_id: str, variant: str, base_url: str, ssid: str) -> str:
    validate_pdata_id(pdata_id)
    if variant not in ALLOWED_VARIANTS:
        raise InvalidVariant(f"invalid variant: {variant!r}")

    path = ALLOWED_VARIANTS[variant]
    query = urlencode(
        {
            "ssid": ssid,
            "openfolder": "forcedownload",
            "ep": "",
            "fid": ssid,
            "filename": pdata_id,
            "path": path,
        }
    )
    return f"{base_url}?{query}"
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_images.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/images.py backend/tests/test_images.py
git commit -m "feat: NAS1 이미지 프록시 URL 빌더(nas-image.php 포팅)"
```

---

### Task 10: `/api/recommend` 라우터

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/recommend.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_recommend_router.py`

- [ ] **Step 1: `app/schemas.py` 작성 (Pydantic 응답 모델)**

```python
from pydantic import BaseModel


class WineCard(BaseModel):
    item_cd: str
    wine_name: str
    region: str
    country: str
    grape: str
    type_label_kr: str
    price_krw: int
    price_desc: str
    note: str
    persona_line: str
    pdata_id: str | None
```

- [ ] **Step 2: 실패하는 테스트 작성**

```python
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_recommend_returns_card_when_candidate_found():
    fake_candidate = {
        "itemCd": "ABC123",
        "nameKo": "테스트 와인",
        "type": "Red",
        "producer": '{"ko": "테스트 와이너리", "en": "Test Winery"}',
        "variety": '{"ko": "피노누아", "en": "Pinot Noir"}',
        "country": '{"ko": "프랑스", "en": "France"}',
        "place": '{"ko": "부르고뉴", "en": "Burgundy"}',
        "taste_raw": '{"sweetness": 1, "acidity": 3, "body": 3, "tannin": 3}',
        "notes_taste_raw": None,
        "tastingNote": None,
        "desc1": None,
        "pdataId": "00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        "price_krw": 45000,
        "reviews": 2,
        "wishes": 5,
    }
    with patch("app.routers.recommend.query_candidates", return_value=[fake_candidate]):
        response = client.get(
            "/api/recommend",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["wine_name"] == "테스트 와인"
    assert body["region"] == "부르고뉴"
    assert body["price_krw"] == 45000


def test_recommend_returns_404_when_no_candidate_even_after_fallback():
    with patch("app.routers.recommend.query_candidates", return_value=[]):
        response = client.get(
            "/api/recommend",
            params={"price_tier": 3, "country_index": 0, "region_index": 0, "wine_type": "Red"},
        )
    assert response.status_code == 404
```

- [ ] **Step 3: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_recommend_router.py -v`
Expected: FAIL — `404 route not found` 또는 import 에러

- [ ] **Step 4: `app/routers/recommend.py` 구현**

```python
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import WineCard
from app.services.pairing import infer_taste_target, score_by_pairing
from app.services.price_tiers import tier_label
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


def _to_card(candidate: dict, price_tier: int) -> WineCard:
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
        price_desc=tier_label(price_tier),
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
        card = _to_card(top, price_tier)
        card.persona_line = f"{card.wine_name}, {pairing_text}이랑 같이면 {reason}"
        return card

    top = pick_top_candidates(candidates, limit=1)[0]
    return _to_card(top, price_tier)
```

- [ ] **Step 5: `app/main.py`에 라우터 연결**

```python
from fastapi import FastAPI

from app.routers.recommend import router as recommend_router

app = FastAPI(title="AI Wine Recommend API")
app.include_router(recommend_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: 테스트 실행 (통과 확인)**

Run: `pytest tests/test_recommend_router.py -v`
Expected: PASS (2 passed) — `region_cache.get`은 실제 DB를 부르므로 이 테스트가 통과하려면
`region_cache._order`를 테스트에서 미리 채워둬야 함. 아래로 `conftest.py` 추가:

`backend/tests/conftest.py`:
```python
import pytest

from app.services.region_cache import CountryRegions, RegionCount, region_cache


@pytest.fixture(autouse=True)
def _seed_region_cache():
    region_cache._order = [
        CountryRegions(country="France", sku_count=10, regions=[RegionCount(label="부르고뉴", sku_count=10)])
    ]
    region_cache._fetched_at = 10**12  # 아주 먼 미래 타임스탬프로 TTL 만료 방지
    yield
    region_cache._order = []
    region_cache._fetched_at = 0.0
```

Run: `AI_RECOMMEND_DB_PASSWORD=x POS_DB_PASSWORD=x NAS1_SHARE_SSID=x pytest tests/test_recommend_router.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/ backend/app/main.py backend/tests/test_recommend_router.py backend/tests/conftest.py
git commit -m "feat: GET /api/recommend 엔드포인트"
```

---

### Task 11: `/api/images/{pdata_id}` 라우터

**Files:**
- Create: `backend/app/routers/images.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_images_router.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_images_returns_400_for_invalid_pdata_id():
    response = client.get("/api/images/not-valid", params={"variant": "thumb"})
    assert response.status_code == 400


def test_images_returns_400_for_invalid_variant():
    response = client.get(
        "/api/images/00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
        params={"variant": "huge"},
    )
    assert response.status_code == 400


def test_images_streams_bytes_on_success():
    with patch("app.routers.images.fetch_image_bytes", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (b"\x89PNGfakebytes", "image/png")
        response = client.get(
            "/api/images/00004338_7562cd0b-aad4-4383-a980-c0c52ada67d5",
            params={"variant": "removebg"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNGfakebytes"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `pytest tests/test_images_router.py -v`
Expected: FAIL — 라우트 없음(404) 혹은 import 에러

- [ ] **Step 3: `app/services/images.py`에 fetch 함수 추가**

`backend/app/services/images.py` 끝에 추가:
```python
import httpx

from app.config import settings


async def fetch_image_bytes(pdata_id: str, variant: str) -> tuple[bytes, str]:
    url = build_nas1_url(pdata_id, variant, settings.nas1_base_url, settings.nas1_share_ssid)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "application/octet-stream")
    return response.content, content_type
```

- [ ] **Step 4: `app/routers/images.py` 구현**

```python
from fastapi import APIRouter, HTTPException, Response

from app.services.images import InvalidPdataId, InvalidVariant, fetch_image_bytes

router = APIRouter(prefix="/api")


@router.get("/images/{pdata_id}")
async def get_image(pdata_id: str, variant: str = "thumb") -> Response:
    try:
        content, content_type = await fetch_image_bytes(pdata_id, variant)
    except (InvalidPdataId, InvalidVariant) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="NAS 이미지 가져오기 실패")

    return Response(content=content, media_type=content_type)
```

- [ ] **Step 5: `app/main.py`에 라우터 연결**

```python
from fastapi import FastAPI

from app.routers.images import router as images_router
from app.routers.recommend import router as recommend_router

app = FastAPI(title="AI Wine Recommend API")
app.include_router(recommend_router)
app.include_router(images_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: 테스트 실행 (통과 확인)**

Run: `AI_RECOMMEND_DB_PASSWORD=x POS_DB_PASSWORD=x NAS1_SHARE_SSID=x pytest tests/test_images_router.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/images.py backend/app/routers/images.py backend/app/main.py backend/tests/test_images_router.py
git commit -m "feat: GET /api/images/{pdata_id} NAS1 프록시 엔드포인트"
```

---

### Task 12: 프론트 — Next.js rewrite + mock 제거, API 연동

**Files:**
- Modify: `frontend/next.config.js`
- Create: `frontend/app/api.ts`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: `next.config.js`에 백엔드 프록시 rewrite 추가**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
  },
};
module.exports = nextConfig;
```

- [ ] **Step 2: `frontend/app/api.ts` 작성 (타입 + fetch 함수)**

```typescript
export type WineType = "Red" | "White" | "Sparkling";

export interface WineCard {
  item_cd: string;
  wine_name: string;
  region: string;
  country: string;
  grape: string;
  type_label_kr: string;
  price_krw: number;
  price_desc: string;
  note: string;
  persona_line: string;
  pdata_id: string | null;
}

export interface RecommendParams {
  priceTier: number;
  countryIndex: number;
  regionIndex: number;
  wineType: WineType;
  pairingText?: string;
}

export async function fetchRecommendation(params: RecommendParams): Promise<WineCard | null> {
  const search = new URLSearchParams({
    price_tier: String(params.priceTier),
    country_index: String(params.countryIndex),
    region_index: String(params.regionIndex),
    wine_type: params.wineType,
  });
  if (params.pairingText) search.set("pairing_text", params.pairingText);

  const response = await fetch(`/api/recommend?${search.toString()}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`recommend 요청 실패: ${response.status}`);
  return response.json();
}

export function imageUrl(pdataId: string | null, variant: "thumb" | "removebg" = "removebg"): string | null {
  if (!pdataId) return null;
  return `/api/images/${pdataId}?variant=${variant}`;
}
```

- [ ] **Step 3: `page.tsx`에서 mock 데이터/로직 제거, API 훅으로 교체**

`frontend/app/page.tsx` 전체를 아래로 교체(기존 mock 상수 `REGIONS`/`GRAPES`/`TIERS`/`PAIRINGS`/
`computeWineFor`/`buildCard`는 전부 제거 — 백엔드가 대체):

```typescript
"use client";

import { useEffect, useState } from "react";
import styles from "./wine-recommend.module.css";
import { fetchRecommendation, imageUrl, type WineCard, type WineType } from "./api";

const COMPANION_TYPE: Record<WineType, WineType> = { Red: "White", White: "Sparkling", Sparkling: "Red" };
const TIER_CAP_COLORS = [
  "#D8CDBB", "#D8CDBB", "#C9A24B", "#C9A24B", "#C9A24B",
  "#C9A24B", "#7A1F2B", "#7A1F2B", "#7A1F2B", "#7A1F2B",
];
const GLASS_COLOR: Record<WineType, string> = { Red: "#5C1F2E", White: "#C9BC79", Sparkling: "#D8C687" };

interface CardState {
  visible: boolean;
  saved: boolean;
  swap: number;
}

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

export default function Home() {
  const [isIntro, setIsIntro] = useState(true);
  const [introStep, setIntroStep] = useState(0);
  const [typeAnswer, setTypeAnswer] = useState<WineType>("Red");
  const [regionIndex, setRegionIndex] = useState(0);
  const [countryIndex, setCountryIndex] = useState(0);
  const [tierIndex, setTierIndex] = useState(0);
  const [pairingText, setPairingText] = useState("");
  const [pairingInput, setPairingInput] = useState("");
  const [cards, setCards] = useState<Record<"a" | "b", CardState>>({
    a: { visible: true, saved: false, swap: 0 },
    b: { visible: true, saved: false, swap: 0 },
  });
  const [cardData, setCardData] = useState<Record<"a" | "b", WineCard | null>>({ a: null, b: null });
  const [loading, setLoading] = useState(false);

  function selectIntro(stepIdx: number, value: string | number) {
    if (stepIdx === 1) setTierIndex(Number(value));
    if (stepIdx === 2) setTypeAnswer(value as WineType);
    if (stepIdx < 2) {
      setIntroStep(stepIdx + 1);
    } else {
      setIsIntro(false);
    }
  }

  useEffect(() => {
    if (isIntro) return;
    setLoading(true);
    const typeB = COMPANION_TYPE[typeAnswer];
    Promise.all([
      fetchRecommendation({ priceTier: tierIndex, countryIndex, regionIndex, wineType: typeAnswer, pairingText }),
      fetchRecommendation({ priceTier: tierIndex, countryIndex, regionIndex, wineType: typeB, pairingText }),
    ])
      .then(([a, b]) => setCardData({ a, b }))
      .finally(() => setLoading(false));
  }, [isIntro, typeAnswer, countryIndex, regionIndex, tierIndex, pairingText]);

  function bumpAll() {
    setCards((c) => ({ a: { ...c.a, swap: c.a.swap + 1 }, b: { ...c.b, swap: c.b.swap + 1 } }));
  }
  function priceUp() {
    if (tierIndex >= 9) return;
    setTierIndex((t) => t + 1);
    bumpAll();
  }
  function priceDown() {
    if (tierIndex <= 0) return;
    setTierIndex((t) => t - 1);
    bumpAll();
  }
  function regionNext() {
    setRegionIndex((r) => r + 1);
    bumpAll();
  }
  function countryNext() {
    setCountryIndex((c) => c + 1);
    setRegionIndex(0);
    bumpAll();
  }
  function submitPairing() {
    setPairingText(pairingInput.trim());
    bumpAll();
  }
  function toggleSave(id: "a" | "b") {
    setCards((c) => ({ ...c, [id]: { ...c[id], saved: !c[id].saved } }));
  }
  function exclude(id: "a" | "b") {
    setCards((c) => ({ ...c, [id]: { ...c[id], visible: false } }));
  }
  function resetCards() {
    setCards((c) => ({
      a: { visible: true, saved: c.a.saved, swap: c.a.swap + 1 },
      b: { visible: true, saved: c.b.saved, swap: c.b.swap + 1 },
    }));
  }

  const visibleCardIds = (["a", "b"] as const).filter((id) => cards[id].visible && cardData[id]);
  const anyHidden = !(cards.a.visible && cards.b.visible);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.brand}>SIP.</div>
        <div className={styles.tagline}>AI 소믈리에가 지금 이 순간에 맞는 와인을 골라줘요</div>
      </div>

      {isIntro ? (
        <div className={styles.introSection}>
          <div className={styles.dots}>
            {INTRO_STEPS.map((_, i) => (
              <div key={i} className={i <= introStep ? `${styles.dot} ${styles.dotActive}` : styles.dot} />
            ))}
          </div>
          <div key={introStep} className={styles.stepCard}>
            <div className={styles.stepLabel}>Step {introStep + 1} / 3</div>
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
        <>
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
              {!loading && visibleCardIds.map((id) => {
                const card = cardData[id]!;
                const type = id === "a" ? typeAnswer : COMPANION_TYPE[typeAnswer];
                return (
                  <div key={`${id}-${cards[id].swap}`} className={styles.card}>
                    <button type="button" onClick={() => toggleSave(id)} className={cards[id].saved ? `${styles.saveBtn} ${styles.saveBtnActive}` : styles.saveBtn}>
                      &#9825;
                    </button>
                    <button type="button" onClick={() => exclude(id)} className={styles.excludeBtn}>&#10005;</button>

                    <div className={styles.bottleWrap}>
                      <div className={styles.bottleAnim}>
                        <div className={styles.cap} style={{ background: TIER_CAP_COLORS[tierIndex] }} />
                        <div className={styles.neck} style={{ background: GLASS_COLOR[type] }} />
                        <div className={styles.shoulder} style={{ borderBottomColor: GLASS_COLOR[type] }} />
                        <div className={styles.bottleBody} style={{ background: GLASS_COLOR[type] }}>
                          {imageUrl(card.pdata_id) ? (
                            <img src={imageUrl(card.pdata_id)!} alt={card.wine_name} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }} />
                          ) : (
                            <div className={styles.labelPatch}>
                              <div className={styles.labelRegion}>{card.region}</div>
                              <div className={styles.labelGrape}>{card.grape}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className={styles.wineName}>{card.wine_name}</div>
                    <div className={styles.wineMeta}>{card.region}, {card.country} · {card.type_label_kr}</div>

                    <div className={styles.priceRow}>
                      <span className={styles.price}>₩{card.price_krw.toLocaleString()}</span>
                      <span className={styles.priceDesc}>{card.price_desc}</span>
                    </div>

                    <div className={styles.note}>{card.note}</div>

                    <div className={styles.personaBox}>
                      <div className={styles.personaLine}>&ldquo;{card.persona_line}&rdquo;</div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className={styles.pairingWrap}>
              <input
                type="text"
                value={pairingInput}
                onChange={(e) => setPairingInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitPairing()}
                placeholder="같이 먹을 음식"
                className={styles.option}
                style={{ fontSize: 13, padding: "8px 12px", width: 120 }}
              />
              <button type="button" onClick={submitPairing} className={styles.joyBtn}>
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

          {anyHidden && (
            <div className={styles.resetWrap}>
              <button type="button" onClick={resetCards} className={styles.resetLink}>추천 다시 두 개 보기</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 타입체크**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 5: Commit**

```bash
git add frontend/next.config.js frontend/app/api.ts frontend/app/page.tsx
git commit -m "feat: 프론트 mock 제거, /api/recommend·/api/images 연동 + 국가(<<) 버튼/페어링 입력창"
```

---

### Task 13: 디자인 토큰화 (radius/shadow/transition — 색상 팔레트는 유지)

스펙의 "SIP. 크림/테라코타 팔레트 유지, radius/shadow/transition만 CSS 변수로" 항목.
색상 hex 값은 그대로 두고(팔레트 자체를 바꾸는 게 아님), 반복되는 반경/그림자/트랜지션 값만
`.page` 스코프 CSS 변수로 뽑아 한 곳에서 관리되게 한다.

**Files:**
- Modify: `frontend/app/wine-recommend.module.css`

- [ ] **Step 1: `.page` 규칙에 변수 선언 추가**

`frontend/app/wine-recommend.module.css`의 `.page { ... }` 블록을 아래로 교체:

```css
.page {
  min-height: 100vh;
  width: 100%;
  background: #EFE7D8;
  font-family: 'Manrope', sans-serif;
  color: #241C15;

  --wine-radius-card: 28px;
  --wine-radius-chip: 20px;
  --wine-radius-button: 18px;
  --wine-shadow-card: 0 20px 45px rgba(60, 40, 20, 0.14);
  --wine-transition-fast: 0.12s;
  --wine-transition-standard: 0.15s;
}
```

- [ ] **Step 2: 하드코딩된 값을 변수 참조로 교체**

같은 파일에서 아래 치환(값은 그대로, 참조만 바뀜):
- `.card`의 `border-radius: 28px;` → `border-radius: var(--wine-radius-card);`
- `.card`의 `box-shadow: 0 20px 45px rgba(60, 40, 20, 0.14);` → `box-shadow: var(--wine-shadow-card);`
- `.chip`의 `border-radius: 20px;` → `border-radius: var(--wine-radius-chip);`
- `.personaBox`의 `border-radius: 20px;` → `border-radius: var(--wine-radius-chip);`
- `.joyBtn`의 `border-radius: 18px;` → `border-radius: var(--wine-radius-button);`
- `.joyBtn`의 `transition: transform 0.12s;` → `transition: transform var(--wine-transition-fast);`
- `.option`의 `transition: all 0.15s;` → `transition: all var(--wine-transition-standard);`
- `.excludeBtn`의 `transition: all 0.15s;` → `transition: all var(--wine-transition-standard);`

- [ ] **Step 3: 프론트 다시 띄워서 시각적으로 그대로인지 확인**

Run: (Task 14의 dev 서버로 확인 — 카드 모서리 둥글기/그림자/버튼 눌림 애니메이션이 이전과
동일하면 통과. 값 자체를 안 바꿨으므로 육안상 차이 없어야 정상.)

- [ ] **Step 4: Commit**

```bash
git add frontend/app/wine-recommend.module.css
git commit -m "refactor: radius/shadow/transition CSS 변수화 (팔레트는 유지)"
```

---

### Task 14: 통합 검증 (수동)

**Files:** 없음(검증만)

- [ ] **Step 1: 백엔드 기동**

Run:
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 2: 헬스체크 + 추천 엔드포인트 curl 확인**

Run:
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/recommend?price_tier=3&country_index=0&region_index=0&wine_type=Red"
```
Expected: 헬스체크 `{"status":"ok"}`. 추천은 200(카드 JSON) 또는 그 티어에 진짜 재고가 없으면
404 — 404면 `price_tier`를 다른 값으로 바꿔가며 실데이터가 있는 조합 확인.

- [ ] **Step 3: 가격 ETL 1회 수동 실행**

Run: `cd backend && python -m etl.sync_price`
Expected: `[sync_price] N건 갱신` (N > 0)

- [ ] **Step 4: 프론트 기동 후 브라우저로 전체 플로우 클릭 확인**

Run: `cd frontend && npm run dev` (또는 이 세션에서 `preview_start` 사용)

체크리스트:
- 질문 3개 답변 → 카드 2개(레드+화이트 등) 실제 DB 와인 이름/가격으로 나오는지
- 가격 UP/DOWN, 지역(`<`)/국가(`<<`) 눌렀을 때 카드가 실제로 바뀌는지
- 페어링 입력창에 음식 이름 넣고 검색 눌렀을 때 personaLine이 그 음식 이름으로 바뀌는지
- 병 이미지가 NAS1에서 실제로 로드되는지(비어있으면 `bottleImg`/`pdataId` 없는 SKU가 뽑힌 것 —
  다른 조합으로 재확인)

- [ ] **Step 5: 문제 있으면 해당 Task로 돌아가 수정 후 재검증, 없으면 완료**
