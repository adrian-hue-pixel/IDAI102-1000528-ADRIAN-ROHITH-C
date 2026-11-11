"""Cited research tools embedded in ShopImpact’s everyday workspace."""

import calendar
import datetime as dt
import hashlib
import json
import math
import uuid

import altair as alt
import pandas as pd
import streamlit as st
from shopimpact_core import (
    comparison,
    counterexample,
    estimate,
    factors,
    greedy,
    manifest,
    monthly,
    optimize,
    references,
)
from shopimpact_core.classifier import DATA, evaluate, predict
from shopimpact_core.lifecycle import break_even, concentration, lifespan
from shopimpact_core.model import CPI, replay, replay_export
from streamlit_js_eval import streamlit_js_eval

from styles import style_chart
from ui.common import app_today

VERSION = "research-0.1.0"
STORAGE = "shopimpact_research_v1"


def validate_store(data):
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("Unsupported research journal schema.")
    records = data.get("records", [])
    if not isinstance(records, list) or len(records) > 2000:
        raise ValueError("At most 2,000 records are supported.")
    ids = set()
    for r in records:
        if r["id"] in ids:
            raise ValueError("Duplicate record ID.")
        ids.add(r["id"])
        dt.date.fromisoformat(r["date"])
        result = estimate(
            r["category"],
            r["amount"],
            r["region"],
            r["currency"],
            r["price_year"],
            draws=100,
        )
        if r["dataset_version"] not in {
            "2026.11.1",
            manifest()["version"],
        } or not math.isclose(
            result["point"], r["estimate_kg"], rel_tol=1e-10, abs_tol=1e-10
        ):
            raise ValueError(
                "Stored estimate differs from this dataset; migration required."
            )
        if "factor_snapshot" in r and r["factor_snapshot"] != result["source_rows"]:
            raise ValueError("Stored source factors differ; migration required.")
        if "cpi_index" in r and r["cpi_index"] != CPI[r["price_year"]]:
            raise ValueError("Stored CPI differs; migration required.")
    corrections = data.get("corrections", [])
    if not isinstance(corrections, list) or len(corrections) > 1000:
        raise ValueError("Too many corrections.")
    for r in corrections:
        if (
            r["category"] not in factors()
            or not isinstance(r["text"], str)
            or len(r["text"]) > 10000
        ):
            raise ValueError("Invalid classifier correction.")
    feedback = data.get("feedback", [])
    if not isinstance(feedback, list) or len(feedback) > 1000:
        raise ValueError("Invalid feedback list.")
    for r in feedback:
        if (
            not isinstance(r, dict)
            or set(r) - {"id", "task", "ease", "trust", "consent", "version"}
            or not r.get("consent")
            or not 1 <= r.get("ease", 0) <= 5
            or not 1 <= r.get("trust", 0) <= 5
        ):
            raise ValueError("Invalid anonymous feedback.")
    return {
        "schema": 1,
        "records": records,
        "corrections": corrections,
        "feedback": feedback,
    }


def bootstrap():
    state = st.session_state
    for key, value in {
        "research_records": [],
        "research_corrections": [],
        "research_feedback": [],
        "research_loaded": False,
        "research_locked": False,
        "research_mode": "Light",
        "research_motion": False,
        "research_ambient": True,
        "research_tour": False,
    }.items():
        state.setdefault(key, value)
    if not state.research_loaded:
        raw = streamlit_js_eval(
            js_expressions=f"(function(){{try{{return JSON.stringify({{ok:true,value:localStorage.getItem({json.dumps(STORAGE)})}})}}catch(e){{return JSON.stringify({{ok:false}})}}}})()",
            key="shopimpact_research_read",
            default=None,
        )
        if raw is None:
            st.info("Loading your research journal from this browser…")
            if st.button("Continue with session-only storage"):
                state.research_loaded = True
                state.research_session_only = True
                st.rerun()
            st.stop()
        state.research_loaded = True
        try:
            response = json.loads(raw)
            if not response.get("ok"):
                state.research_session_only = True
            elif response.get("value"):
                state.research_raw_saved = response["value"]
                data = validate_store(json.loads(response["value"]))
                state.research_records = data["records"]
                state.research_corrections = data["corrections"]
                state.research_feedback = data["feedback"]
        except (KeyError, TypeError, ValueError) as exc:
            state.research_locked = True
            state.research_storage_error = str(exc)
    if state.research_locked:
        st.warning(
            "Saved research data could not be validated. Saving is locked: "
            + state.research_storage_error
        )


