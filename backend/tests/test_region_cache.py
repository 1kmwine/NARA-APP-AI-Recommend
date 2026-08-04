from app.services.region_cache import CountryRegions, build_region_order


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
