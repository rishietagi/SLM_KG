"""Seeded synthetic CPG dataset for a fictional company (PROJECT_CONTEXT §9). `make synth`.

Writes data/synthetic/tabular/*.csv (structured feeds), data/synthetic/documents/*.md (narrative
documents for LLM extraction) and data/synthetic/truth.json (planted answers for competency tests).

Planted patterns:
  1. TP2026-003 loads micro-market-B distributors (primary +80%) without outlet sell-through (CQ6).
  2. TP2026-005 is healthy: primary and sell-out both rise.
  3. TP2026-005 claims: one partly approved (620,000 -> 510,000), one rejected, one approved but unsettled (CQ7).
  4. Low on-shelf availability for TP2026-004 SKUs in micro-market C (CQ8, Phase 3).
  5. BW-LIQ-1L margin declines while its trade spend rises (CQ9, Phase 3).
All names are fictional.
"""
from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
HERE = Path(__file__).parent
TAB = HERE / "tabular"
DOCS = HERE / "documents"
START = date(2026, 4, 6)  # Monday, FY26 week 1 (April-March fiscal year)
WEEKS = 26
CURRENCY = "INR"

rng = np.random.default_rng(SEED)


def week_start(w: int) -> date:  # w is 1-based
    return START + timedelta(weeks=w - 1)


def fiscal_quarter(d: date) -> str:
    return "FY26-Q1" if d < date(2026, 7, 6) else "FY26-Q2"


# ------------------------------------------------------------------ masters
BRANDS = [("BW", "Brightwash", "Home care detergents and dishwash"), ("SN", "Sunnymeal", "Breakfast cereals")]
CATEGORIES = [("LAUNDRY", "Laundry detergent", "10000203"), ("DISH", "Dishwash", "10000204"),
              ("BFAST", "Breakfast cereal", "10000280")]
FAMILIES = [  # id, name, brand, category
    ("BW-PWD", "Brightwash Powder", "BW", "LAUNDRY"), ("BW-LIQ", "Brightwash Liquid", "BW", "LAUNDRY"),
    ("BW-DSH", "Brightwash Dish Gel", "BW", "DISH"), ("SN-OAT", "Sunnymeal Oats", "SN", "BFAST"),
    ("SN-FLK", "Sunnymeal Flakes", "SN", "BFAST"),
]
SIZES = {  # family -> [(size code, pack size, price INR, base weekly units per outlet)]
    "BW-PWD": [("500G", "500 g", 55, 6), ("1KG", "1 kg", 99, 9), ("2KG", "2 kg", 189, 4), ("4KG", "4 kg", 359, 2),
               ("6KG", "6 kg", 520, 1), ("SACHET", "80 g sachet", 10, 20)],
    "BW-LIQ": [("500ML", "500 ml", 99, 4), ("1L", "1 l", 189, 5), ("2L", "2 l", 349, 2), ("POUCH", "200 ml pouch", 20, 10),
               ("3L", "3 l", 499, 1), ("REFILL", "1 l refill", 169, 2)],
    "BW-DSH": [("250ML", "250 ml", 55, 6), ("500ML", "500 ml", 99, 5), ("750ML", "750 ml", 139, 3),
               ("BAR", "200 g bar", 20, 12), ("SACHET", "20 ml sachet", 5, 15), ("1L", "1 l refill", 169, 2)],
    "SN-OAT": [("400G", "400 g", 99, 4), ("1KG", "1 kg", 199, 3), ("CUP", "40 g cup", 20, 8), ("MASALA", "500 g masala", 120, 3),
               ("200G", "200 g", 55, 5), ("2KG", "2 kg", 379, 1)],
    "SN-FLK": [("250G", "250 g", 99, 4), ("475G", "475 g", 179, 3), ("1KG", "1 kg", 329, 1), ("HONEY", "300 g honey", 149, 3),
               ("30G", "30 g pack", 10, 9), ("CHOCO", "350 g choco", 169, 2)],
}
PRICE_POINTS = sorted({p for sizes in SIZES.values() for _, _, p, _ in sizes})

GEOS = [("IN", "India", "country", None), ("WEST", "West region", "region", "IN"), ("PUNE", "Pune", "city", "WEST"),
        ("MM-A", "Pune Central", "micro_market", "PUNE"), ("MM-B", "Pune East", "micro_market", "PUNE"),
        ("MM-C", "Pune West", "micro_market", "PUNE")]