def store_data():
    s = st.session_state
    return {
        "schema": 1,
        "records": s.research_records,
        "corrections": s.research_corrections,
        "feedback": s.research_feedback,
    }


def persist():
    if st.session_state.research_locked or st.session_state.get(
        "research_session_only"
    ):
        return
    text = json.dumps(store_data(), allow_nan=False, sort_keys=True)
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    result = streamlit_js_eval(
        js_expressions=f'(function(){{try{{localStorage.setItem({json.dumps(STORAGE)},{json.dumps(text)});return "saved"}}catch(e){{return "unavailable"}}}})()',
        key="shopimpact_research_write_" + digest,
        default=None,
    )
    if result == "unavailable":
        st.warning("Browser saving failed. Download a journal backup before leaving.")


def header(title, description):
    if st.session_state.get("research_embedded"):
        st.subheader(title)
        st.caption(description)
        return
    with st.container(key="studio-page-heading"):
        st.markdown(
            f'<div class="page-eyebrow">SHOPIMPACT / YOUR WORKSPACE · {manifest()["version"]}</div>',
            unsafe_allow_html=True,
        )
        st.title(title)
        st.caption(description)


def scoped():
    return [
        r
        for r in st.session_state.research_records
        if r["date"][:7] == st.session_state.research_month
    ]


def histogram(samples, label):
    frame = pd.DataFrame({"kg CO₂e": samples})
    chart = (
        alt.Chart(frame)
        .mark_bar(color="#43856e")
        .encode(
            x=alt.X("kg CO₂e:Q", bin=alt.Bin(maxbins=25)),
            y=alt.Y("count():Q", title="Monte Carlo draws"),
            tooltip=["count():Q"],
        )
        .properties(height=200, title=label)
    )
    st.altair_chart(style_chart(chart, st.session_state.research_mode), width="stretch")
    st.caption(
        label
        + ". 5th–95th percentiles represent category-mapping sensitivity, not measurement confidence."
    )


def interval_note(result):
    if not result["mapping_spread_available"]:
        st.warning(
            "This category has one distinct published factor. The sampled distribution is a point; its parameter uncertainty is unpublished and remains unquantified. A narrow interval does not imply high confidence."
        )
    else:
        st.caption(
            "Spread comes from the listed candidate USEEIO commodities, equally weighted. It is mapping sensitivity, not a calibrated probability of real-world impact."
        )


def provenance(category):
    with st.expander("Data provenance · source, year, region and version"):
        st.dataframe(
            pd.DataFrame(factors()[category]), hide_index=True, width="stretch"
        )
        st.markdown(
            "[EPA dataset and documentation](https://doi.org/10.23719/1531143) · [CPI-U price-year data](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm)"
        )
        st.caption(
            "Manufacturer factors include purchaser margins. Category mappings and equal weights are analyst decisions. Raw EPA file SHA256: "
            + manifest()["epa_sha256"]
        )


