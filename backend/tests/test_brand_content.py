from unittest.mock import MagicMock

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.services.brand_content import fetch_brand_articles, fetch_brand_intro


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


def test_bindparam_expanding_actually_expands_in_clause_on_real_engine():
    """Regression guard (Task 3 교훈): mock 테스트는 IN절이 실제로 여러 항목으로
    확장되는지 검증하지 못한다. bindparam(expanding=True)가 이 SQLAlchemy
    버전에서 실제 엔진 위에 여러 항목을 올바르게 바인딩하는지 최소 쿼리로 확인한다.
    (wine_info. 스키마 프리픽스는 SQLite가 못 읽으므로 여기선 무프리픽스 테이블 사용)"""
    from sqlalchemy import bindparam

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE brand_intro (brandName TEXT, introText TEXT)"))
        conn.execute(
            text("INSERT INTO brand_intro (brandName, introText) VALUES (:brandName, :introText)"),
            [
                {"brandName": "브랜드1", "introText": "소개1"},
                {"brandName": "브랜드2", "introText": "소개2"},
                {"brandName": "브랜드3", "introText": "소개3"},
            ],
        )

    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        stmt = text(
            "SELECT brandName, introText FROM brand_intro WHERE brandName IN :brand_names"
        ).bindparams(bindparam("brand_names", expanding=True))
        rows = session.execute(stmt, {"brand_names": ["브랜드1", "브랜드2"]}).mappings().all()
    finally:
        session.close()

    assert {row["brandName"] for row in rows} == {"브랜드1", "브랜드2"}
