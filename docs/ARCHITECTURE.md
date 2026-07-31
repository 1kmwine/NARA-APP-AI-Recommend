# ARCHITECTURE

## 이 블록의 위치

허브 `nara-information-digest`(github.com/1kmwine/NARA-Information-Digest)가 정의한
33개 블록 중 앱 레이어(데이터·AI팀 담당) 블록. 레이어 표 기준:

| 항목 | 값 |
|---|---|
| 블록명 | AI 와인 추천 |
| 리포 이름 | `nara-app-ai-recommend` |
| 레이어 | 앱 (`nara-app-*`) |
| URL 경로(허브 하위) | `/app/ai-recommend` (허브가 nginx/Next.js rewrite로 프록시) |

## 기술 스택 (허브 컨벤션, §4/§4.1)

| 영역 | 선택 | 상태 |
|---|---|---|
| 프론트엔드 | Next.js (React), App Router | 이번 단계에서 스캐폴드 완료 |
| 백엔드 | Python (FastAPI) — 앱 레이어(통계·분석·AI) 기본값 | 미착수 (다음 단계) |
| DB | MariaDB (`{{DB_HOST}}`, 블록 전용 스키마 `ai_recommend` 예정, 계정 `ai_recommend_app` 형태로 다른 블록과 동일 패턴) | 미착수 (다음 단계) |
| 인증 | 허브 SSO 세션/토큰 전달 | 미착수 |
| 배포 | Docker Compose + nginx 리버스 프록시, 개발서버 `{{DEV_SERVER_HOST}}` | 미착수 |

## 참고

전체 허브 구조, 다른 블록과의 관계, 테스트 서버/DB/NAS 접속 정보는
`NARA-Information-Digest` 리포의 `docs/ARCHITECTURE.md`를 참고한다(실제 접속값은
그 리포의 `docs/CREDENTIALS.local.md`에만 있음, 여기서 복제하지 않는다).