MICRO = ["MM-A", "MM-B", "MM-C"]
CHANNELS = [("GT", "General trade", "traditional"), ("MT", "Modern trade", "organised_retail"),
            ("QC", "Quick commerce", "digital")]
DISTRIBUTORS = {  # code -> micro-market
    "D101": "MM-A", "D102": "MM-A", "D103": "MM-A", "D104": "MM-B", "D105": "MM-B", "D106": "MM-B",
    "D107": "MM-C", "D108": "MM-C", "D109": "MM-C", "D110": "MM-B",
}
DIST_NAMES = {"D101": "Shree Ganesh Traders", "D102": "Kothrud Distributors", "D103": "Deccan Agencies",
              "D104": "Hadapsar Sales Corp", "D105": "Kharadi Supply Co", "D106": "Viman Nagar Traders",
              "D107": "Baner Distribution", "D108": "Aundh Wholesale", "D109": "Pashan Agencies",
              "D110": "Wagholi Enterprises"}
RETAILERS = [("MT01", "Metro Mart", "modern_trade_chain", "MT"), ("QC01", "ZipCart", "quick_commerce", "QC")]
SEGMENTS = [("SEG-VAL", "Value-seeking families", "income band"), ("SEG-URB", "Urban young professionals", "life stage"),
            ("SEG-PRM", "Premium health-conscious", "attitude")]
NEEDS = [("NS-STAIN", "Tough stain removal"), ("NS-VALUE", "Value stock-up"), ("NS-QUICK", "Quick breakfast"),
         ("NS-HEALTH", "Healthy start"), ("NS-GENTLE", "Gentle on hands")]
SEGMENT_NEEDS = [("SEG-VAL", "NS-VALUE"), ("SEG-VAL", "NS-STAIN"), ("SEG-URB", "NS-QUICK"), ("SEG-URB", "NS-GENTLE"),
                 ("SEG-PRM", "NS-HEALTH"), ("SEG-PRM", "NS-QUICK")]
FAMILY_NEEDS = {"BW-PWD": ["NS-STAIN", "NS-VALUE"], "BW-LIQ": ["NS-STAIN"], "BW-DSH": ["NS-GENTLE"],
                "SN-OAT": ["NS-HEALTH", "NS-QUICK"], "SN-FLK": ["NS-QUICK"]}

# Promotions (TPM export). scope: distributor codes / retailer codes the promotion targets.
PROMOS = [
    dict(id="TP2026-001", name="Brightwash Powder 1kg Buy 4 Get 1", brand="BW", skus=["BW-PWD-1KG"],
         channel="GT", geo="MM-A", targets=["D101", "D102", "D103"], weeks=(5, 8), mechanic="free goods",
         budget=900_000, ptype="consumer_offer", primary_uplift=0.35, sellout_uplift=0.30),
    dict(id="TP2026-002", name="Sunnymeal Oats Modern Trade Price-Off", brand="SN", skus=["SN-OAT-400G", "SN-OAT-1KG"],
         channel="MT", geo="PUNE", targets=["MT01"], weeks=(6, 9), mechanic="price discount",
         budget=650_000, ptype="price_promotion", primary_uplift=0.30, sellout_uplift=0.28),
    dict(id="TP2026-003", name="Brightwash Liquid Volume Incentive East", brand="BW", skus=["BW-LIQ-1L", "BW-LIQ-2L"],
         channel="GT", geo="MM-B", targets=["D104", "D105", "D106"], weeks=(10, 13), mechanic="volume incentive",
         budget=1_200_000, ptype="trade_incentive", primary_uplift=0.80, sellout_uplift=0.0),
    dict(id="TP2026-004", name="Brightwash Dish Gel Display Drive West", brand="BW", skus=["BW-DSH-500ML", "BW-DSH-750ML"],
         channel="GT", geo="MM-C", targets=["D107", "D108", "D109"], weeks=(12, 15), mechanic="display allowance",
         budget=500_000, ptype="display", primary_uplift=0.25, sellout_uplift=0.08),
    dict(id="TP2026-005", name="Brightwash Powder Monsoon Rebate", brand="BW", skus=["BW-PWD-1KG", "BW-PWD-2KG"],
         channel="GT", geo="PUNE", targets=["D101", "D103", "D107", "D108"], weeks=(16, 19), mechanic="rebate",
         budget=1_500_000, ptype="trade_rebate", primary_uplift=0.45, sellout_uplift=0.40),
    dict(id="TP2026-006", name="Sunnymeal Flakes Quick Commerce Bundle", brand="SN", skus=["SN-FLK-475G", "SN-FLK-HONEY"],
         channel="QC", geo="PUNE", targets=["QC01"], weeks=(20, 23), mechanic="bundle",
         budget=400_000, ptype="consumer_offer", primary_uplift=0.30, sellout_uplift=0.32),
]


