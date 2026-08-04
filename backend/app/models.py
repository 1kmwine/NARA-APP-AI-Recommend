from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WinePriceCache(Base):
    __tablename__ = "wine_price_cache"

    item_cd: Mapped[str] = mapped_column(String(45), primary_key=True)
    price_krw: Mapped[int] = mapped_column(Integer)
    price_source: Mapped[str] = mapped_column(String(20))  # 'tb_product' | 'v_daily_sale_calc'
    synced_at: Mapped[datetime] = mapped_column(DateTime)
