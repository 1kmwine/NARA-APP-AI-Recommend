# AI 와인 추천 블록 — 프론트엔드 스캐폴드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `NARA-APP-AI-Recommend` 로컬 리포에 Next.js 15 + React 19 + TypeScript 프론트엔드 뼈대와 프로젝트 문서(README/CLAUDE.md/ARCHITECTURE.md)를 만들어, "AI 와인 추천" 자리표시 페이지가 로컬에서 `npm run dev`로 뜨는 상태를 만든다.

**Architecture:** `NARA-MGMT-Revenue/frontend`의 실제 컨벤션(App Router, `styles/design-system.css`는 허브 공용 파일 그대로 복사, `next.config.js`/`tsconfig.json` 동일 설정)을 그대로 이식한다. 백엔드/DB/배포는 이번 계획 범위 밖(스펙 참고: `docs/superpowers/specs/2026-07-31-frontend-scaffold-design.md`).

**Tech Stack:** Next.js 15, React 19, TypeScript 5.5, npm.

---

### Task 1: 루트 문서 (CLAUDE.md, README.md, docs/ARCHITECTURE.md, .gitignore)

**Files:**
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/CLAUDE.md`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/README.md`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/docs/ARCHITECTURE.md`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/.gitignore`

- [ ] **Step 1: `.gitignore` 작성**

```
node_modules/
.next/
next-env.d.ts
*.tsbuildinfo
.env
CREDENTIALS.local.md
```

- [ ] **Step 2: `CLAUDE.md` 작성**

```markdown
# CLAUDE.md

## 자격증명 취급 규칙

실제 비밀번호/토큰/키는 절대 트래킹되는 파일에 쓰지 않는다. `docs/CREDENTIALS.local.md`(gitignore 처리, 로컬 전용)에만 실제 값을 기록하고, `docs/ARCHITECTURE.md` 등 커밋되는 문서엔 `{{PLACEHOLDER}}` 형태로만 참조한다.

- 새 서버/DB/NAS 접속 정보 추가 시: 실제 값 → `docs/CREDENTIALS.local.md`에 추가, 문서엔 플레이스홀더만.
- `docs/CREDENTIALS.local.md`는 `git add`/`git commit` 대상에서 항상 제외.
```

- [ ] **Step 3: `README.md` 작성**

```markdown
# NARA-APP-AI-Recommend

나라셀라 정보 대시보드(`nara-information-digest`) 앱 레이어 블록 — AI 와인 추천 (`nara-app-ai-recommend`).

현재 단계: 프론트엔드 스캐폴드만. 화면 구현은 Claude Design 목업 수신 후 진행.
```

- [ ] **Step 4: `docs/ARCHITECTURE.md` 작성**

```markdown
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
```

- [ ] **Step 5: Commit**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add .gitignore CLAUDE.md README.md docs/ARCHITECTURE.md
git commit -m "docs: 루트 문서 (CLAUDE.md, README, ARCHITECTURE)"
```

---

### Task 2: 프론트엔드 프로젝트 설정 (package.json, next.config.js, tsconfig.json)

**Files:**
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/package.json`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/next.config.js`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/tsconfig.json`

- [ ] **Step 1: `package.json` 작성**

```json
{
  "name": "ai-wine-recommend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^19.0.0",
    "typescript": "^5.5.0"
  }
}
```

- [ ] **Step 2: `next.config.js` 작성**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {};
module.exports = nextConfig;
```

- [ ] **Step 3: `tsconfig.json` 작성**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/package.json frontend/next.config.js frontend/tsconfig.json
git commit -m "chore: Next.js 프론트엔드 프로젝트 설정"
```

---

### Task 3: 앱 라우트 + 디자인 시스템

**Files:**
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/styles/design-system.css` (허브 원본 그대로 복사)
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/app/layout.tsx`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/app/globals.css`
- Create: `/Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/app/page.tsx`

- [ ] **Step 1: 허브 공용 디자인 시스템 CSS 그대로 복사**

```bash
cp /Users/jaeyungsong/Projects/NARA-Information-Digest/design-system/design-system.css \
   /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend/styles/design-system.css
```

- [ ] **Step 2: `app/layout.tsx` 작성**

```tsx
import "../styles/design-system.css";
import "./globals.css";

export const metadata = { title: "AI 와인 추천" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: `app/globals.css` 작성 (자리표시 — 목업 반영 시 채움)**

```css
/* 목업 반영 전까지 비워둠. 화면 구현 시 design-system.css 위에 필요한 규칙만 추가. */
```

- [ ] **Step 4: `app/page.tsx` 작성**

```tsx
export default function Home() {
  return (
    <main style={{ padding: 32 }}>
      <h1>AI 와인 추천</h1>
      <p>목업 반영 예정 — 아직 자리표시 화면입니다.</p>
    </main>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/styles/design-system.css frontend/app/layout.tsx frontend/app/globals.css frontend/app/page.tsx
git commit -m "feat: AI 와인 추천 자리표시 페이지 + 디자인 시스템 연결"
```

---

### Task 4: 로컬 동작 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: 의존성 설치**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend/frontend
npm install
```

Expected: `node_modules/`와 `package-lock.json` 생성, 에러 없이 종료.

- [ ] **Step 2: 프로덕션 빌드로 스캐폴드 검증**

```bash
npm run build
```

Expected: `Compiled successfully` 로그와 함께 `.next/` 생성. 타입 에러/빌드 에러 없어야 함.

- [ ] **Step 3: 개발 서버로 자리표시 페이지 확인**

```bash
npm run dev
```

Expected: `http://localhost:3000`에서 "AI 와인 추천" 제목 + "목업 반영 예정" 문구가 보임. 확인 후 `Ctrl+C`로 종료.

- [ ] **Step 4: `package-lock.json` 커밋**

```bash
cd /Users/jaeyungsong/Projects/NARA-APP-AI-Recommend
git add frontend/package-lock.json
git commit -m "chore: package-lock.json"
```

---

## 이 계획 이후 (범위 밖, 다음 단계)

- Claude Design 목업 수신 → `app/page.tsx`/`globals.css` 실제 화면으로 교체
- `backend/`(FastAPI) + MariaDB `ai_recommend` 스키마 추가
- `docker-compose.yml` + 개발서버 배포
- 허브(`NARA-Information-Digest`)에서 AI 와인 추천 블록 카드 활성화(iframe/프록시 연결)