def log_page():
    header("Log a purchase", "One entry, with a cited source and visible limits.")
    if not st.session_state.research_tour:
        st.info(
            "1 · Log with a price year. 2 · Inspect the range. 3 · Compare methods in Impact Lab. Previous illustrative records remain in the legacy workspace."
        )
        if st.button("Got it — start my research journal"):
            st.session_state.research_tour = True
            st.rerun()
    category = st.selectbox("Category", list(factors()), key="science_category")
    left, right = st.columns(2)
    region = left.selectbox("Purchase region", ["US", "IN", "EU"])
    currency = right.selectbox(
        "Currency",
        ["USD"] if region == "US" else ["INR"] if region == "IN" else ["EUR"],
    )
    if region != "US":
        st.error(
            "A validated native factor set is not yet bundled for this region. No fixed exchange-rate or US-factor proxy is used. You can inspect manufacturer references in Impact Lab, but they are not region-adjusted."
        )
        return
    amount = left.number_input(
        "Total spend (USD, expressed in the selected price basis)",
        min_value=0.0,
        max_value=1_000_000.0,
        value=25.0,
    )
    year = right.selectbox(
        "Price basis (verified CPI period)",
        list(CPI),
        index=list(CPI).index(max(k for k in CPI if isinstance(k, str))),
        help="Use the matching annual or monthly price index. The latest published month is a proxy for more recent prices; it is not an exact index for an unpublished month.",
    )
    date = left.date_input("Purchase date", value=app_today(), max_value=app_today())
    quantity = right.number_input(
        "Number of physical units for comparison", min_value=1, max_value=100, value=1
    )
    result = estimate(category, amount, price_year=year)
    st.metric("Spend-based estimate", f"{result['point']:.2f} kg CO₂e")
    st.caption("EPA SC-GHG v1.3.0 · US · purchaser-price USD2022 · CPI-U normalization")
    st.write(
        f"Mapping-sensitivity interval: {result['p05']:.2f}–{result['p95']:.2f} kg CO₂e"
    )
    interval_note(result)
    if st.button(
        "Save purchase",
        type="primary",
        disabled=amount <= 0 or st.session_state.research_locked,
    ):
        st.session_state.research_records.append(
            {
                "id": str(uuid.uuid4()),
                "date": date.isoformat(),
                "category": category,
                "amount": amount,
                "currency": currency,
                "region": region,
                "price_year": year,
                "units": quantity,
                "estimate_kg": result["point"],
                "dataset_version": manifest()["version"],
                "dataset_sha256": manifest()["dataset_sha256"],
                "factor_snapshot": result["source_rows"],
                "cpi_index": CPI[year],
                "cpi_source": result["cpi_source"],
            }
        )
        st.success("Purchase saved to your research journal.")
    histogram(result["samples"], "Purchase mapping sensitivity")
    provenance(category)
    with st.expander("Compare with an exact manufacturer configuration"):
        available = [r for r in references() if r["category"] == category]
        if available:
            reference = st.selectbox(
                "Exact model and storage", available, format_func=lambda r: r["name"]
            )
            product_kg = reference["lca_kg"] * quantity
            diff = abs(result["point"] - product_kg) / product_kg
            st.metric("Manufacturer life-cycle reference", f"{product_kg:.2f} kg CO₂e")
            if diff > 0.5:
                st.warning(
                    "LOW CONFIDENCE · methods differ by more than 50% of the LCA reference. This threshold is a heuristic, not a statistical test."
                )
            st.caption(
                "Boundary mismatch: upstream spend model versus full life-cycle LCA. Reference use-phase assumptions are not adapted to your region."
            )
            st.markdown(f"[Manufacturer report]({reference['source']})")
        else:
            st.caption(
                "No verified product-level reference is bundled for this category."
            )


def journal_page():
    header(
        "Research journal",
        "Versioned records; historical illustrative records are kept separately.",
    )
    rows = st.session_state.research_records
    if not rows:
        st.info("No research records yet. Start with Log a purchase.")
    if rows:
        display = pd.DataFrame(rows)[
            [
                "date",
                "category",
                "amount",
                "currency",
                "price_year",
                "estimate_kg",
                "dataset_version",
            ]
        ]
        display["price_year"] = display["price_year"].astype(str)
        st.dataframe(display, hide_index=True, width="stretch")
        with st.expander("Inspect saved source snapshots"):
            st.json(rows)
        selected = st.selectbox(
            "Record to remove",
            [r["id"] for r in rows],
            format_func=lambda id: next(
                r["category"] + " · " + r["date"] for r in rows if r["id"] == id
            ),
        )
        if st.button("Remove selected record"):
            st.session_state.research_undo = list(rows)
            st.session_state.research_records = [r for r in rows if r["id"] != selected]
            st.rerun()
    if st.session_state.get("research_undo") is not None and st.button(
        "Undo last removal"
    ):
        st.session_state.research_records = st.session_state.pop("research_undo")
        st.rerun()
    st.download_button(
        "Download full journal backup",
        json.dumps(store_data(), indent=2),
        file_name="shopimpact-research-journal.json",
        mime="application/json",
    )
    upload = st.file_uploader("Restore research journal JSON", type="json")
    if upload:
        try:
            if upload.size > 2_000_000:
                raise ValueError("File exceeds 2 MB.")
            data = validate_store(json.loads(upload.getvalue()))
            st.caption(
                f"Preview: {len(data['records'])} records; existing research records will be replaced."
            )
            consent = st.checkbox(
                "Replace my research journal with this validated backup"
            )
            if st.button("Restore backup", disabled=not consent):
                st.session_state.research_undo = list(rows)
                st.session_state.research_records = data["records"]
                st.session_state.research_corrections = data["corrections"]
                st.session_state.research_feedback = data["feedback"]
                st.rerun()
        except (ValueError, TypeError, KeyError) as exc:
            st.error(str(exc))


