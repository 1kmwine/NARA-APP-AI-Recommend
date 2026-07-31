# AI 와인 추천 블록 — 프론트엔드 스캐폴드 설계

## 배경

`NARA-Information-Digest`(허브) 아키텍처 문서 기준, 이 리포는 앱 레이어 블록
`nara-app-ai-recommend`("AI 와인 추천")를 담당한다. 최종적으로는 33개 블록 중
하나로 허브 카드에서 iframe/프록시 연결되며, 백엔드는 앱 레이어 컨벤션상
Python(FastAPI), DB는 MariaDB 테스트 서버(`192.168.47.105`) 위 전용 스키마를
쓴다(다른 블록의 패턴, 예: `wine_info` 스키마 + `wine_info_app` 계정과 동일).

이번 단계 범위: **프론트엔드 스캐폴드만.** 실제 화면은 사용자가 Claude Design으로
만들 목업을 받은 뒤 구현한다. 백엔드/DB/배포/허브 카드 활성화는 이후 단계.

## 결정 사항

- 위치: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend` (로컬 git repo, remote 없음 — 나중에 GitHub 리포 추가 예정)
- 스택: Next.js 15 + React 19 + TypeScript, App Router — `NARA-MGMT-Revenue/frontend`와 동일 컨벤션 이식
- 디자인 시스템: `NARA-Information-Digest/design-system/design-system.css` 원본을 그대로 복사해 `frontend/styles/design-system.css`로 사용
- 자리표시 화면: `app/page.tsx`에 "AI 와인 추천" 타이틀의 최소 페이지만 (목업 도착 전까지)
- 테스트: 지금은 테스트할 로직이 없어 vitest 스캐폴드 생략 — 실제 로직(추천 API 연동 등) 생기면 그때 추가
- 문서: 루트 `CLAUDE.md`(자격증명 취급 규칙, 플레이스홀더 방식), `README.md`, `docs/ARCHITECTURE.md`(허브 구조에서 이 블록의 좌표 요약)
- 범위 제외(다음 단계로 미룸): `backend/`, `docker-compose.yml`, MariaDB 스키마, 개발서버 배포, 허브에서 블록 카드 활성화

## 완료 기준

- `cd frontend && npm install && npm run dev`로 로컬에서 자리표시 페이지가 뜬다
- git 커밋 히스토리에 초기 스캐폴드가 기록됨
