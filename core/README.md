# shopimpact-core

Install from the project with `python -m pip install ./core`. This package is installable locally; it has not been published to PyPI.

```python
from shopimpact_core import estimate

r = estimate("Furniture", 100, price_year=2022, seed=42)
print(r["point"], r["p05"], r["p95"])
```

CLI: `shopimpact --category Smartphone --amount 799 --price-year 2023 > experiment.json`, then `shopimpact --replay experiment.json`.

EPA SC-GHG v1.3.0, USD2022 purchaser-price factors, are pinned to DOI https://doi.org/10.23719/1531143 and raw file SHA256 in data/manifest.json. Each selected factor records NAICS, USEEIO commodity, title, year, region, currency and boundary. Analyst-defined category mappings are versioned and include equal weights over unique underlying commodities. This is NOT an expenditure-weighted average. CPI-U all-items is a broad price-year proxy rather than a sector deflator.

Monte Carlo resamples that empirical mapping spread. Repeated records in one category share the same factor draw within a monthly iteration. It does not quantify unpublished parameter, inventory or measurement uncertainty. Single-factor categories have a degenerate sensitivity interval and explicitly missing parameter uncertainty. Manufacturer point LCAs are not given invented distributions.

The comparison is a three-product US-configured Apple convenience pilot. EPA supply-chain factors and full manufacturer LCAs have different boundaries. Differences cannot be interpreted as pure estimator accuracy or generalized to all products/regions. No India/EU spend factor is fabricated; unsupported regions fail closed.

The grouped DP planner uses integer minor currency units, at most one action per group, a hard budget, maximum changes and a feasibility filter. Benefits/costs are user-supplied scenarios. Its frontier contains nondominated cost/benefit states. It refuses excessive state counts instead of silently approximating.

The receipt classifier is an uncalibrated NB development baseline with a tiny author-curated holdout. Benchmark precision/recall are computed on that separate frozen set; no real-world performance is claimed. Corrections can update the local model but never the reported frozen benchmark.