def dashboard_page():
    header(
        "Understand your month",
        "Mapping-sensitive totals, personal budgeting and the purchases that dominate.",
    )
    rows = scoped()
    if not rows:
        st.info(
            "This month has no research entries. Log a purchase or choose another month."
        )
        return
    result = monthly(rows)
    cols = st.columns(3)
    cols[0].metric("Entries", len(rows))
    cols[1].metric("Spend-model total", f"{sum(r['estimate_kg'] for r in rows):.2f} kg")
    cols[2].metric("Mapping sensitivity", f"{result['p05']:.1f}–{result['p95']:.1f} kg")
    st.warning(
        "Published factor parameter uncertainty is unavailable. These ranges cover mapping choices only, including shared category-level draws; they are not full confidence intervals."
    )
    histogram(result["samples"], "Month mapping sensitivity")
    groups = {}
    for r in rows:
        groups.setdefault(r["category"], []).append(r)
    chart_rows = []
    for category, items in groups.items():
        q = monthly(items)
        chart_rows.append(
            {
                "Category": category,
                "Estimate": sum(r["estimate_kg"] for r in items),
                "Low": q["p05"],
                "High": q["p95"],
            }
        )
    frame = pd.DataFrame(chart_rows)
    base = alt.Chart(frame).encode(y=alt.Y("Category:N", sort="-x"))
    plot = (
        base.mark_bar(color="#43856e").encode(
            x=alt.X("Estimate:Q", title="Spend-based kg CO₂e")
        )
        + base.mark_rule(color="#a26e57").encode(x="Low:Q", x2="High:Q")
    ).properties(height=300)
    st.altair_chart(style_chart(plot, st.session_state.research_mode), width="stretch")
    st.caption(
        "Category estimates with 5th–95th percentile mapping-sensitivity bars. A zero-width bar means missing source uncertainty, not certainty. A text table follows."
    )
    st.dataframe(frame, hide_index=True, width="stretch")
    st.subheader("Carbon budget forecast")
    budget = st.number_input(
        "Personal monthly carbon budget (kg)", min_value=0.0, value=100.0
    )
    year, month = map(int, st.session_state.research_month.split("-"))
    days = calendar.monthrange(year, month)[1]
    today = app_today()
    elapsed = today.day if (year, month) == (today.year, today.month) else days
    total = sum(r["estimate_kg"] for r in rows)
    projection = total / elapsed * days
    st.metric("Projected month-end at recorded pace", f"{projection:.1f} kg")
    forecast = pd.DataFrame(
        {
            "Day": [elapsed, days],
            "Projected kg": [total, projection],
            "Personal budget": [budget, budget],
        }
    )
    line = (
        alt.Chart(forecast)
        .mark_line(strokeDash=[5, 4])
        .encode(x="Day:Q", y="Projected kg:Q")
    )
    budget_line = (
        alt.Chart(pd.DataFrame({"Budget": [budget]}))
        .mark_rule(color="#a26e57")
        .encode(y="Budget:Q")
    )
    st.altair_chart(
        style_chart(line + budget_line, st.session_state.research_mode), width="stretch"
    )
    st.caption(
        "Projection assumes the observed recording pace continues. Incomplete journals and irregular purchases can make it misleading."
    )
    st.subheader("Concentration and outliers")
    ranked = concentration(rows)
    top_count = next(
        (r["rank"] for r in ranked if r["cumulative_share"] >= 0.8), len(rows)
    )
    st.write(
        f"{top_count} of {len(rows)} records account for at least 80% of this recorded footprint."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Category": r["category"],
                    "Estimate kg": r["estimate_kg"],
                    "Cumulative share": r["cumulative_share"],
                }
                for r in ranked
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    values = sorted(r["estimate_kg"] for r in rows)
    if len(values) >= 4:
        q1 = values[(len(values) - 1) // 4]
        q3 = values[3 * (len(values) - 1) // 4]
        threshold = q3 + 1.5 * (q3 - q1)
        flags = [r for r in rows if r["estimate_kg"] > threshold]
        st.caption(
            f"{len(flags)} high-value flags using Q3 + 1.5 × IQR. These are review prompts, not errors."
        )


def method_body():
    st.subheader("Method and provenance")
    st.markdown(
        "[EPA USEEIO supply-chain factors v1.3.0](https://doi.org/10.23719/1531143) are the bundled spend source. Every row carries its NAICS/USEEIO code, version, region and price year."
    )
    category = st.selectbox(
        "Inspect category mapping", list(factors()), key="method_category"
    )
    provenance(category)
    st.code(
        "USD2022 = entered USD × CPI(2022) / CPI(price basis)\nkg CO₂e = USD2022 × EPA purchaser-price supply-chain factor"
    )
    st.write(
        "No brand-name, second-hand or packaging discount is applied. Those tags alone do not establish a measured emissions reduction."
    )
    st.subheader("What the Monte Carlo interval means")
    st.write(
        "Draw 4,096 candidate factors with replacement from unique mapped USEEIO commodities. Candidate categories have equal analyst weights. A month shares a category draw across its purchases. Quantiles describe mapping sensitivity, not a validated uncertainty distribution for the true product footprint."
    )
    st.warning(
        "EPA and bundled manufacturer reports do not supply usable parameter distributions here. We do not invent ±30% bands. Single-factor categories remain explicitly unquantified. Manufacturer configuration differences are not treated as measurement uncertainty for an exact model."
    )
    st.subheader("Region availability")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Region": "US",
                    "Currency": "USD",
                    "Status": "EPA v1.3.0; verified annual/monthly CPI snapshot",
                },
                {
                    "Region": "India",
                    "Currency": "INR",
                    "Status": "Native dataset not yet verified; estimates blocked",
                },
                {
                    "Region": "EU",
                    "Currency": "EUR",
                    "Status": "Native dataset not yet verified; estimates blocked",
                },
            ]
        ),
        hide_index=True,
    )
    st.caption(
        "No arbitrary fixed exchange rate is used. Product references are US configurations; no regional use-phase adjustment is claimed."
    )
    st.json(manifest())


