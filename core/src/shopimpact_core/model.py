"""EPA purchaser-price factors and reproducible mapping-sensitivity simulation."""

import hashlib
import json
import math
import random
import statistics
from importlib.resources import files

VERSION = "0.1.0"
CPI = {2022: 292.655, 2023: 304.702, 2024: 313.689}
CPI_SOURCE = "https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm"


def load(name):
    return json.loads(files("shopimpact_core").joinpath("data", name).read_text())


# Monthly CPI is a pinned BLS snapshot, never fetched during an estimate.
CPI.update(load("cpi.json")["periods"])
BLS_MONTHLY_SOURCE = load("cpi.json")["source"]


def manifest():
    result = load("manifest.json")
    result["dataset_sha256"] = hashlib.sha256(
        b"".join(
            files("shopimpact_core").joinpath("data", name).read_bytes()
            for name in [
                "factors.json",
                "products.json",
                "epa_v1.3_usd2022.csv",
                "cpi.json",
            ]
        )
    ).hexdigest()
    return result


def factors():
    return load("factors.json")


def references():
    return load("products.json")


def positive(value, name, zero=True):
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
        or value < 0
        or (not zero and value == 0)
    ):
        raise ValueError(
            f"{name} must be a finite {'nonnegative' if zero else 'positive'} number."
        )
    return float(value)


def source_rows(category):
    if category not in factors():
        raise ValueError("Unknown category.")
    # NAICS codes sharing a USEEIO commodity are not independent observations.
    return list({r["useeio"]: r for r in factors()[category]}.values())


def normalized_amount(amount, region="US", currency="USD", price_year=2022):
    positive(amount, "Spend")
    if region != "US" or currency != "USD":
        raise ValueError(
            "No validated native spend factors for this region/currency. A US factor is not substituted."
        )
    if price_year not in CPI:
        raise ValueError(
            "Price-year CPI is unavailable. Choose a verified annual or monthly CPI price basis."
        )
    return amount * CPI[2022] / CPI[price_year]


def summary(samples):
    ordered = sorted(samples)

    def q(p):
        index = (len(ordered) - 1) * p
        lo = int(index)
        hi = min(lo + 1, len(ordered) - 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)

    return {
        "mean": statistics.fmean(samples),
        "p05": q(0.05),
        "p50": q(0.5),
        "p95": q(0.95),
    }


def estimate(
    category, amount, region="US", currency="USD", price_year=2022, draws=4096, seed=42
):
    if (
        isinstance(draws, bool)
        or not isinstance(draws, int)
        or not 100 <= draws <= 50000
    ):
        raise ValueError("Draw count must be an integer between 100 and 50000.")
    spend = normalized_amount(amount, region, currency, price_year)
    rows = source_rows(category)
    rng = random.Random(seed)
    samples = [spend * rng.choice(rows)["value"] for _ in range(draws)]
    return {
        **summary(samples),
        "samples": samples,
        "point": spend * statistics.fmean(r["value"] for r in rows),
        "source_rows": rows,
        "source_count": len(rows),
        "parameter_uncertainty_available": False,
        "mapping_spread_available": len({r["value"] for r in rows}) > 1,
        "interval_kind": "5th–95th percentile category-mapping sensitivity; NOT a confidence interval",
        "normalized_usd2022": spend,
        "cpi_source": BLS_MONTHLY_SOURCE if isinstance(price_year, str) else CPI_SOURCE,
        "dataset_version": manifest()["version"],
        "seed": seed,
        "draws": draws,
    }


def monthly(records, draws=4096, seed=42):
    if (
        isinstance(draws, bool)
        or not isinstance(draws, int)
        or not 100 <= draws <= 50000
    ):
        raise ValueError("Draw count must be 100–50000.")
    if not isinstance(records, list) or len(records) > 2000:
        raise ValueError("At most 2,000 records supported.")
    # Shared systematic factor per category per draw: do not cancel correlated errors.
    if not records:
        return {
            **summary([0.0] * draws),
            "samples": [0.0] * draws,
            "unquantified_categories": [],
        }
    by_category = {}
    for r in records:
        category = r["category"]
        by_category[category] = by_category.get(category, 0) + normalized_amount(
            r["amount"], r["region"], r["currency"], r["price_year"]
        )
    rng = random.Random(seed)
    candidates = {cat: source_rows(cat) for cat in by_category}
    samples = []
    for _ in range(draws):
        samples.append(
            sum(
                spend * rng.choice(candidates[cat])["value"]
                for cat, spend in sorted(by_category.items())
            )
        )
    return {
        **summary(samples),
        "samples": samples,
        "unquantified_categories": list(by_category),
    }


def comparison(product):
    estimate_result = estimate(
        product["category"], product["price"], price_year=product["price_year"]
    )
    predicted = estimate_result["point"]
    reference = product["lca_kg"]
    return {
        **product,
        "spend_kg": predicted,
        "difference_kg": predicted - reference,
        "relative_difference_pct": 100 * (predicted - reference) / reference,
        "low_confidence": abs(predicted - reference) / reference > 0.5,
        "boundary_warning": "EPA upstream purchaser-price and manufacturer cradle-to-grave boundaries differ. Difference is not pure predictive error.",
    }


def replay_export(payload, kind="estimate"):
    allowed = {"estimate", "monthly"}
    if kind not in allowed:
        raise ValueError("Unsupported experiment kind.")
    result = estimate(**payload) if kind == "estimate" else monthly(**payload)
    result.pop("samples", None)
    data = {
        "schema": 1,
        "core_version": VERSION,
        "dataset_sha256": manifest()["dataset_sha256"],
        "dataset_version": manifest()["version"],
        "kind": kind,
        "inputs": payload,
        "results": result,
    }
    return json.dumps(data, sort_keys=True, allow_nan=False)


def replay(text):
    if len(text) > 2_000_000:
        raise ValueError("Experiment exceeds 2 MB.")
    data = json.loads(text)
    if (
        data.get("schema") != 1
        or data.get("core_version") != VERSION
        or data.get("dataset_sha256") != manifest()["dataset_sha256"]
    ):
        raise ValueError("Incompatible schema, core or dataset; exact replay refused.")
    actual = json.loads(replay_export(data["inputs"], data["kind"]))
    if actual != data:
        raise ValueError("Replay results differ from the stored experiment.")
    return actual
