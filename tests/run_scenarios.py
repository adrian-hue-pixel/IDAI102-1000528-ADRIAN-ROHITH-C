"""
Runs the 15-purchase demo scenario through the logic engine and prints Markdown
tables (used in docs/test_log.md).   Run with:  python tests/run_scenarios.py
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logic as lg

GOAL_KG = 80
today = dt.date(2026, 10, 5)
demo = lg.demo_purchases(today)

print("### Purchases and estimated impact\n")
print("| # | Date | Product | Brand | Condition | Price (USD) | CO₂e (kg) | Rating |")
print("|---|------|---------|-------|-----------|------------:|----------:|--------|")
for p in demo:
    print(
        f"| {p['id']} | {p['date']} | {p['product_type']} | {p['brand']} | {p['condition']} | "
        f"{p['price_usd']:.2f} | {p['co2_kg']:.2f} | {p['rating']} |"
    )

print(f"\n### Monthly dashboard numbers (goal = {GOAL_KG} kg)\n")
print("| Month | Purchases | Spend (USD) | CO₂e (kg) | Avg kg per $ | Rating |")
print("|-------|----------:|------------:|----------:|-------------:|--------|")
for row in lg.monthly_totals(demo):
    s = lg.monthly_summary(demo, row["ym"])
    print(
        f"| {lg.month_label(row['ym'])} | {s['n']} | {s['spend_usd']:.2f} | {s['co2_kg']:.2f} | "
        f"{s['intensity']:.3f} | {s['rating']} |"
    )

print("\n### Badges earned per month\n")
names = [b["name"] for b in lg.BADGES]
print("| Month | " + " | ".join(names) + " |")
print("|-------|" + "|".join([":---:"] * len(names)) + "|")
for row in lg.monthly_totals(demo):
    got = lg.earned_badge_ids(demo, row["ym"], GOAL_KG)
    print(
        f"| {lg.month_label(row['ym'])} | "
        + " | ".join("✅" if b["id"] in got else "—" for b in lg.BADGES)
        + " |"
    )