def validation_body():
    st.subheader("When does spend-based estimation mislead?")
    rows = [comparison(p) for p in references()]
    frame = pd.DataFrame(rows)
    st.write(
        "Pilot: two base iPhone configurations and one base MacBook Air configuration, selected because official LCAs and US launch prices are available. Price years are normalized with CPI-U. No model fitting is performed on these three references."
    )
    st.warning(
        "n = 3, one manufacturer, convenience selection. Manufacturer LCA includes use/end-of-life; EPA is upstream supply-chain accounting. Relative differences below are descriptive mismatches, not a validated measure of pure prediction error."
    )
    mae = sum(abs(r["difference_kg"]) for r in rows) / len(rows)
    mape = sum(abs(r["relative_difference_pct"]) for r in rows) / len(rows)
    c = st.columns(2)
    c[0].metric("Mean absolute mismatch", f"{mae:.2f} kg")
    c[1].metric("Mean absolute relative mismatch", f"{mape:.1f}%")
    points = (
        alt.Chart(frame)
        .mark_circle(size=100, color="#43856e")
        .encode(
            x=alt.X(
                "lca_kg:Q", title="Manufacturer cradle-to-grave reference · kg CO₂e"
            ),
            y=alt.Y("spend_kg:Q", title="EPA upstream spend estimate · kg CO₂e"),
            tooltip=["name", "lca_kg", "spend_kg"],
        )
    )
    diagonal = (
        alt.Chart(pd.DataFrame({"x": [0, 160]}))
        .mark_line(strokeDash=[4, 4], color="#888")
        .encode(x="x:Q", y="x:Q")
    )
    st.altair_chart(
        style_chart(points + diagonal, st.session_state.research_mode), width="stretch"
    )
    st.caption(
        "Reference-versus-estimate plot. Dashed line is identity, not a fitted relationship. Exact values and sources follow."
    )
    bars = (
        alt.Chart(frame)
        .mark_bar(color="#43856e")
        .encode(
            x=alt.X(
                "relative_difference_pct:Q",
                title="Signed mismatch relative to manufacturer LCA · %",
            ),
            y="name:N",
            color="category:N",
        )
    )
    st.altair_chart(style_chart(bars, st.session_state.research_mode), width="stretch")
    st.dataframe(
        frame[
            [
                "name",
                "category",
                "price",
                "price_year",
                "lca_kg",
                "spend_kg",
                "relative_difference_pct",
            ]
        ],
        hide_index=True,
        width="stretch",
    )
    for r in rows:
        st.markdown(
            f"**{r['name']}** — [LCA report]({r['source']}) · [launch price]({r['price_source']})"
        )
    st.write(
        "Finding in this pilot: the spend method is above the phone references and below the laptop reference. A common sector multiplier cannot recover product design, storage, repairability or service life from price. Boundary mismatch and general CPI normalization are major confounders."
    )
    st.caption(
        "Next study: preregister inclusion rules, add independent manufacturers and region-matched prices, align life-cycle stages, and collect reported uncertainty. No significance claim is made from this pilot."
    )
    st.download_button(
        "Download pilot results CSV",
        frame.to_csv(index=False),
        "shopimpact-validation-pilot.csv",
        "text/csv",
    )


