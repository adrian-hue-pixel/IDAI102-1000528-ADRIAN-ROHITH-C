"""Small multinomial NB baseline, with a separate frozen curated holdout."""

import collections
import hashlib
import json
import math
import re

DATA = {
    "Clothing": (
        ["cotton shirt", "wool sweater", "denim jeans", "linen dress"],
        ["cotton hoodie", "denim jacket"],
    ),
    "Leather Shoes": (
        ["leather boots", "leather loafers", "suede shoes", "leather sandals"],
        ["suede boots", "leather brogues"],
    ),
    "Sneakers": (
        ["running sneakers", "sports trainers", "canvas sneakers", "athletic trainers"],
        ["running trainers", "sports sneakers"],
    ),
    "Smartphone": (
        ["iphone phone", "android smartphone", "samsung handset", "mobile phone"],
        ["android handset", "iphone smartphone"],
    ),
    "Laptop / Computer": (
        ["macbook laptop", "dell computer", "lenovo notebook", "desktop computer"],
        ["dell laptop", "macbook notebook"],
    ),
    "Home Appliance": (
        [
            "washing machine",
            "electric refrigerator",
            "kitchen toaster",
            "dishwasher appliance",
        ],
        ["kitchen refrigerator", "electric toaster"],
    ),
    "Furniture": (
        ["wooden table", "office chair", "bedroom wardrobe", "dining furniture"],
        ["dining table", "wooden chair"],
    ),
    "Groceries - Meat & Dairy": (
        ["chicken meat", "beef steak", "dairy milk", "cheddar cheese"],
        ["chicken steak", "dairy cheese"],
    ),
    "Groceries - Plant-based": (
        ["fresh apples", "organic lentils", "fresh carrots", "organic beans"],
        ["organic carrots", "fresh lentils"],
    ),
    "Books & Stationery": (
        ["paper notebook", "printed book", "stationery pencil", "paper journal"],
        ["printed journal", "stationery notebook"],
    ),
    "Cosmetics & Personal Care": (
        ["face cream", "hair shampoo", "skin moisturizer", "face cleanser"],
        ["skin cream", "hair cleanser"],
    ),
    "Cleaning Products": (
        [
            "floor detergent",
            "surface disinfectant",
            "laundry detergent",
            "floor cleaner",
        ],
        ["laundry cleaner", "surface detergent"],
    ),
    "Toys & Games": (
        ["board game", "puzzle toy", "building blocks", "plush toy"],
        ["building toy", "puzzle game"],
    ),
    "Coffee & Tea": (
        ["roasted coffee", "black tea", "ground coffee", "green tea"],
        ["roasted tea", "ground tea"],
    ),
}


def tokens(text):
    return re.findall(r"[a-z]+", text.lower())


def train(corrections=()):
    counts = {k: collections.Counter() for k in DATA}
    docs = collections.Counter()
    vocab = set()
    heldout = {t for _, tests in DATA.values() for t in tests}
    rows = [(t, k) for k, (texts, _) in DATA.items() for t in texts]
    for r in corrections:
        if r["category"] not in DATA:
            raise ValueError("Unknown correction category.")
        if r["text"].lower().strip() in heldout:
            continue
        rows.append((r["text"], r["category"]))
    for text, k in rows:
        ts = tokens(text)
        counts[k].update(ts)
        docs[k] += 1
        vocab.update(ts)
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    return {"counts": counts, "docs": docs, "vocab": vocab, "hash": digest}


def predict(text, corrections=()):
    if not isinstance(text, str) or len(text) > 10000:
        raise ValueError("Text must be at most 10,000 characters.")
    model = train(corrections)
    ts = tokens(text)
    scores = {}
    overlap = len(set(ts) & model["vocab"])
    for k in DATA:
        counts = model["counts"][k]
        scores[k] = math.log(model["docs"][k] / sum(model["docs"].values())) + sum(
            math.log((counts[t] + 1) / (sum(counts.values()) + len(model["vocab"])))
            for t in ts
        )
    peak = max(scores.values())
    prob = {k: math.exp(v - peak) for k, v in scores.items()}
    total = sum(prob.values())
    prob = {k: v / total for k, v in prob.items()}
    best = max(prob, key=prob.get)
    return {
        "category": best if overlap else None,
        "score": prob[best],
        "abstained": not overlap,
        "scores": prob,
        "model_hash": model["hash"],
        "calibrated": False,
    }


def evaluate():
    pairs = [
        (k, predict(t)["category"]) for k, (_, texts) in DATA.items() for t in texts
    ]
    metrics = []
    for k in DATA:
        tp = sum(a == k and b == k for a, b in pairs)
        fp = sum(a != k and b == k for a, b in pairs)
        fn = sum(a == k and b != k for a, b in pairs)
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        metrics.append(
            {
                "category": k,
                "precision": precision,
                "recall": recall,
                "support": sum(a == k for a, b in pairs),
            }
        )
    return {
        "test_n": len(pairs),
        "train_n": sum(len(v[0]) for v in DATA.values()),
        "accuracy": sum(a == b for a, b in pairs) / len(pairs),
        "metrics": metrics,
        "scope": "Author-curated short-text smoke benchmark; template vocabulary overlaps. NOT real-receipt validation. Corrections are never used to fit this reported benchmark.",
    }
