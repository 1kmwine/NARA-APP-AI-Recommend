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


class BracketCard(WineCard):
    axis_label: str


class BracketMatch(BaseModel):
    round: str
    axis: str
    cards: list[BracketCard]


class BracketResponse(BaseModel):
    matches: list[BracketMatch]