def build():
    shutil.rmtree(TAB, ignore_errors=True)
    shutil.rmtree(DOCS, ignore_errors=True)
    TAB.mkdir(parents=True)
    DOCS.mkdir(parents=True)
    out: dict[str, pd.DataFrame] = {}

    out["brands"] = pd.DataFrame(BRANDS, columns=["brand_code", "name", "description"])
    out["categories"] = pd.DataFrame(CATEGORIES, columns=["category_code", "name", "gpc_brick_code"])
    out["product_families"] = pd.DataFrame(FAMILIES, columns=["family_code", "name", "brand_code", "category_code"])
    skus = []
    for fam, sizes in SIZES.items():
        fname = next(f[1] for f in FAMILIES if f[0] == fam)
        for code, pack, price, base in sizes:
            skus.append(dict(sku_code=f"{fam}-{code}", name=f"{fname} {pack}", family_code=fam, pack_size=pack,
                             unit_of_measure="unit", price_point=price, base_weekly_units=base))
    sku_df = pd.DataFrame(skus)
    out["skus"] = sku_df.drop(columns=["base_weekly_units"])
    out["pack_price_points"] = pd.DataFrame(
        [dict(ppp_code=f"PPP-{p}", name=f"INR {p} price point", price_point=p, currency=CURRENCY) for p in PRICE_POINTS])
    out["geographies"] = pd.DataFrame(GEOS, columns=["geo_code", "name", "geography_level", "parent_code"])
    out["channels"] = pd.DataFrame(CHANNELS, columns=["channel_code", "name", "channel_type"])
    out["distributors"] = pd.DataFrame(
        [dict(code=c, name=DIST_NAMES[c], distributor_type="distributor", micro_market=m) for c, m in DISTRIBUTORS.items()])
    out["retailers"] = pd.DataFrame(RETAILERS, columns=["code", "name", "retailer_type", "channel_code"])
    customers = [dict(customer_code=c, name=DIST_NAMES[c], customer_type="distributor", credit_class="B",
                      partner_class="Distributor", partner_code=c, geo_code=m) for c, m in DISTRIBUTORS.items()]
    customers += [dict(customer_code=c, name=n, customer_type=t, credit_class="A", partner_class="Retailer",
                       partner_code=c, geo_code="PUNE") for c, n, t, _ in RETAILERS]
    out["customers"] = pd.DataFrame(customers)
    out["consumer_segments"] = pd.DataFrame(SEGMENTS, columns=["segment_code", "name", "segment_basis"])
    out["need_states"] = pd.DataFrame(NEEDS, columns=["need_code", "name"])
    out["segment_needs"] = pd.DataFrame(SEGMENT_NEEDS, columns=["segment_code", "need_code"])
    out["fiscal_periods"] = pd.DataFrame([
        dict(period_code="FY26-Q1", name="FY26 Q1", start_date="2026-04-01", end_date="2026-06-30", fiscal_year="FY26"),
        dict(period_code="FY26-Q2", name="FY26 Q2", start_date="2026-07-01", end_date="2026-09-30", fiscal_year="FY26")])

    # outlets: 170 GT across distributors, 20 MT stores, 10 QC dark stores
    outlets, serves = [], []
    n = 0
    gt_per_dist = {c: 17 for c in DISTRIBUTORS}
    for dist, mm in DISTRIBUTORS.items():
        for _ in range(gt_per_dist[dist]):
            n += 1
            oc = f"OUT-{n:04d}"
            outlets.append(dict(outlet_code=oc, name=f"{rng.choice(['Sai', 'Om', 'Laxmi', 'New', 'Star', 'City'])} "
                                f"{rng.choice(['Kirana', 'General Stores', 'Provisions', 'Mart', 'Chemist'])} {n}",
                                outlet_type=str(rng.choice(["kirana", "kirana", "general_store", "chemist"])),
                                outlet_class=str(rng.choice(["A", "B", "B", "C", "C"])), channel_code="GT",
                                geo_code=mm, distributor_code=dist))
            serves.append(dict(distributor_code=dist, outlet_code=oc))
    for code, cnt, typ, ch in (("MT01", 20, "supermarket", "MT"), ("QC01", 10, "dark_store", "QC")):
        for i in range(cnt):
            n += 1
            outlets.append(dict(outlet_code=f"OUT-{n:04d}", name=f"{'Metro Mart' if ch == 'MT' else 'ZipCart'} "
                                f"{['Central', 'East', 'West'][i % 3]} #{i + 1}", outlet_type=typ, outlet_class="A",
                                channel_code=ch, geo_code=MICRO[i % 3], distributor_code=""))
    out_df = pd.DataFrame(outlets)
    out["outlets"] = out_df
    out["serves"] = pd.DataFrame(serves)

    # assortment: each outlet stocks 9-14 SKUs; promoted SKUs are stocked where promotions run
    sku_codes = sku_df.sku_code.tolist()
    stocks = []
    for o in outlets:
        k = int(rng.integers(9, 15))
        chosen = set(rng.choice(sku_codes, size=k, replace=False))
        for p in PROMOS:
            if _outlet_in_scope(o, p):
                chosen |= set(p["skus"])
        stocks += [dict(outlet_code=o["outlet_code"], sku_code=s) for s in sorted(chosen)]
    out["outlet_skus"] = pd.DataFrame(stocks)

    # promotions (TPM export)
    out["promotions"] = pd.DataFrame([dict(
        promotion_code=p["id"], name=p["name"], promotion_type=p["ptype"], brand_code=p["brand"], channel_code=p["channel"],
        geo_code=p["geo"], start_date=str(week_start(p["weeks"][0])), end_date=str(week_start(p["weeks"][1]) + timedelta(days=6)),
        status="closed", fiscal_period=fiscal_quarter(week_start(p["weeks"][0]))) for p in PROMOS])
    out["promotion_targets"] = pd.DataFrame([dict(promotion_code=p["id"], customer_code=t) for p in PROMOS for t in p["targets"]])
    out["promotion_skus"] = pd.DataFrame([dict(promotion_code=p["id"], sku_code=s) for p in PROMOS for s in p["skus"]])

    # ---------------------------------------------------------- weekly sell-out
    base = dict(zip(sku_df.sku_code, sku_df.base_weekly_units))
    price = dict(zip(sku_df.sku_code, sku_df.price_point))
    cls_mult = {"A": 1.6, "B": 1.0, "C": 0.6}
    stocks_by_outlet: dict[str, list[str]] = {}
    for s in stocks:
        stocks_by_outlet.setdefault(s["outlet_code"], []).append(s["sku_code"])
    sell = []
    for o in outlets:
        mult = cls_mult[o["outlet_class"]] * (3.0 if o["channel_code"] == "MT" else 2.0 if o["channel_code"] == "QC" else 1.0)
        for s in stocks_by_outlet[o["outlet_code"]]:
            for w in range(1, WEEKS + 1):
                lam = base[s] * mult * _uplift(o, s, w, "sellout_uplift")
                q = int(rng.poisson(lam))
                if q:
                    sell.append(dict(outlet_code=o["outlet_code"], sku_code=s, week=w, week_start=str(week_start(w)),
                                     quantity=q, unit="unit", sales_value=q * price[s], currency=CURRENCY))
    sell_df = pd.DataFrame(sell)
    out["sell_out"] = sell_df

    # ---------------------------------------------------------- primary invoices (weekly per account)
    acct_outlets = {c: [o["outlet_code"] for o in outlets if o["distributor_code"] == c] for c in DISTRIBUTORS}
    acct_outlets["MT01"] = [o["outlet_code"] for o in outlets if o["channel_code"] == "MT"]
    acct_outlets["QC01"] = [o["outlet_code"] for o in outlets if o["channel_code"] == "QC"]
    expected = sell_df.groupby(["outlet_code", "sku_code"]).quantity.mean().to_dict()
    orders, invoices, lines, inventory = [], [], [], []
    for acct, ols in acct_outlets.items():
        acct_skus = sorted({s for oc in ols for s in stocks_by_outlet[oc]})
        stock = {s: 0.0 for s in acct_skus}
        for w in range(1, WEEKS + 1):
            ws = week_start(w)
            inv_code = f"INV-{acct}-W{w:02d}"
            so_code = f"SO-{acct}-W{w:02d}"
            total, ln = 0.0, 0
            for s in acct_skus:
                need = sum(expected.get((oc, s), 0) for oc in ols)
                up = max((1 + p["primary_uplift"] for p in PROMOS
                          if acct in p["targets"] and s in p["skus"] and p["weeks"][0] <= w <= p["weeks"][1]), default=1.0)
                q = int(round(need * up * rng.uniform(0.92, 1.08)))
                if q <= 0:
                    continue
                ln += 1
                unit_price = round(price[s] * 0.78, 2)  # distributor landing price
                amt = round(q * unit_price, 2)
                total += amt
                lines.append(dict(invoice_line_code=f"{inv_code}-L{ln:02d}", invoice_code=inv_code, sku_code=s,
                                  quantity=q, unit="unit", unit_price=unit_price, line_amount=amt))
                sold = sell_df[(sell_df.week == w) & (sell_df.sku_code == s) & (sell_df.outlet_code.isin(ols))].quantity.sum()
                stock[s] += q - sold
            orders.append(dict(order_code=so_code, customer_code=acct, order_date=str(ws), status="invoiced",
                               channel_code="GT" if acct.startswith("D") else ("MT" if acct == "MT01" else "QC")))
            invoices.append(dict(invoice_code=inv_code, order_code=so_code, customer_code=acct,
                                 invoice_date=str(ws + timedelta(days=1)), due_date=str(ws + timedelta(days=31)),
                                 amount=round(total, 2), currency=CURRENCY, status="posted",
                                 fiscal_period=fiscal_quarter(ws)))
            if acct.startswith("D") and w % 4 == 0:  # monthly-ish distributor stock snapshot
                for s in acct_skus:
                    weekly_sell = max(1.0, sum(expected.get((oc, s), 0) for oc in ols))
                    q = max(0.0, stock[s] + 2 * weekly_sell)  # 2 weeks pipeline stock + accumulated build
                    inventory.append(dict(distributor_code=acct, sku_code=s, as_of_date=str(ws + timedelta(days=6)),
                                          quantity=round(q), unit="unit", days_of_cover=round(7 * q / weekly_sell, 1)))
    out["sales_orders"] = pd.DataFrame(orders)
    out["invoices"] = pd.DataFrame(invoices)
    out["invoice_lines"] = pd.DataFrame(lines)
    out["inventory"] = pd.DataFrame(inventory)

    # ---------------------------------------------------------- forecasts (monthly, SKU x micro-market)
    fc = []
    months = [(f"2026-{m:02d}", m - 3) for m in range(4, 10)]  # Apr..Sep
    for s in sku_codes:
        for mm in MICRO:
            mm_outlets = [o for o in outlets if o["geo_code"] == mm and s in stocks_by_outlet[o["outlet_code"]]]
            monthly = sum(base[s] * cls_mult[o["outlet_class"]] for o in mm_outlets) * 4.33
            for period, idx in months:
                promo = [p for p in PROMOS if s in p["skus"] and (p["geo"] in (mm, "PUNE"))
                         and _month_of(p["weeks"][0]) == idx]
                for ftype, f in (("baseline", 1.0), ("consensus", 1 + (promo[0]["primary_uplift"] if promo else 0))):
                    fc.append(dict(forecast_code=f"DF-{s}-{mm}-{period}-{ftype[:4].upper()}", sku_code=s, geo_code=mm,
                                   period=period, forecast_type=ftype, forecast_quantity=round(monthly * f),
                                   unit="unit", version="v1", promotion_code=promo[0]["id"] if promo and ftype == "consensus" else ""))
    out["forecasts"] = pd.DataFrame(fc)

    # ---------------------------------------------------------- availability (bi-weekly visits, 3 SKUs per visit)
    av = []
    for o in outlets:
        for w in range(2, WEEKS + 1, 2):
            for s in rng.choice(stocks_by_outlet[o["outlet_code"]], size=3, replace=False):
                p_on = 0.92
                if o["geo_code"] == "MM-C" and _promo_active("TP2026-004", s, w):
                    p_on = 0.50  # planted low OSA during the display drive
                av.append(dict(observation_code=f"AV-{o['outlet_code']}-{s}-W{w:02d}", outlet_code=o["outlet_code"],
                               sku_code=s, observation_date=str(week_start(w) + timedelta(days=2)),
                               on_shelf=bool(rng.random() < p_on), facings=int(rng.integers(1, 6))))
    out["availability"] = pd.DataFrame(av)

    # ---------------------------------------------------------- consumer panel purchases
    pe = []
    for h in range(1, 301):
        home = outlets[int(rng.integers(0, len(outlets)))]
        for _ in range(int(rng.integers(3, 11))):
            s = str(rng.choice(stocks_by_outlet[home["outlet_code"]]))
            d = START + timedelta(days=int(rng.integers(0, WEEKS * 7)))
            fam = "-".join(s.split("-")[:2])
            q = int(rng.integers(1, 3))
            pe.append(dict(purchase_code=f"PE-{len(pe) + 1:05d}", household_ref=f"HH-{h:04d}", outlet_code=home["outlet_code"],
                           sku_code=s, purchase_date=str(d), quantity=q, spend=q * price[s], currency=CURRENCY,
                           need_code=str(rng.choice(FAMILY_NEEDS[fam]))))
    out["purchases"] = pd.DataFrame(pe)

    # ---------------------------------------------------------- claims, settlements (documents) + trade spend, margin (tabular)
    claims = _claims(out["invoices"])
    spend = []
    for p in PROMOS:
        settled = sum(c["approved"] for c in claims if c["promotion"] == p["id"] and c["settlement"])
        spend.append(dict(trade_spend_code=f"TS-{p['id']}", promotion_code=p["id"], spend_type=p["mechanic"],
                          amount=settled or round(p["budget"] * 0.6), currency=CURRENCY,
                          period=fiscal_quarter(week_start(p["weeks"][0]))))
    for i, m in enumerate(range(4, 10)):  # planted: BW-LIQ-1L trade spend rises monthly
        spend.append(dict(trade_spend_code=f"TS-BW-LIQ-1L-2026-{m:02d}", promotion_code="", spend_type="listing and visibility",
                          amount=60_000 + 45_000 * i, currency=CURRENCY, period=f"2026-{m:02d}", sku_code="BW-LIQ-1L"))
    out["trade_spend"] = pd.DataFrame(spend)
    margins = []
    for s in sku_codes:
        for i, m in enumerate(range(4, 10)):
            gm = 38.0 + rng.normal(0, 0.6)
            if s == "BW-LIQ-1L":
                gm = 38.0 - 2.6 * i + rng.normal(0, 0.3)  # planted decline
            margins.append(dict(margin_code=f"GM-{s}-2026-{m:02d}", sku_code=s, period=f"2026-{m:02d}",
                                value=round(gm, 2), unit="%"))
    out["margins"] = pd.DataFrame(margins)

    for name, df in out.items():
        df.to_csv(TAB / f"{name}.csv", index=False)
    _documents(claims)
    truth = _truth(claims)
    (HERE / "truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    print(f"synth: {sum(len(d) for d in out.values())} tabular rows in {len(out)} files, "
          f"{len(list(DOCS.glob('*.md')))} documents; sell_out={len(sell_df)}")


