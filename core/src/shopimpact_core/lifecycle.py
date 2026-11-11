"""User-declared lifespan and replacement scenarios, not causal recommendations."""

from .model import positive


def lifespan(kg, cost, years, uses_per_year):
    positive(kg, "Footprint")
    positive(cost, "Cost")
    positive(years, "Expected years", False)
    positive(uses_per_year, "Uses per year", False)
    return {"kg_per_year": kg / years, "cost_per_use": cost / (years * uses_per_year)}


def break_even(embodied_kg, old_kwh_year, new_kwh_year, grid_kg_kwh):
    for name, value in [
        ("Embodied emissions", embodied_kg),
        ("Old energy", old_kwh_year),
        ("New energy", new_kwh_year),
        ("Grid factor", grid_kg_kwh),
    ]:
        positive(value, name)
    annual = (old_kwh_year - new_kwh_year) * grid_kg_kwh
    return {
        "annual_difference": annual,
        "years": embodied_kg / annual if annual > 0 else None,
        "limits": "Assumes constant electricity use/grid, equal service, and excludes repair, degradation, disposal and rebound.",
    }


def concentration(records):
    rows = sorted(records, key=lambda r: -r["estimate_kg"])
    total = sum(r["estimate_kg"] for r in rows)
    running = 0
    result = []
    for index, r in enumerate(rows, 1):
        running += r["estimate_kg"]
        result.append(
            {**r, "rank": index, "cumulative_share": running / total if total else 0}
        )
    return result
