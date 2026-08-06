from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


def fetch_brand_articles(session: Session, brand_names: list[str]) -> dict[str, list[dict]]:
    """wine_article_brands로 브랜드명↔기사 매칭을 찾고, 기사 제목/발췌/URL을 브랜드명
    기준으로 묶어서 반환한다. 매칭 기사가 없는 브랜드는 결과 dict에 키 자체가 없다
    (호출 측이 "이 브랜드는 스토리 없음"으로 취급하면 됨)."""
    if not brand_names:
        return {}
    stmt = text(
        """
        SELECT b.brand_name, a.title, a.excerpt, a.external_url
        FROM wine_info.wine_article_brands b
        JOIN wine_info.wine_articles a ON a.id = b.article_id
        WHERE b.brand_name IN :brand_names
        """
    ).bindparams(bindparam("brand_names", expanding=True))
    rows = session.execute(stmt, {"brand_names": list(brand_names)}).mappings().all()

    result: dict[str, list[dict]] = {}
    for row in rows:
        result.setdefault(row["brand_name"], []).append(
            {"title": row["title"], "excerpt": row["excerpt"], "url": row["external_url"]}
        )
    return result


def fetch_brand_intro(session: Session, brand_names: list[str]) -> dict[str, str]:
    """brand_intro.introText를 브랜드명 기준으로 조회한다."""
    if not brand_names:
        return {}
    stmt = text(
        "SELECT brandName, introText FROM wine_info.brand_intro WHERE brandName IN :brand_names"
    ).bindparams(bindparam("brand_names", expanding=True))
    rows = session.execute(stmt, {"brand_names": list(brand_names)}).mappings().all()
    return {row["brandName"]: row["introText"] for row in rows}