def planner_body():
    st.subheader("Budget- and feasibility-constrained planner")
    st.caption(
        "Candidate benefits/costs below are explicit scenario inputs, not verified savings or derived automatically from brand/condition tags. Use a single currency and mutually exclusive purchase-group IDs."
    )
    example = counterexample()
    edited = st.data_editor(
        pd.DataFrame(example["actions"]),
        num_rows="dynamic",
        hide_index=True,
        key="planner_actions",
    )
    planning_currency = st.selectbox("Planning currency", ["INR", "USD", "EUR", "GBP"])
    budget = st.slider("Budget (in your chosen currency)", 0, 5000, 10)
    maximum = st.slider("Maximum changes", 0, 20, 3)
    threshold = st.slider("Minimum feasibility score", 0.0, 1.0, 0.0, step=0.1)
    algorithm = st.radio(
        "Algorithm", ["Dynamic programming (exact)", "Greedy ratio"], horizontal=True
    )
    try:
        actions = edited.to_dict("records")
        dp = optimize(actions, budget, maximum, threshold)
        approx = greedy(actions, budget, maximum, threshold)
        result = dp if algorithm.startswith("Dynamic") else approx
        cost_col, benefit_col = st.columns(2)
        cost_col.metric(
            "Selected scenario cost", f"{result['cost']:.2f} {planning_currency}"
        )
        benefit_col.metric(
            "Hypothetical avoided emissions", f"{result['kg']:.2f} kg CO₂e"
        )
        st.write(
            "Selected actions: "
            + (", ".join(result["ids"]) or "None within these constraints")
        )
        st.caption(
            f"Costs in {planning_currency}. Greedy: {approx['kg']:.2f} kg scenario benefit. DP: {dp['kg']:.2f} kg. Gap: {dp['kg'] - approx['kg']:.2f} kg."
        )
        frontier = pd.DataFrame(dp["frontier"])
        chart = (
            alt.Chart(frontier)
            .mark_line(point=True, color="#43856e")
            .encode(
                x=alt.X("cost:Q", title="Scenario cost"),
                y=alt.Y("kg:Q", title="Hypothetical avoided kg CO₂e"),
            )
        )
        st.altair_chart(
            style_chart(chart, st.session_state.research_mode), width="stretch"
        )
        st.caption(
            "Nondominated cost–CO₂ scenario frontier, under your constraints. No cost/benefit measurements are implied."
        )
    except (ValueError, KeyError, TypeError) as exc:
        st.error(str(exc))
    with st.expander("Why greedy fails — a complete counterexample"):
        st.write(
            "Budget 10. A costs 6 and saves 12; B and C each cost 5 and save 9. Greedy ratios are 2 versus 1.8: it takes A and cannot fit either remaining item, giving 12. DP chooses B+C for 18. Thus ratio-greedy is not optimal for 0/1 selection."
        )
        st.code("D[g,b,k] = max(D[g−1,b,k], max_a(D[g−1,b−cost(a),k−1] + benefit(a)))")
        st.caption(
            "The previous-group transition enforces one action per purchase group. Sparse exact states use integer minor currency units. A state guard refuses excessive instances; it does not silently round costs or substitute greedy."
        )


def lab_page():
    header("Impact Lab", "Method → validation → a constrained decision.")
    method, validation, planner = st.tabs(["Method", "Validation", "Planner"])
    with method:
        method_body()
    with validation:
        validation_body()
    with planner:
        planner_body()
    replay_body()


def replay_body():
    st.subheader("Experiment replay")
    payload = {
        "category": "Furniture",
        "amount": 100,
        "price_year": 2022,
        "seed": 42,
        "draws": 4096,
    }
    st.download_button(
        "Download reproducible example",
        replay_export(payload),
        "shopimpact-experiment.json",
        "application/json",
    )
    file = st.file_uploader("Import experiment JSON", type="json")
    if file:
        try:
            result = replay(file.getvalue().decode())
            st.success("Exact replay matched stored results.")
            st.json(result)
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            st.error(str(exc))


