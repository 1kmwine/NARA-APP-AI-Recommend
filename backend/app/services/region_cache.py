import time
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.region_overrides import (
    extract_raw_region,
    normalize_region_label,
    region_to_country,
)

TTL_SECONDS = 3600


@dataclass
class RegionCount:
    label: str
    sku_count: int


@dataclass
class CountryRegions:
    country: str
    sku_count: int
    regions: list[RegionCount] = field(default_factory=list)


def build_region_order(rows: list[tuple[str | None, str | None]]) -> list[CountryRegions]:
    """(place_json, country_name) 행 리스트로부터 국가별/지역별 SKU 개수 집계 후
    국가는 총 SKU 개수 내림차순, 국가 내 지역도 SKU 개수 내림차순으로 정렬."""
    counts: Counter[tuple[str, str]] = Counter()
    for place_json, country_name in rows:
        raw_region = extract_raw_region(place_json)
        label = normalize_region_label(raw_region) if raw_region else "기타"
        country = region_to_country(raw_region) or country_name or "기타"
        counts[(country, label)] += 1

    country_totals: Counter[str] = Counter()
    by_country: dict[str, Counter[str]] = {}
    for (country, label), n in counts.items():
        country_totals[country] += n
        by_country.setdefault(country, Counter())[label] += n

    result: list[CountryRegions] = []
    for country, total in country_totals.most_common():
        regions = [
            RegionCount(label=label, sku_count=n)
            for label, n in by_country[country].most_common()
        ]
        result.append(CountryRegions(country=country, sku_count=total, regions=regions))
    return result


class RegionCache:
    def __init__(self) -> None:
        self._order: list[CountryRegions] = []
        self._fetched_at: float = 0.0

    def get(self, session: Session) -> list[CountryRegions]:
        now = time.time()
        if not self._order or now - self._fetched_at > TTL_SECONDS:
            rows = session.execute(
                text("SELECT place, countryName FROM wine_info.integrated_item_info")
            ).all()
            self._order = build_region_order([(r[0], r[1]) for r in rows])
            self._fetched_at = now
        return self._order


region_cache = RegionCache()
