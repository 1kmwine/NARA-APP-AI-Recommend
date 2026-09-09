# NARA-APP-AI-Recommend

"AI 와인 추천" 블록 — 고객 취향을 좁혀가며 맞춤 와인을 추천한다. 토너먼트(브라켓) 방식으로
선호를 수집하고, 향/페어링/가격대 정보를 붙여 추천 결과를 낸다.

- Nblocks 허브 블록: **a2 (앱 레이어, 데이터·AI팀)**
- 개발서버: <http://192.168.47.105:3005>
- 접근 권한: 사원+

## 기능

| 영역 | 내용 |
|---|---|
| 추천 (`routers/recommend.py`) | 수집된 선호로 와인 추천 — `services/recommend.py` |
| 브라켓 (`routers/bracket.py`) | 토너먼트식 취향 수집 — `services/bracket.py`, `bracket_content.py` |
| 이미지 (`routers/images.py`) | 와인 병 이미지 서빙 — `services/images.py` |
| 부가 정보 | 향(`aroma.py`), 페어링(`pairing.py`), 가격대(`price_tiers.py`), 브랜드 설명(`brand_content.py`), 산지(`region_cache.py`, `region_overrides.py`) |
| ETL | 가격 동기화 — `backend/etl/sync_price.py` |
| 프론트 | 취향 선택·추천 결과·찜 목록(`app/liked`), 선호 상태는 `preferences.ts`/`useBracket.ts` |

## 구성

```
backend/     FastAPI ("AI Wine Recommend API") — routers/ + services/ + etl/, tests
frontend/    Next.js — 추천 UI (컨테이너 3005:3000, BACKEND_URL로 백엔드 프록시)
docker-compose.yml   backend(내부) + frontend 3005:3000
```

백엔드는 외부 포트를 열지 않고 프론트가 컨테이너 네트워크(`http://backend:8000`)로 호출한다.

## 실행

```bash
docker compose up -d --build
```

테스트: `cd backend && pytest`

## 배포

CI 없음 — 개발서버에서 pull 후 `docker compose up -d --build`.
(CI를 붙이려면 허브 문서 §7-3의 docker-compose 블록용 템플릿 사용)

## 참고

- 허브 구조: [`NARA-AI-Playground/docs/ARCHITECTURE.md`](https://github.com/1kmwine/NARA-AI-Playground/blob/main/docs/ARCHITECTURE.md)
- 디자인 시스템: 색상 하드코딩 금지 — 허브 `design-system/design-system.css` 토큰 확인
- 자격증명: 실제 값은 `docs/CREDENTIALS.local.md`(gitignore)에만, 커밋 문서엔 `{{PLACEHOLDER}}`
