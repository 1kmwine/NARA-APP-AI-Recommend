# DB 인프라 검증 결과 (2026-08-04)

> `2026-08-04-ai-recommend-real-data-design.md`의 "⚠️ 인프라 미완료 항목"(스키마/계정/GRANT가
> 서버에 실제로 만들어졌는지 검증 필요)에 대한 답 — Info-Digest 허브 쪽에서 진행 중이던 33블록
> DB 재설계 작업 중 실서버(`192.168.47.105`)를 실측하다 이 레포 관련 상태도 같이 확인했다.
> **이 문서는 확인 결과 보고만 함 — 이 레포 코드는 건드리지 않았다** (동시 작업 중인 것으로
> 파악해 충돌 방지).

## 결론: 스펙과 실제 서버 상태가 다르다 — 지금 이대로 백엔드 붙이면 DB 연결 실패

### 1. `ai_recommend` 스키마 자체가 서버에 없음

```
mariadb> SHOW DATABASES;
-- ai_recommend 없음. wine_info / market_share / pos / it_schedule / sys 뿐.
```

`backend/.env`의 `AI_RECOMMEND_DB_NAME=ai_recommend`로 `app/db.py`의 메인 엔진이 연결을
시도하면 `Unknown database 'ai_recommend'`로 즉시 실패한다. `CREATE DATABASE ai_recommend;`
필요.

### 2. `ai_recommend_app` 계정 권한이 스펙과 반대로 되어 있음

스펙(설계 문서 표)이 원한 것:

| 스키마 | 권한 |
|---|---|
| `ai_recommend`(전체) | DDL+DML |
| `wine_info.integrated_item_info`, `wine_info.wine_notes` | SELECT만 |

실제 `SHOW GRANTS FOR 'ai_recommend_app'@'%'`:

```
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER,
      CREATE VIEW, SHOW VIEW, TRIGGER, DELETE HISTORY
  ON `wine_info`.* TO `ai_recommend_app`@`%` WITH GRANT OPTION
```

- `ai_recommend` 스키마 자체엔 권한이 **없음**(스키마가 없으니 당연).
- `wine_info` 전체(테이블 2개가 아니라 스키마 전체)에 DDL 포함 풀권한 + `GRANT OPTION`까지 —
  스펙보다 훨씬 넓게 열려 있음. 아마 스키마 분리 세팅 도중 임시로 잘못 부여된 것으로 보임.

### 3. `ai_recommend_pos_ro` 계정도 스펙보다 넓게 열려 있음(막힌 건 아님)

스펙: `pos.tb_product`, `pos.v_daily_sale` SELECT만.
실제: `GRANT SELECT ON pos.* TO 'ai_recommend_pos_ro'@'%'` — `pos` 스키마 전체 SELECT.
필요한 두 테이블은 포함되어 있어 이것 때문에 막히진 않음. 최소권한 원칙엔 안 맞음.

## 스펙대로 맞추려면 필요한 DDL (실행 안 함 — 검토 후 적용)

```sql
-- 1. ai_recommend 스키마 생성
CREATE DATABASE ai_recommend CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. ai_recommend_app 권한을 스펙대로 재설정
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'ai_recommend_app'@'%';
GRANT ALL PRIVILEGES ON ai_recommend.* TO 'ai_recommend_app'@'%';
GRANT SELECT ON wine_info.integrated_item_info TO 'ai_recommend_app'@'%';
GRANT SELECT ON wine_info.wine_notes TO 'ai_recommend_app'@'%';

-- 3. ai_recommend_pos_ro를 최소권한으로 좁힘 (선택 — 지금도 동작은 함)
REVOKE ALL PRIVILEGES ON pos.* FROM 'ai_recommend_pos_ro'@'%';
GRANT SELECT ON pos.tb_product TO 'ai_recommend_pos_ro'@'%';
GRANT SELECT ON pos.v_daily_sale TO 'ai_recommend_pos_ro'@'%';

FLUSH PRIVILEGES;
```

`REVOKE ALL ... FROM 'ai_recommend_app'` 시점부터 GRANT 두 줄이 실행되기 전까지는 이 계정으로
붙은 커넥션이 전부 끊긴다 — 배포된 백엔드가 아직 없는 지금(스캐폴드 단계) 실행하는 게
안전하다. 이 레포에서 백엔드 트래픽이 생긴 뒤로 미루지 말 것.

## 참고: `wine_info_db_name` 설정이 이미 있는데 안 쓰이고 있음

`app/config.py`에 `wine_info_db_name: str = "wine_info"` 필드가 있지만 `app/db.py`
어디서도 참조 안 됨 — 지금은 `region_cache.py`가 `FROM wine_info.integrated_item_info`처럼
쿼리 안에서 직접 스키마를 명시해 크로스스키마 접근하는 방식이라 이 필드 없이도 동작은 하게
설계되어 있음(메인 엔진 접속 스키마만 고쳐지면). 죽은 설정값이니 필요 없으면 정리해도 됨 —
판단은 이 레포 작업자 몫.

## 정리

- 코드 변경 불필요할 수도 있음(`app/db.py`의 `wine_info` 관련 로직은 스펙 설계와 일치) —
  **DB 쪽 GRANT/스키마 생성만** 스펙에 안 맞음.
- 위 SQL 3단계 적용 후 `python -c "from app.db import engine; engine.connect()"` 같은 걸로
  연결 검증 권장.