def method_page():
    header("Method", "Sources, boundaries, assumptions and missing evidence.")
    method_body()


def classifier_page():
    header(
        "Product text classifier",
        "A transparent development baseline, with local corrections.",
    )
    text = st.text_area(
        "Paste a product description (omit names, card details and identifiers)",
        max_chars=10000,
    )
    if text:
        r = predict(text, st.session_state.research_corrections)
        if r["abstained"]:
            st.warning("No known product vocabulary found. Choose a category manually.")
        else:
            st.write("Suggested category: **" + r["category"] + "**")
            st.caption(
                f"Uncalibrated model score: {r['score']:.2f}. This is not a probability of being correct."
            )
        corrected = st.selectbox(
            "Correct me",
            list(factors()),
            index=list(factors()).index(r["category"]) if r["category"] else 0,
        )
        allow = st.checkbox("Use this text and label to update my local model")
        if st.button(
            "Save correction", disabled=not allow or st.session_state.research_locked
        ):
            item = {"text": text, "category": corrected}
            if item not in st.session_state.research_corrections:
                st.session_state.research_corrections.append(item)
            st.success(
                "Local training correction saved. The frozen benchmark is unchanged."
            )
        st.caption(
            "Local model training hash: "
            + predict(text, st.session_state.research_corrections)["model_hash"]
        )
    report = evaluate()
    st.subheader("Precision and recall on the frozen development set")
    st.warning(report["scope"])
    st.caption(
        f"{report['train_n']} training descriptions; {report['test_n']} held-out descriptions; 2 held-out examples per class. Template/vocabulary overlap makes this an optimistic smoke test, not a real receipt benchmark."
    )
    st.dataframe(pd.DataFrame(report["metrics"]), hide_index=True, width="stretch")
    with st.expander("Inspect every labelled benchmark example"):
        st.json(DATA)
    consent = st.checkbox(
        "Include my saved correction text in a downloaded training file"
    )
    if consent:
        st.download_button(
            "Download labelled corrections",
            json.dumps(st.session_state.research_corrections, indent=2),
            "shopimpact-local-corrections.json",
            "application/json",
        )


def lifecycle_page():
    header(
        "Lifespan and replacement",
        "Service-life assumptions make price-only comparisons less misleading.",
    )
    reference = st.selectbox(
        "Manufacturer reference", references(), format_func=lambda r: r["name"]
    )
    cost = st.number_input(
        "Purchase cost (your native currency)", min_value=0.0, value=100.0
    )
    currency = st.selectbox("Cost currency", ["INR", "USD", "EUR", "GBP"])
    years = st.number_input(
        "Expected years of use (your assumption)",
        min_value=0.1,
        max_value=100.0,
        value=5.0,
    )
    uses = st.number_input(
        "Uses per year (your assumption)",
        min_value=1.0,
        max_value=100000.0,
        value=365.0,
    )
    result = lifespan(reference["lca_kg"], cost, years, uses)
    st.metric(
        "Allocated footprint per expected year",
        f"{result['kg_per_year']:.2f} kg CO₂e/year",
    )
    st.metric("Cost per expected use", f"{result['cost_per_use']:.2f} {currency}")
    st.caption(
        "Annual allocation of a fixed published full-life-cycle figure. Changing expected lifespan does not re-model the LCA use phase. Native cost calculations do not substitute for native-region emissions factors."
    )
    st.subheader("Keep versus replace")
    embodied = st.number_input(
        "Replacement embodied emissions (kg, supply your source)",
        min_value=0.0,
        value=0.0,
    )
    old = st.number_input(
        "Old device electricity (kWh/year)", min_value=0.0, value=100.0
    )
    new = st.number_input(
        "Replacement electricity (kWh/year)", min_value=0.0, value=50.0
    )
    grid = st.number_input(
        "Grid factor (kg CO₂e/kWh, supply your source)",
        min_value=0.0,
        value=0.0,
        step=0.01,
    )
    source = st.text_input("Source URL and year for embodied/grid assumptions")
    if embodied > 0 and grid > 0 and source.strip():
        r = break_even(embodied, old, new, grid)
        st.write(
            "Break-even: "
            + (
                f"{r['years']:.2f} years"
                if r["years"] is not None
                else "none under these assumptions"
            )
        )
        st.caption(r["limits"])
    else:
        st.info(
            "Enter sourced embodied emissions and a grid factor to calculate a break-even. No default measurement is fabricated."
        )