def _outlet_in_scope(o: dict, p: dict) -> bool:
    if o["channel_code"] != p["channel"]:
        return False
    if p["channel"] == "GT":
        return o["distributor_code"] in p["targets"]
    return True


def _promo_active(pid: str, sku: str, w: int) -> bool:
    p = next(x for x in PROMOS if x["id"] == pid)
    return sku in p["skus"] and p["weeks"][0] <= w <= p["weeks"][1]


def _uplift(o: dict, sku: str, w: int, key: str) -> float:
    for p in PROMOS:
        if sku in p["skus"] and p["weeks"][0] <= w <= p["weeks"][1] and _outlet_in_scope(o, p):
            return 1 + p[key] * rng.uniform(0.85, 1.15) if p[key] > 0.05 else 1 + p[key]
    return 1.0


def _month_of(week: int) -> int:
    return (week_start(week).month - 4) + 1


def _claims(invoices: pd.DataFrame) -> list[dict]:
    def inv(acct: str, w: int) -> str:
        return f"INV-{acct}-W{w:02d}"

    c = []
    # TP2026-005 (CQ7): partial approval (spec §8 numbers), full approval, rejection, approved-unsettled
    c.append(dict(id="CLM8421", promotion="TP2026-005", customer="D107", sku="BW-PWD-1KG", invoice=inv("D107", 17),
                  claimed=620_000, approved=510_000, status="partially_approved", settlement="CN7311",
                  settlement_type="credit_note", claim_date="2026-08-14", settle_date="2026-08-28",
                  reason="Rebate on 1 kg volumes; 110,000 disallowed for sales outside the offer period."))
    c.append(dict(id="CLM8422", promotion="TP2026-005", customer="D101", sku="BW-PWD-2KG", invoice=inv("D101", 18),
                  claimed=240_000, approved=240_000, status="approved", settlement="CN7312",
                  settlement_type="credit_note", claim_date="2026-08-17", settle_date="2026-08-31", reason=""))
    c.append(dict(id="CLM8423", promotion="TP2026-005", customer="D103", sku="BW-PWD-1KG", invoice=inv("D103", 19),
                  claimed=180_000, approved=0, status="rejected", settlement="", settlement_type="",
                  claim_date="2026-08-20", settle_date="", dispute="DSP-0091",
                  reason="Supporting secondary sales evidence not provided."))
    c.append(dict(id="CLM8424", promotion="TP2026-005", customer="D108", sku="BW-PWD-2KG", invoice=inv("D108", 18),
                  claimed=95_000, approved=95_000, status="approved", settlement="", settlement_type="",
                  claim_date="2026-08-24", settle_date="", reason="Approved; settlement pending."))
    # TP2026-003: loaded distributors claim the volume incentive in full
    for i, d in enumerate(["D104", "D105", "D106"]):
        amt = [410_000, 385_000, 352_000][i]
        c.append(dict(id=f"CLM83{i + 10}", promotion="TP2026-003", customer=d, sku="BW-LIQ-1L", invoice=inv(d, 12),
                      claimed=amt, approved=amt, status="approved", settlement=f"CN72{i + 50}",
                      settlement_type="credit_note", claim_date="2026-07-10", settle_date="2026-07-24", reason=""))
    # TP2026-001: settled by bank transfer
    c.append(dict(id="CLM8105", promotion="TP2026-001", customer="D102", sku="BW-PWD-1KG", invoice=inv("D102", 7),
                  claimed=128_000, approved=128_000, status="approved", settlement="PS-2026-0042",
                  settlement_type="settlement", claim_date="2026-06-10", settle_date="2026-06-24", reason=""))
    return c


