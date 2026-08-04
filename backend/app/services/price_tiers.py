PRICE_TIERS: list[tuple[str, int, int | None]] = [
    ("1만원 이하", 0, 10_000),
    ("2만원대", 10_001, 20_000),
    ("3만원대", 20_001, 30_000),
    ("5만원대", 30_001, 50_000),
    ("7만원대", 50_001, 70_000),
    ("10만원대", 70_001, 100_000),
    ("30만원대", 100_001, 300_000),
    ("100만원대", 300_001, 1_000_000),
    ("1000만원대", 1_000_001, 10_000_000),
    ("1000만원 이상", 10_000_001, None),
]


def tier_bounds(tier_index: int) -> tuple[int, int | None]:
    _, low, high = PRICE_TIERS[tier_index]
    return (low, high)


def tier_label(tier_index: int) -> str:
    label, _, _ = PRICE_TIERS[tier_index]
    return label


def widen_tier_ranges(tier_index: int) -> list[tuple[int, int | None]]:
    """정확한 티어부터 시작해서 점점 폭을 넓혀가며 (min, max) 범위를 반환한다.
    10단계라 정확한 티어에 SKU가 없는 경우가 흔해서, 호출 측이 순서대로 검색하다가
    결과가 나오면 멈추는 폴백에 쓴다."""
    n = len(PRICE_TIERS)
    ranges: list[tuple[int, int | None]] = [tier_bounds(tier_index)]
    widen = 1
    while True:
        lo_idx = max(0, tier_index - widen)
        hi_idx = min(n - 1, tier_index + widen)
        lo, _ = tier_bounds(lo_idx)
        _, hi = tier_bounds(hi_idx)
        candidate = (lo, hi)
        if candidate != ranges[-1]:
            ranges.append(candidate)
        if lo_idx == 0 and hi_idx == n - 1:
            break
        widen += 1
    return ranges
