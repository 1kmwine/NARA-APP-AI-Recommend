"""POS(tb_product/v_daily_sale) -> ai_recommend.wine_price_cache 가격 동기화.
수동 실행 또는 cron: `python -m etl.sync_price` (backend/ 에서).
"""
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal, pos_engine
from app.models import WinePriceCache


def compute_price(
    tb_product_row: dict | None, daily_sales: list[dict]
) -> tuple[int, str] | None:
    """tb_product.price__original 우선, 없거나 0/null이면 v_daily_sale 평균단가.
    둘 다 없거나 계산 결과가 비정상(0 이하)이면 None (해당 SKU는 가격 캐시에서 건너뜀)."""
    if tb_product_row and tb_product_row.get("price__original"):
        return (int(tb_product_row["price__original"]), "tb_product")

    total_amt = sum((row.get("sale__amt") or 0) for row in daily_sales)
    total_qty = sum((row.get("sales_qty") or 0) for row in daily_sales)
    if total_qty > 0:
        price = round(total_amt / total_qty)
        # v_daily_sale에 반품/환불로 인한 음수 qty/amt 행이 섞여 있을 수 있어
        # (2026-08-04 확인, 실데이터), 순합이 양수라도 계산된 단가가 0 이하로
        # 나올 수 있다 — 그런 값은 캐시하지 않고 건너뛴다(잘못된 가격을 사용자에게
        # 노출하는 것보다 "가격 모름"이 낫다).
        if price > 0:
            return (price, "v_daily_sale_calc")

    return None


def run_sync() -> int:
    """POS에서 전체 item_cd에 대해 가격을 계산해 wine_price_cache를 upsert한다.
    반환값: 갱신된 행 수."""
    with pos_engine.connect() as pos_conn:
        product_rows = pos_conn.execute(
            text("SELECT item_cd, price__original FROM tb_product")
        ).mappings().all()
        # v_daily_sale엔 item_cd가 없다 - erp_goods_cd가 tb_product.item_cd와 같은 포맷
        # (예: 11USFN0100962021)이라 조인 키로 쓴다. sale_amt/sale_qty도 실제 컬럼명이
        # 계획 문서의 sale__amt/sales_qty와 달라 별칭으로 맞춘다.
        sale_rows = pos_conn.execute(
            text(
                "SELECT erp_goods_cd AS item_cd, sale_amt AS sale__amt, "
                "sale_qty AS sales_qty FROM v_daily_sale"
            )
        ).mappings().all()

    products_by_item: dict[str, dict] = {r["item_cd"]: dict(r) for r in product_rows}
    sales_by_item: dict[str, list[dict]] = {}
    for r in sale_rows:
        sales_by_item.setdefault(r["item_cd"], []).append(dict(r))

    all_item_cds = set(products_by_item) | set(sales_by_item)
    # ponytail: 델리스트된 와인의 캐시 행은 여기서 안 지운다 — POS 조회 실패로
    # 일시적으로 빠진 것과 진짜 델리스트를 구분 못 해서, 지우는 게 더 위험할 수
    # 있음. 필요해지면 별도 정리 배치로 처리.

    updated = 0
    session: Session = SessionLocal()
    try:
        for item_cd in all_item_cds:
            priced = compute_price(products_by_item.get(item_cd), sales_by_item.get(item_cd, []))
            if priced is None:
                continue
            price_krw, source = priced
            session.merge(
                WinePriceCache(
                    item_cd=item_cd,
                    price_krw=price_krw,
                    price_source=source,
                    synced_at=datetime.utcnow(),
                )
            )
            updated += 1
        session.commit()
    finally:
        session.close()

    return updated


if __name__ == "__main__":
    n = run_sync()
    print(f"[sync_price] {n}건 갱신")