def feedback_page():
    header(
        "Research feedback",
        "A short consent-based form. No name, email or purchase text is requested.",
    )
    st.info(
        "This form saves in this browser and offers an anonymous JSON download for a researcher. It is not a connected central response database. Use the Feedback link in Impact Lab to return here."
    )
    with st.form("study_feedback"):
        task = st.selectbox(
            "Task attempted",
            [
                "Log a purchase",
                "Understand uncertainty",
                "Compare methods",
                "Use the planner",
                "Other",
            ],
        )
        ease = st.slider("How easy was the task?", 1, 5, 3)
        trust = st.slider("How clearly were limitations explained?", 1, 5, 3)
        consent = st.checkbox(
            "I consent to storing these anonymous ratings here and downloading them for the study"
        )
        submitted = st.form_submit_button(
            "Save anonymous response", disabled=st.session_state.research_locked
        )
        if submitted:
            if not consent:
                st.error("Consent is required; no response was saved.")
            else:
                st.session_state.research_feedback.append(
                    {
                        "id": str(uuid.uuid4()),
                        "task": task,
                        "ease": ease,
                        "trust": trust,
                        "consent": True,
                        "version": VERSION,
                    }
                )
                st.success(
                    "Saved in this browser. Download and share it only if you choose."
                )
    if st.session_state.research_feedback:
        st.download_button(
            "Download my anonymous responses",
            json.dumps(st.session_state.research_feedback, indent=2),
            "shopimpact-feedback.json",
            "application/json",
        )
    st.subheader("Opt-in research export")
    include_amounts = st.checkbox(
        "Include purchase amounts in the research export (off by default)"
    )
    agree = st.checkbox(
        "I choose to export a de-identified copy for research; nothing is sent automatically"
    )
    if agree:
        rows = [
            {
                "category": r["category"],
                "month": r["date"][:7],
                "estimate_kg": r["estimate_kg"],
                "dataset_version": r["dataset_version"],
                **(
                    {
                        "amount": r["amount"],
                        "currency": r["currency"],
                        "price_year": r["price_year"],
                    }
                    if include_amounts
                    else {}
                ),
            }
            for r in st.session_state.research_records
        ]
        st.download_button(
            "Download opt-in research copy",
            json.dumps(
                {
                    "schema": 1,
                    "consent": True,
                    "records": rows,
                    "feedback": st.session_state.research_feedback,
                },
                indent=2,
            ),
            "shopimpact-research-opt-in.json",
            "application/json",
        )


def garden_page():
    from ui.common import render_svg, render_tilly
    from ui.illustrations import cached_garden_svg

    header("Garden", "Optional journal progress, separate from research evidence.")
    count = len(st.session_state.research_records)
    st.caption(
        f"{count} research entries recorded. Garden growth is playful feedback, not a measured environmental outcome."
    )
    render_tilly(
        "happy" if count else "curious",
        st.session_state.research_mode,
        st.session_state.research_motion,
    )
    level = min(8, count)
    render_svg(
        cached_garden_svg(
            level, st.session_state.research_mode, not st.session_state.research_motion
        ),
        "Turtle-drawn research journal garden",
        360,
        static_svg=cached_garden_svg(level, st.session_state.research_mode, False),
    )


def settings_page():
    header(
        "Settings",
        "Appearance, storage and project status. Model explanation lives in Method.",
    )
    st.caption(
        "Appearance and motion controls are in the sidebar. The ambient scene is off by default."
    )
    if st.session_state.research_locked and st.session_state.get("research_raw_saved"):
        st.download_button(
            "Download unmodified saved research data",
            st.session_state.research_raw_saved,
            "research-recovery.json",
            "application/json",
        )
    st.download_button(
        "Download full research backup",
        json.dumps(store_data(), indent=2),
        "shopimpact-research-backup.json",
        "application/json",
    )
    st.write(
        "Data availability: US EPA spend factors and three Apple LCA references. Missing: validated native India/EU factor releases and a real receipt benchmark."
    )
    st.warning(
        "Physical-phone testing, a full accessibility audit and the automated browser matrix are not yet verified. Deployment remains a separate step; no passing evidence is invented."
    )
    st.markdown(
        "Package: `python -m pip install ./core` · CLI: `shopimpact --category Smartphone --amount 799 --price-year 2023`"
    )
    st.caption(
        "Local deployments process data on your machine. Hosted Streamlit processes session inputs on its server; journal persistence is browser-local. No external emissions API, classifier API or central research collector is called."
    )
