"""Exact grouped 0/1 knapsack with integer costs and a max-change constraint."""

import math
from decimal import Decimal, InvalidOperation


def cents(value):
    if isinstance(value, bool):
        raise TypeError("Boolean costs are invalid.")
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Cost must be a decimal number.") from exc
    if not d.is_finite() or d < 0 or d * 100 != (d * 100).to_integral_value():
        raise ValueError("Costs must be nonnegative with at most two decimal places.")
    return int(d * 100)


def eligible(actions, budget, max_changes, feasibility):
    budget = cents(budget)
    if (
        isinstance(max_changes, bool)
        or not isinstance(max_changes, int)
        or not 0 <= max_changes <= 20
    ):
        raise ValueError("Maximum changes must be 0–20.")
    if not math.isfinite(feasibility) or not 0 <= feasibility <= 1:
        raise ValueError("Feasibility must be 0–1.")
    if len(actions) > 40:
        raise ValueError("At most 40 candidate actions supported.")
    ids = []
    groups = {}
    for a in actions:
        if (
            not isinstance(a.get("id"), str)
            or not a["id"]
            or not isinstance(a.get("group"), str)
            or not a["group"]
        ):
            raise ValueError("Action and group IDs must be nonempty strings.")
        if a["id"] in ids:
            raise ValueError("Action IDs must be unique.")
        ids.append(a["id"])
        cost = cents(a["cost"])
        benefit = float(a["kg"])
        score = float(a["feasibility"])
        if (
            not all(math.isfinite(x) for x in [benefit, score])
            or benefit < 0
            or not 0 <= score <= 1
        ):
            raise ValueError("Invalid benefit or feasibility.")
        if score >= feasibility and benefit > 0 and cost <= budget:
            groups.setdefault(str(a["group"]), []).append({**a, "cents": cost})
    return budget, groups


def greedy(actions, budget, max_changes=3, feasibility=0):
    limit, groups = eligible(actions, budget, max_changes, feasibility)
    chosen = []
    used = set()
    cost = 0
    value = 0
    candidates = sorted(
        [a for g in groups.values() for a in g],
        key=lambda a: (
            -(a["kg"] / a["cents"] if a["cents"] else float("inf")),
            str(a["id"]),
        ),
    )
    for a in candidates:
        if (
            len(chosen) < max_changes
            and a["group"] not in used
            and cost + a["cents"] <= limit
        ):
            chosen.append(a["id"])
            used.add(a["group"])
            cost += a["cents"]
            value += a["kg"]
    return {"ids": chosen, "cost": cost / 100, "kg": value}


def optimize(actions, budget, max_changes=3, feasibility=0):
    limit, groups = eligible(actions, budget, max_changes, feasibility)
    states = {(0, 0): (0.0, ())}
    for group in sorted(groups):
        previous = states
        next_states = dict(previous)
        for (cost, count), (value, ids) in previous.items():
            for a in groups[group]:
                key = (cost + a["cents"], count + 1)
                if key[0] <= limit and key[1] <= max_changes:
                    candidate = (value + a["kg"], ids + (a["id"],))
                    if candidate[0] > next_states.get(key, (-1, ()))[0]:
                        next_states[key] = candidate
                        if len(next_states) > 250000:
                            raise ValueError(
                                "Exact state limit reached; reduce budget/actions."
                            )
        if len(next_states) > 250000:
            raise ValueError(
                "Exact state limit reached; reduce budget/actions, no approximation silently substituted."
            )
        states = next_states
    best = max(states, key=lambda k: (states[k][0], -k[0], -k[1]))
    frontier = []
    highest = -1
    cost_best = {}
    for (cost, _), (value, _) in states.items():
        cost_best[cost] = max(value, cost_best.get(cost, -1))
    for cost, value in sorted(cost_best.items()):
        if value > highest:
            frontier.append({"cost": cost / 100, "kg": value})
            highest = value
    return {
        "ids": list(states[best][1]),
        "cost": best[0] / 100,
        "kg": states[best][0],
        "frontier": frontier,
        "states": len(states),
    }


def counterexample():
    actions = [
        {"id": name, "group": name, "cost": cost, "kg": kg, "feasibility": 1}
        for name, cost, kg in [("A", 6, 12), ("B", 5, 9), ("C", 5, 9)]
    ]
    return {
        "actions": actions,
        "budget": 10,
        "greedy": greedy(actions, 10),
        "dp": optimize(actions, 10),
    }
