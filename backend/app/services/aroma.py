from typing import Literal

# tb_pdata.aroma에 실제로 나오는 영어 태그(2026-08-06 샘플 확인) 기준 분류.
# 과일류(1차 향)는 fruit, 꽃/오크/숙성/향신료 등 2·3차 향은 floral_tertiary.
FRUIT_TAGS = {
    "blackcurrant", "blackberry", "raspberry", "strawberry", "cherry", "plum",
    "prune", "fig", "pineapple", "banana", "grapefruit", "orange peel", "peach",
    "apple", "lemon", "lime", "apricot", "melon", "grape", "citrus", "tropical fruit",
    "red fruit", "black fruit", "stone fruit",
}
FLORAL_TERTIARY_TAGS = {
    "violet", "rose", "jasmine", "vanilla", "leather", "tobacco", "mushroom",
    "cloves", "nutmeg", "cedar", "smoke", "toast", "chocolate", "coffee", "earth",
    "mineral", "herb", "pepper", "licorice", "liquorice", "honey", "butter",
    "oak", "truffle", "game", "forest floor", "wet stone",
}

Aroma = Literal["fruit", "floral_tertiary"]


def classify_aroma_tags(tags: list[str]) -> Aroma:
    """아로마 태그 목록을 과일향/꽃·2,3차향 둘 중 하나로 분류한다.
    알려진 태그 수를 세어 많은 쪽으로 정하고, 동점이거나 알려진 태그가 없으면
    "fruit"으로 기본값을 준다(결정적 동작이 필요해서 임의 우선순위를 둠)."""
    fruit_count = 0
    floral_count = 0
    for tag in tags:
        normalized = tag.strip().lower()
        if normalized in FRUIT_TAGS:
            fruit_count += 1
        elif normalized in FLORAL_TERTIARY_TAGS:
            floral_count += 1
    if floral_count > fruit_count:
        return "floral_tertiary"
    return "fruit"
