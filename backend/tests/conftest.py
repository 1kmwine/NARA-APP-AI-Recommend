import pytest

from app.services.region_cache import CountryRegions, RegionCount, region_cache

_SEEDED_ORDER = [
    CountryRegions(country="France", sku_count=10, regions=[RegionCount(label="부르고뉴", sku_count=10)])
]


@pytest.fixture(autouse=True)
def _seed_region_cache():
    # RegionCache는 wine_type별로 따로 캐싱한다(app/services/region_cache.py) — 어떤
    # wine_type으로 조회해도 실DB를 안 타도록 None과 테스트에서 실제 쓰는 값들을 미리
    # 채워둔다. 새 wine_type이 테스트에 추가되면 여기도 같이 추가해야 함.
    far_future = 10**12  # TTL 만료 방지
    for wine_type in (None, "Red", "White", "Sparkling"):
        region_cache._cache[wine_type] = (_SEEDED_ORDER, far_future)
    yield
    region_cache._cache = {}
