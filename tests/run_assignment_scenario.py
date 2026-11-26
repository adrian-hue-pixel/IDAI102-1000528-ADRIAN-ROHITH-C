import datetime as dt
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import logic as lg
today=dt.date(2026,11,26)
rows=[
("Clothing","Generic shop",25,"New",False),
("Clothing","Thrift store",20,"Second-hand",True),
("Leather Shoes","Generic shop",120,"New",False),
("Books & Stationery","Used bookshop",8,"Second-hand",True),
("Laptop / Computer","Generic shop",900,"New",False),
("Smartphone","Generic shop",250,"Refurbished",False),
("Groceries - Meat & Dairy","Supermarket",45,"New",False),
("Groceries - Plant-based","Market",30,"New",True),
("Cleaning Products","Generic shop",9,"New",True),
("Coffee & Tea","Generic shop",12,"New",False),
("Furniture","Used furniture shop",80,"Second-hand",False),
("Cosmetics & Personal Care","Generic shop",15,"New",True),
]
purchases=[]
print("| # | Category | Condition | Minimal packaging | USD | kg CO₂e | Rating |")
print("|---:|---|---|---|---:|---:|---|")
for i,(cat,brand,price,condition,pack) in enumerate(rows,1):
    p=lg.add_purchase(purchases,i,dt.date(2026,11,i),cat,brand,price,condition,pack,today=today)
    expected=round(price*lg.PRODUCTS[cat]["multiplier"]*lg.CONDITION_FACTORS[condition]*(lg.CURATED_BRAND_FACTOR if lg.matches_curated_brand(brand) else 1)*(lg.LOW_PACKAGING_FACTOR if pack else 1),3)
    assert math.isclose(p["co2_kg"],expected)
    summary=lg.monthly_summary(purchases,(2026,11))
    assert summary["n"]==i
    assert summary["spend_usd"]==round(sum(x[2] for x in rows[:i]),2)
    assert summary["co2_kg"]==round(sum(x["co2_kg"] for x in purchases),2)
    alternatives=lg.suggest_alternatives(cat,brand,price,condition,pack)
    assert alternatives["static"]
    print(f"| {i} | {cat} | {condition} | {'Yes' if pack else 'No'} | {price:.2f} | {p['co2_kg']:.3f} | {p['rating']} |")
print("\nFinal summary:", {k:v for k,v in summary.items() if k not in ("by_type","by_category")})
badges = lg.earned_badge_ids(purchases, (2026, 11), 80)
assert badges == {"first_step", "second_life"}
print("Earned badge IDs:", ", ".join(sorted(badges)))
assert lg.monthly_summary(purchases,(2026,10))["n"]==0
for bad in (-1,0,float("nan"),float("inf")):
    try: lg.add_purchase(purchases,99,today,"Clothing","Generic shop",bad,today=today)
    except ValueError: pass
    else: raise AssertionError("Invalid price accepted")
assert len(purchases)==12
print("PASS: 12 sequential additions, independent formula and running totals, category alternatives, empty month, four invalid prices rejected without changing the journal.")
