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
