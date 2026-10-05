"""Structured lane of the hybrid ingestion (DECISIONS D40): CSV feeds -> staging/extracted/tab_<feed>.jsonl.

Deterministic mappers, no inference: each CSV row becomes the entities and relationships it states.
`make stage`.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator

import pandas as pd

from codegen.loader import ROOT
from pipeline.staging import EXTRACTED, entity, rel, source, write_jsonl

TAB = ROOT / "data" / "synthetic" / "tabular"

# feed -> source system that would export it in a real landscape
SYSTEMS = {
    "masters": "synthetic_mdm", "promotions": "synthetic_tpm", "orders": "synthetic_erp",
    "sell_out": "synthetic_dms", "inventory": "synthetic_dms", "forecasts": "synthetic_aps",
    "availability": "synthetic_retail_audit", "purchases": "synthetic_panel", "finance": "synthetic_erp",
}


def _rows(name: str) -> Iterator[tuple[int, dict]]:
    df = pd.read_csv(TAB / f"{name}.csv", dtype=str, keep_default_na=False)
    for i, r in enumerate(df.to_dict("records"), start=2):  # row 1 is the header
        yield i, r


def _src(feed: str, csv: str, row: int, record_id: str) -> dict:
    return source(SYSTEMS[feed], record_id, f"data/synthetic/tabular/{csv}.csv#row={row}")


def _num(v: str):
    return float(v) if v not in ("", None) else None


def masters() -> Iterator[dict]:
    f = "masters"
    yield entity("Currency", "INR", "Indian rupee", source(SYSTEMS[f], "INR", "data/synthetic/tabular"), iso_code="INR")
    for i, r in _rows("brands"):
        s = _src(f, "brands", i, r["brand_code"])
        yield entity("Brand", r["brand_code"], r["name"], s, description=r["description"], owner="Aurora Consumer Goods")
    for i, r in _rows("categories"):
        yield entity("Category", r["category_code"], r["name"], _src(f, "categories", i, r["category_code"]),
                     gpc_brick_code=r["gpc_brick_code"])
    for i, r in _rows("product_families"):
        s = _src(f, "product_families", i, r["family_code"])
        yield entity("ProductFamily", r["family_code"], r["name"], s)
        yield rel("ProductFamily", r["family_code"], "BELONGS_TO_BRAND", "Brand", r["brand_code"], s)
        yield rel("ProductFamily", r["family_code"], "BELONGS_TO_CATEGORY", "Category", r["category_code"], s)
    for i, r in _rows("pack_price_points"):
        yield entity("PackPricePoint", r["ppp_code"], r["name"], _src(f, "pack_price_points", i, r["ppp_code"]),
                     pack_size="various", price_point=_num(r["price_point"]), price_point_text=f"INR {r['price_point']}",
                     currency=r["currency"])
    for i, r in _rows("skus"):
        s = _src(f, "skus", i, r["sku_code"])
        yield entity("SKU", r["sku_code"], r["name"], s, pack_size=r["pack_size"], unit_of_measure=r["unit_of_measure"])
        yield rel("SKU", r["sku_code"], "BELONGS_TO", "ProductFamily", r["family_code"], s)
        yield rel("SKU", r["sku_code"], "PRICED_AT", "PackPricePoint", f"PPP-{r['price_point']}", s)
    for i, r in _rows("geographies"):
        s = _src(f, "geographies", i, r["geo_code"])
        yield entity("Geography", r["geo_code"], r["name"], s, geography_level=r["geography_level"])
        if r["parent_code"]:
            yield rel("Geography", r["geo_code"], "PART_OF", "Geography", r["parent_code"], s)
    for i, r in _rows("channels"):
        yield entity("Channel", r["channel_code"], r["name"], _src(f, "channels", i, r["channel_code"]),
                     channel_type=r["channel_type"])
    for i, r in _rows("distributors"):
        s = _src(f, "distributors", i, r["code"])
        yield entity("Distributor", r["code"], r["name"], s, distributor_type=r["distributor_type"])
        yield rel("Distributor", r["code"], "OPERATES_IN", "Geography", r["micro_market"], s)
    for i, r in _rows("retailers"):
        yield entity("Retailer", r["code"], r["name"], _src(f, "retailers", i, r["code"]), retailer_type=r["retailer_type"])
    for i, r in _rows("customers"):
        s = _src(f, "customers", i, r["customer_code"])
        yield entity("Customer", r["customer_code"], r["name"], s, customer_type=r["customer_type"],
                     credit_class=r["credit_class"])
        yield rel("Customer", r["customer_code"], "ACCOUNT_OF", r["partner_class"], r["partner_code"], s)
        yield rel("Customer", r["customer_code"], "OPERATES_IN", "Geography", r["geo_code"], s)
    for i, r in _rows("outlets"):
        s = _src(f, "outlets", i, r["outlet_code"])
        yield entity("Outlet", r["outlet_code"], r["name"], s, outlet_type=r["outlet_type"], outlet_class=r["outlet_class"])
        yield rel("Outlet", r["outlet_code"], "LOCATED_IN", "Geography", r["geo_code"], s)
        yield rel("Outlet", r["outlet_code"], "BELONGS_TO", "Channel", r["channel_code"], s)
    for i, r in _rows("serves"):
        yield rel("Distributor", r["distributor_code"], "SERVES", "Outlet", r["outlet_code"],
                  _src(f, "serves", i, f"{r['distributor_code']}-{r['outlet_code']}"))
    for i, r in _rows("outlet_skus"):
        yield rel("Outlet", r["outlet_code"], "STOCKS", "SKU", r["sku_code"],
                  _src(f, "outlet_skus", i, f"{r['outlet_code']}-{r['sku_code']}"))
    for i, r in _rows("consumer_segments"):
        yield entity("ConsumerSegment", r["segment_code"], r["name"], _src(f, "consumer_segments", i, r["segment_code"]),
                     segment_basis=r["segment_basis"])
    for i, r in _rows("need_states"):
        yield entity("NeedState", r["need_code"], r["name"], _src(f, "need_states", i, r["need_code"]))
    for i, r in _rows("segment_needs"):
        yield rel("ConsumerSegment", r["segment_code"], "HAS", "NeedState", r["need_code"],
                  _src(f, "segment_needs", i, f"{r['segment_code']}-{r['need_code']}"))
    for i, r in _rows("fiscal_periods"):
        yield entity("FiscalPeriod", r["period_code"], r["name"], _src(f, "fiscal_periods", i, r["period_code"]),
                     start_date=r["start_date"], end_date=r["end_date"], fiscal_year=r["fiscal_year"])


def promotions() -> Iterator[dict]:
    f = "promotions"
    for i, r in _rows("promotions"):
        s = _src(f, "promotions", i, r["promotion_code"])
        yield entity("TradePromotion", r["promotion_code"], r["name"], s, promotion_type=r["promotion_type"],
                     start_date=r["start_date"], end_date=r["end_date"], status=r["status"])
        yield rel("TradePromotion", r["promotion_code"], "BELONGS_TO", "Brand", r["brand_code"], s)
        yield rel("TradePromotion", r["promotion_code"], "EXECUTED_IN", "Channel", r["channel_code"], s)
        yield rel("TradePromotion", r["promotion_code"], "VALID_IN", "Geography", r["geo_code"], s)
        yield rel("TradePromotion", r["promotion_code"], "VALID_DURING", "FiscalPeriod", r["fiscal_period"], s)
    for i, r in _rows("promotion_targets"):
        yield rel("TradePromotion", r["promotion_code"], "TARGETS", "Customer", r["customer_code"],
                  _src(f, "promotion_targets", i, f"{r['promotion_code']}-{r['customer_code']}"))
    for i, r in _rows("promotion_skus"):
        yield rel("TradePromotion", r["promotion_code"], "APPLIES_TO", "SKU", r["sku_code"],
                  _src(f, "promotion_skus", i, f"{r['promotion_code']}-{r['sku_code']}"))


def orders() -> Iterator[dict]:
    f = "orders"
    for i, r in _rows("sales_orders"):
        s = _src(f, "sales_orders", i, r["order_code"])
        yield entity("SalesOrder", r["order_code"], r["order_code"], s, order_date=r["order_date"], status=r["status"])
        yield rel("SalesOrder", r["order_code"], "PLACED_BY", "Customer", r["customer_code"], s)
        yield rel("SalesOrder", r["order_code"], "FULFILLED_THROUGH", "Channel", r["channel_code"], s)
    for i, r in _rows("invoices"):
        s = _src(f, "invoices", i, r["invoice_code"])
        yield entity("SalesInvoice", r["invoice_code"], r["invoice_code"], s, invoice_date=r["invoice_date"],
                     due_date=r["due_date"], amount=_num(r["amount"]), amount_text=f"{r['currency']} {r['amount']}",
                     currency=r["currency"], status=r["status"])
        yield rel("SalesInvoice", r["invoice_code"], "REFERENCES", "SalesOrder", r["order_code"], s)
        yield rel("SalesInvoice", r["invoice_code"], "ISSUED_TO", "Customer", r["customer_code"], s)
        yield rel("SalesInvoice", r["invoice_code"], "OCCURRED_DURING", "FiscalPeriod", r["fiscal_period"], s)
        yield rel("SalesInvoice", r["invoice_code"], "DENOMINATED_IN", "Currency", r["currency"], s)
    for i, r in _rows("invoice_lines"):
        s = _src(f, "invoice_lines", i, r["invoice_line_code"])
        yield entity("InvoiceLine", r["invoice_line_code"], r["invoice_line_code"], s, quantity=_num(r["quantity"]),
                     unit=r["unit"], unit_price=_num(r["unit_price"]), unit_price_text=r["unit_price"],
                     line_amount=_num(r["line_amount"]), line_amount_text=r["line_amount"])
        yield rel("SalesInvoice", r["invoice_code"], "CONTAINS", "InvoiceLine", r["invoice_line_code"], s)
        yield rel("InvoiceLine", r["invoice_line_code"], "REFERENCES", "SKU", r["sku_code"], s)


def sell_out() -> Iterator[dict]:
    for i, r in _rows("sell_out"):
        code = f"SO-{r['outlet_code']}-{r['sku_code']}-W{int(r['week']):02d}"
        s = _src("sell_out", "sell_out", i, code)
        yield entity("SellOutTransaction", code, f"{r['sku_code']} at {r['outlet_code']} week {r['week']}", s,
                     week_start=r["week_start"], quantity=_num(r["quantity"]), unit=r["unit"],
                     sales_value=_num(r["sales_value"]), sales_value_text=f"{r['currency']} {r['sales_value']}",
                     currency=r["currency"])
        yield rel("SellOutTransaction", code, "OCCURS_AT", "Outlet", r["outlet_code"], s)
        yield rel("SellOutTransaction", code, "REFERENCES", "SKU", r["sku_code"], s)


def inventory() -> Iterator[dict]:
    for i, r in _rows("inventory"):
        code = f"IP-{r['distributor_code']}-{r['sku_code']}-{r['as_of_date']}"
        s = _src("inventory", "inventory", i, code)
        yield entity("InventoryPosition", code, f"{r['sku_code']} stock at {r['distributor_code']} {r['as_of_date']}", s,
                     as_of_date=r["as_of_date"], quantity=_num(r["quantity"]), unit=r["unit"],
                     days_of_cover=_num(r["days_of_cover"]))
        yield rel("InventoryPosition", code, "MEASURED_FOR", "SKU", r["sku_code"], s)
        yield rel("InventoryPosition", code, "HELD_AT", "Distributor", r["distributor_code"], s)


def forecasts() -> Iterator[dict]:
    for i, r in _rows("forecasts"):
        s = _src("forecasts", "forecasts", i, r["forecast_code"])
        yield entity("DemandForecast", r["forecast_code"], f"{r['forecast_type']} forecast {r['sku_code']} {r['geo_code']} {r['period']}",
                     s, period=r["period"], forecast_quantity=_num(r["forecast_quantity"]), unit=r["unit"],
                     forecast_type=r["forecast_type"], version=r["version"])
        yield rel("DemandForecast", r["forecast_code"], "FORECASTS", "SKU", r["sku_code"], s)
        yield rel("DemandForecast", r["forecast_code"], "FORECASTS", "Geography", r["geo_code"], s)
        if r["promotion_code"]:
            yield rel("TradePromotion", r["promotion_code"], "UPLIFTS", "DemandForecast", r["forecast_code"], s)


def availability() -> Iterator[dict]:
    for i, r in _rows("availability"):
        s = _src("availability", "availability", i, r["observation_code"])
        yield entity("AvailabilityObservation", r["observation_code"], f"OSA {r['sku_code']} at {r['outlet_code']}", s,
                     observation_date=r["observation_date"], on_shelf=r["on_shelf"] == "True", facings=int(r["facings"]))
        yield rel("AvailabilityObservation", r["observation_code"], "OBSERVED_AT", "Outlet", r["outlet_code"], s)
        yield rel("AvailabilityObservation", r["observation_code"], "MEASURES", "SKU", r["sku_code"], s)


def purchases() -> Iterator[dict]:
    for i, r in _rows("purchases"):
        s = _src("purchases", "purchases", i, r["purchase_code"])
        yield entity("PurchaseEvent", r["purchase_code"], f"Purchase {r['purchase_code']}", s,
                     purchase_date=r["purchase_date"], household_ref=r["household_ref"], quantity=_num(r["quantity"]),
                     spend=_num(r["spend"]), spend_text=f"{r['currency']} {r['spend']}", currency=r["currency"])
        yield rel("PurchaseEvent", r["purchase_code"], "OCCURS_AT", "Outlet", r["outlet_code"], s)
        yield rel("PurchaseEvent", r["purchase_code"], "CONTAINS", "SKU", r["sku_code"], s)
        yield rel("PurchaseEvent", r["purchase_code"], "MOTIVATED_BY", "NeedState", r["need_code"], s)


def finance() -> Iterator[dict]:
    for i, r in _rows("trade_spend"):
        s = _src("finance", "trade_spend", i, r["trade_spend_code"])
        yield entity("TradeSpend", r["trade_spend_code"], f"Trade spend {r['trade_spend_code']}", s,
                     spend_type=r["spend_type"], amount=_num(r["amount"]), amount_text=f"{r['currency']} {r['amount']}",
                     currency=r["currency"], period=r["period"])
        if r["promotion_code"]:
            yield rel("TradeSpend", r["trade_spend_code"], "INCURRED_FOR", "TradePromotion", r["promotion_code"], s)
        if r.get("sku_code"):
            yield rel("TradeSpend", r["trade_spend_code"], "INCURRED_FOR", "SKU", r["sku_code"], s)
    for i, r in _rows("margins"):
        s = _src("finance", "margins", i, r["margin_code"])
        yield entity("Margin", r["margin_code"], f"Gross margin {r['sku_code']} {r['period']}", s,
                     value=_num(r["value"]), value_text=f"{r['value']}%", unit=r["unit"], period=r["period"])
        yield rel("Margin", r["margin_code"], "MEASURED_FOR", "SKU", r["sku_code"], s)


FEEDS: dict[str, Callable[[], Iterator[dict]]] = {
    "masters": masters, "promotions": promotions, "orders": orders, "sell_out": sell_out, "inventory": inventory,
    "forecasts": forecasts, "availability": availability, "purchases": purchases, "finance": finance,
}


def run() -> None:
    if not TAB.exists():
        raise SystemExit("no synthetic data: run `make synth` first")
    for old in EXTRACTED.glob("tab_*.jsonl"):
        old.unlink()
    total = 0
    for name, fn in FEEDS.items():
        n = write_jsonl(EXTRACTED / f"tab_{name}.jsonl", fn())
        total += n
        print(f"stage: {name:<13} {n:>7} records")
    print(f"stage: {total} records -> {EXTRACTED.relative_to(ROOT).as_posix()}")
