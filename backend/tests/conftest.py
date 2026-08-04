import pytest

from app.services.region_cache import CountryRegions, RegionCount, region_cache


@pytest.fixture(autouse=True)
def _seed_region_cache():
    region_cache._order = [
        CountryRegions(country="France", sku_count=10, regions=[RegionCount(label="부르고뉴", sku_count=10)])
    ]
    region_cache._fetched_at = 10**12  # 아주 먼 미래 타임스탬프로 TTL 만료 방지
    yield
    region_cache._order = []
    region_cache._fetched_at = 0.0