def _documents(claims: list[dict]) -> None:
    sku_names = {f"{f}-{c}": f"{next(x[1] for x in FAMILIES if x[0] == f)} {pk}"
                 for f, sizes in SIZES.items() for c, pk, _, _ in sizes}
    geo_names = {g[0]: g[1] for g in GEOS}
    ch_names = {c[0]: c[1] for c in CHANNELS}
    brand_names = {b[0]: b[1] for b in BRANDS}
    for p in PROMOS:
        tgt = ", ".join(f"{t} ({DIST_NAMES.get(t) or dict((r[0], r[1]) for r in RETAILERS)[t]})" for t in p["targets"])
        skus = "\n".join(f"- {s} — {sku_names[s]}" for s in p["skus"])
        start, end = week_start(p["weeks"][0]), week_start(p["weeks"][1]) + timedelta(days=6)
        (DOCS / f"circular_{p['id']}.md").write_text(f"""# Trade circular {p['id']}: {p['name']}

From: Aurora Consumer Goods, Customer Development
To: {ch_names[p['channel']]} partners, {geo_names[p['geo']]}

## Offer
Brand: {brand_names[p['brand']]}. Mechanic: {p['mechanic']}.
Offer period: {start:%d %B %Y} to {end:%d %B %Y} ({fiscal_quarter(start)}).
Channel: {ch_names[p['channel']]}. Geography: {geo_names[p['geo']]} ({p['geo']}).

## Eligible products
{skus}

## Eligible partners
{tgt}

## Budget
The promotion is funded from promotion budget PB-{p['id']} of {CURRENCY} {p['budget']:,} for {fiscal_quarter(start)}.

## Eligibility rule
Claims must be submitted within 30 days of the offer end date with secondary sales evidence.
""", encoding="utf-8")

    for c in claims:
        cust_name = DIST_NAMES[c["customer"]]
        (DOCS / f"claim_{c['id']}.md").write_text(f"""# Scheme claim {c['id']}

From: {cust_name} (Distributor {c['customer']})
To: Aurora Consumer Goods, Trade Finance
Date: {c['claim_date']}

## Claim
Distributor {c['customer']} submits claim {c['id']} for {CURRENCY} {c['claimed']:,} against promotion {c['promotion']}
for SKU {c['sku']} ({sku_names[c['sku']]}), referencing invoice {c['invoice']}.
Secondary sales statements are attached as evidence EV-{c['id']}.
""", encoding="utf-8")
        if c["status"] == "rejected":
            (DOCS / f"claim_decision_{c['id']}.md").write_text(f"""# Claim decision {c['id']}

From: Aurora Consumer Goods, Trade Finance
To: Distributor {c['customer']}

## Decision
Claim {c['id']} for {CURRENCY} {c['claimed']:,} against promotion {c['promotion']} is rejected. Approved amount: {CURRENCY} 0.
Reason: {c['reason']} The distributor has raised dispute {c['dispute']} contesting the rejection.
""", encoding="utf-8")
        elif not c["settlement"]:
            (DOCS / f"claim_decision_{c['id']}.md").write_text(f"""# Claim decision {c['id']}

From: Aurora Consumer Goods, Trade Finance
To: Distributor {c['customer']}

## Decision
Claim {c['id']} against promotion {c['promotion']} is approved for {CURRENCY} {c['approved']:,} of the
{CURRENCY} {c['claimed']:,} claimed. Settlement has not yet been issued.
""", encoding="utf-8")
        elif c["settlement_type"] == "credit_note":
            note = f" {c['reason']}" if c["reason"] else ""
            (DOCS / f"credit_note_{c['settlement']}.md").write_text(f"""# Credit note {c['settlement']}

From: Aurora Consumer Goods, Accounts Receivable
To: Distributor {c['customer']}
Date: {c['settle_date']}

## Settlement
{CURRENCY} {c['approved']:,} was approved on claim {c['id']} ({CURRENCY} {c['claimed']:,} claimed) under promotion
{c['promotion']} and settled through credit note {c['settlement']} against invoice {c['invoice']}.{note}
""", encoding="utf-8")
        else:
            (DOCS / f"settlement_{c['settlement']}.md").write_text(f"""# Settlement advice {c['settlement']}

From: Aurora Consumer Goods, Accounts Payable
To: Distributor {c['customer']}
Date: {c['settle_date']}

## Settlement
Promotion settlement {c['settlement']} of {CURRENCY} {c['approved']:,} by bank transfer settles claim {c['id']}
against promotion {c['promotion']}.
""", encoding="utf-8")


def _truth(claims: list[dict]) -> dict:
    return {
        "seed": SEED,
        "loaded_no_sell_through": ["TP2026-003"],
        "healthy_promotions": ["TP2026-005"],
        "promotion_windows": {p["id"]: [str(week_start(p["weeks"][0])), str(week_start(p["weeks"][1]) + timedelta(days=6))]
                              for p in PROMOS},
        "claims": {c["id"]: {k: c[k] for k in ("promotion", "customer", "sku", "invoice", "claimed", "approved",
                                                "status", "settlement")} for c in claims},
        "low_osa": {"promotion": "TP2026-004", "micro_market": "MM-C"},
        "margin_decline_sku": "BW-LIQ-1L",
    }


if __name__ == "__main__":
    build()
