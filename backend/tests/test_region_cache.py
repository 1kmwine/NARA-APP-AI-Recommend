from unittest.mock import MagicMock

from app.services.region_cache import CountryRegions, RegionCache, build_region_order


def test_build_region_order_counts_and_sorts_by_sku_count_desc():
    rows = [
        ('{"ko": "부르고뉴"}', "France"),
        ('{"ko": "부르고뉴"}', "France"),
        ('{"ko": "부르고뉴"}', "France"),
        ('{"ko": "보르도"}', "France"),
        ('{"ko": "보르도"}', "France"),
        ('{"ko": "나파밸리"}', "USA"),
        ('{"ko": "나파밸리"}', "USA"),
        ('{"ko": "라펠 밸리"}', "Chile"),
    ]
    order = build_region_order(rows)

    assert [c.country for c in order] == ["France", "USA", "Chile"]
    france = order[0]
    assert [r.label for r in france.regions] == ["부르고뉴", "보르도"]
    assert france.regions[0].sku_count == 3
    assert france.regions[1].sku_count == 2


def test_build_region_order_uses_row_country_when_region_unmapped():
    rows = [('{"ko": "존재안함지역"}', "Georgia")]
    order = build_region_order(rows)
    assert order[0].country == "Georgia"


def test_build_region_order_falls_back_to_기타_when_nothing_known():
    rows = [(None, None)]
    order = build_region_order(rows)
    assert order[0].country == "기타"


def _fake_session(rows: list[tuple[str | None, str | None]]) -> MagicMock:
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    return session


def test_region_cache_populates_on_first_call():
    cache = RegionCache()
    session = _fake_session([('{"ko": "부르고뉴"}', "France")])
    order = cache.get(session)
    assert order[0].country == "France"
    session.execute.assert_called_once()


def test_region_cache_skips_db_on_second_call_within_ttl():
    cache = RegionCache()
    session = _fake_session([('{"ko": "부르고뉴"}', "France")])
    cache.get(session)
    cache.get(session)
    session.execute.assert_called_once()


def test_region_cache_does_not_get_stuck_reQuerying_after_empty_result():
    cache = RegionCache()
    session = _fake_session([])
    cache.get(session)
    cache.get(session)
    # 두 번째 호출도 TTL 안이므로 DB를 다시 안 불러야 함 — 빈 결과라도 캐시가 "채워졌다"고 봐야 함
    session.execute.assert_called_once()
