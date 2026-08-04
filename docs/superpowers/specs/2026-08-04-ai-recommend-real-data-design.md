# AI 와인 추천 — 실데이터 연동 설계

## 배경

`docs/superpowers/specs/2026-07-31-frontend-scaffold-design.md`(프론트 스캐폴드) 이후,
Claude Design 목업("SIP.", 조이스틱 토글 카드)을 [frontend/app/page.tsx](../../../frontend/app/page.tsx)에
mock 데이터로 구현 완료(커밋 `f304409`). 이 문서는 그 UI를 실제 데이터(나라셀라 와인 DB,
NAS 이미지, POS 가격)로 연동하는 설계다.

## 확정된 MVP UI (변경 없음)

질문 3개(상황/가격대/타입) → 추천 카드 1~3개 → 4방향 조이스틱 토글로 재추천:
- 위/아래: 가격 UP/DOWN
- 왼쪽: 지역 변경(`<`) / 국가 변경(`<<`)
- 오른쪽: **페어링 — 이 문서에서 변경됨, 아래 "페어링" 절 참고**
- X: 배제, ♡: 저장(세션 로컬만)

## 아키텍처

이 앱 전용 FastAPI 백엔드(`backend/`) 신설. 허브 관례(블록별 자기 스키마)를 따라
새 스키마 `ai_recommend` + 계정 `ai_recommend_app` 신설 — `wine_info` 스키마의 테이블에
쓰기 접근하지 않는다(그 레포의 "블록 격리" 원칙 유지, 관련 조사는
[NARA-DATA-Wine-Info 조사 기록](#조사-원본-메모) 참고).

**필요 DB 계정** (`docs/CREDENTIALS.local.md`에 이미 값 저장됨):
| 계정 | 스키마/테이블 | 권한 |
|---|---|---|
| `ai_recommend_app` | `ai_recommend`(전체) | DDL+DML |
| `ai_recommend_app` | `wine_info.integrated_item_info`, `wine_info.wine_notes` | SELECT |
| `ai_recommend_pos_ro` | `pos.tb_product`, `pos.v_daily_sale` | SELECT |

⚠️ **인프라 미완료 항목**: 위 스키마/계정/GRANT는 서버에 아직 실제로 만들어지지 않았을 수 있음
(자격증명 값은 확보했으나 DBA/서버 쪽 실행 확인 필요) — 백엔드 개발 착수 전 첫 번째로 검증할 것.

## 데이터 흐름

### 가격 (10단계)

고정 구간(원 단위, 사용자 확정):
`~1만 / ~2만 / ~3만 / ~5만 / ~7만 / ~10만 / ~30만 / ~100만 / ~1000만 / 1000만~`(최소~최대)

가격은 `wine_info`에 컬럼 자체가 없어 우리 스키마에 별도 캐시:
```sql
-- ai_recommend.wine_price_cache
item_cd      VARCHAR(45) PRIMARY KEY,
price_krw    INT,
price_source ENUM('tb_product', 'v_daily_sale_calc'),
synced_at    DATETIME
```

ETL(`backend/etl/sync_price.py`, 이 레포 소유): `ai_recommend_pos_ro`로 `pos.tb_product.price__original`
우선 조회 → 없으면 `pos.v_daily_sale`의 `sale__amt / sales_qty` 평균단가 계산 → upsert.
조회 시 FastAPI는 같은 MariaDB 서버 특성을 활용해 `wine_info.integrated_item_info`와
`ai_recommend.wine_price_cache`를 크로스스키마 JOIN.

정확히 맞는 티어에 SKU가 없으면(10단계라 흔함) 인접 티어로 폭을 넓혀가며 재검색하는
폴백 필수 — 완전히 빈 카드 상태 방지.

### 지역/국가 순회

DB에 순서 개념이 없어(자유텍스트 `place`/`country` JSON) FastAPI 시작 시(또는 TTL 캐시)
`integrated_item_info`를 집계: **보유 SKU 개수 내림차순**으로 국가 목록, 각 국가 내 지역 목록 정렬.
`NARA-DATA-Wine-Info`의 `quicklook/wine-info/helpers.php`에 있는 `REGION_COUNTRY_OVERRIDE`
(171건) 상당의 보정 로직을 Python으로 포팅해서 지역명 오염(`countryName`="Korea" 오염 등)을
피해야 함 — SQL(CASE/CTE)로 하려던 시도는 그 레포에서 이미 실패 이력 있음(애플리케이션 레이어 처리 권장).

`<` = 같은 국가 내 다음 지역, `<<` = 다음 국가의 첫 지역. UI: 왼쪽 컬럼에 버튼 세로 스택
(위 `<<`/국가, 아래 `<`/지역).

### 페어링 — 조이스틱 카테고리 대신 자유텍스트 입력 (변경됨)

**변경 사유**: 애초 "10개 카테고리 조이스틱 토글"로 설계했으나, 사용자 요청으로 자유텍스트
음식 입력("이거 먹을 건데 뭐가 어울려?")으로 전환. 별도 지식 소스 조사 중 AWINE(awine.kr, 1,102건
음식-와인 페어링 DB)을 발견했으나 `robots.txt`에 `Content-Signal: ai-train=no`가 명시돼 있어
(크롤링 자체는 허용해도 학습/대량 자산화는 거부 신호) 사용하지 않기로 결정. 대신 원리 기반
접근으로 전환.

**매칭 알고리즘** — Wine Folly(winefolly.com, robots.txt 제한 없음)의 congruent/complementary
페어링 방법론을 채택:
1. 음식의 6대 기본맛(짠맛/산미/단맛/쓴맛/지방/매운맛) 중 지배적인 요소를 텍스트에서 추출
   (자유텍스트 → 이 벡터로 변환하는 단계는 LLM 호출로 처리 — 별도 스크래핑 DB 없이 그때그때 추론)
2. 와인의 구조(`wine_notes.taste` 우선, 없으면 `integrated_item_info.taste`의 sweetness/acidity/
   body/tannin)와 두 가지 방식으로 매칭:
   - **Complementary(대비)**: 와인의 산도/타닌으로 음식의 지방/짠맛을 상쇄
   - **Congruent(공명)**: 향 계열이 겹치는 것끼리 강화(예: 후추 향 계열 스파이스 ↔ 시라 특유의
     후추 노트)
3. 완전 필터가 아니라 랭킹 가중치로 반영(후보가 너무 좁아지는 것 방지 — 기존 설계와 동일 원칙 유지)

**참고 자료** (직접 스크래핑해 우리 말로 재정리, 원문 그대로 인용 안 함 — 저작권 고려):
- winefolly.com `/tutorial/getting-started-with-food-and-wine-pairing/` — 방법론 원본(6대 기본맛, congruent/complementary 구분)
- winefolly.com `/tutorial/never-fear-the-grill-wine-pairings-with-barbecue/` — 바비큐/구이별 매칭
- winefolly.com `/tutorial/6-tips-on-pairing-wine-and-cheese/` — 치즈 숙성도/식감별 매칭
- winefolly.com `/tutorial/what-wines-to-pair-with-chocolate/` — 초콜릿 종류별 매칭
- winefolly.com `/tutorial/pairing-bold-red-wines-with-vegetarian-or-vegan-food/` — 채식 매칭
- winefolly.com `/tutorial/herb-and-spice-pairings-with-wine/` — 향신료 9개 카테고리 분류
- wine21.com(Idx=17341, Idx=17603) — 한식 특화 보정(불고기/잡채/전 등, 여러 반찬 동시 상 차림 특성)

**UI 변경**: 조이스틱 오른쪽 화살표 버튼(고정 목록 순회) → 텍스트 입력창 + 제출 버튼으로 교체.
같은 조이스틱 오른쪽 슬롯 위치 유지. 상세 레이아웃은 구현 단계에서 확정.

## 추천 알고리즘 (요약)

조이스틱 상태(가격티어 0~9 / 국가·지역 인덱스 / 와인타입) + 페어링 자유텍스트(선택) →
후보 조회(타입+지역+가격대 필터) → 폴백 확장(빈 결과 방지) → 페어링 텍스트 있으면 taste벡터
거리로 재랭킹 → `wishes`/`reviews` 내림차순 상위 1~3개.

## 이미지

NAS1(QNAP, `el.naracellar.com`) 공유링크 프록시를 FastAPI로 포팅: `GET /api/images/{pdataId}?variant=removebg`.
인증 불필요(비공식 공유링크 패턴). NAS2(브랜드 이미지)는 스코프 밖.

## 디자인 시스템

SIP. 크림/테라코타 팔레트·Instrument Serif 유지. `radius`/`shadow`/`transition` 값만 CSS 변수로
뽑아 허브 `design-system.css` 네이밍 관례를 따름(색상 팔레트는 하드코딩 유지). NARA-Design-System
원본(Tailwind 아님, 인라인 style React)은 그대로 이식 불가라 토큰 값만 참고.

## 스코프 밖

- `wines-admin` JWT 인증 연동
- NAS2 브랜드 히어로 이미지
- 기사/매출 데이터 노출
- ♡ 저장 영속화(세션 로컬만, DB 저장 안 함)
- AWINE류 대량 페어링 DB 스크래핑(정책상 배제)

## 조사 원본 메모

- NARA-DATA-Wine-Info: NestJS+TypeORM+MariaDB, 실데이터는 `integrated_item_info`(9,214건,
  ERP+POS+1KM레거시 조인) 하나뿐 — 정규화된 `wines/wineries/grapes` 스키마는 설계만 있고 데이터 0건.
  가격 컬럼 없음. 국가/지역은 자유텍스트+PHP 하드코딩 보정으로 운영 중.
- NARA-Design-System: Tailwind 아님, npm 패키지 아님, 인라인 style React 컴포넌트 — 소스 복사로만
  가져올 수 있고 로컬 `design-system.css`는 이미 독자 재해석된 결과물.
