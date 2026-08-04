from etl.sync_price import compute_price


def test_compute_price_prefers_tb_product_original_price():
    result = compute_price(
        tb_product_row={"price__original": 45000},
        daily_sales=[{"sale__amt": 40000, "sales_qty": 1}],
    )
    assert result == (45000, "tb_product")


def test_compute_price_falls_back_to_daily_sale_average():
    result = compute_price(
        tb_product_row=None,
        daily_sales=[
            {"sale__amt": 90000, "sales_qty": 2},
            {"sale__amt": 30000, "sales_qty": 1},
        ],
    )
    assert result == (40000, "v_daily_sale_calc")


def test_compute_price_ignores_zero_or_null_tb_product_price():
    result = compute_price(
        tb_product_row={"price__original": 0},
        daily_sales=[{"sale__amt": 20000, "sales_qty": 1}],
    )
    assert result == (20000, "v_daily_sale_calc")


def test_compute_price_returns_none_when_no_data():
    assert compute_price(tb_product_row=None, daily_sales=[]) is None


def test_compute_price_returns_none_when_daily_sale_qty_is_zero():
    result = compute_price(
        tb_product_row=None,
        daily_sales=[{"sale__amt": 10000, "sales_qty": 0}],
    )
    assert result is None


def test_compute_price_rejects_negative_price_from_net_negative_sales():
    result = compute_price(
        tb_product_row=None,
        daily_sales=[
            {"sale__amt": 250000, "sales_qty": 5},
            {"sale__amt": -300000, "sales_qty": -4},
        ],
    )
    assert result is None


def test_compute_price_handles_none_amounts_without_crashing():
    result = compute_price(
        tb_product_row=None,
        daily_sales=[{"sale__amt": None, "sales_qty": None}, {"sale__amt": 20000, "sales_qty": 1}],
    )
    assert result == (20000, "v_daily_sale_calc")
