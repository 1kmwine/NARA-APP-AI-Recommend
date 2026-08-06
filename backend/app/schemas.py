from pydantic import BaseModel


class WineTaste(BaseModel):
    sweetness: int
    acidity: int
    body: int
    tannin: int


class WineCard(BaseModel):
    item_cd: str
    wine_name: str
    region: str
    country: str
    grape: str
    type_label_kr: str
    price_krw: int
    price_desc: str
    note: str
    persona_line: str
    pdata_id: str | None
    taste: WineTaste
