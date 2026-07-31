# CLAUDE.md

## 자격증명 취급 규칙

실제 비밀번호/토큰/키는 절대 트래킹되는 파일에 쓰지 않는다. `docs/CREDENTIALS.local.md`(gitignore 처리, 로컬 전용)에만 실제 값을 기록하고, `docs/ARCHITECTURE.md` 등 커밋되는 문서엔 `{{PLACEHOLDER}}` 형태로만 참조한다.

- 새 서버/DB/NAS 접속 정보 추가 시: 실제 값 → `docs/CREDENTIALS.local.md`에 추가, 문서엔 플레이스홀더만.
- `docs/CREDENTIALS.local.md`는 `git add`/`git commit` 대상에서 항상 제외.
