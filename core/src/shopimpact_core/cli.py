"""Offline reproducible estimate CLI."""

import argparse

from .model import replay, replay_export


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="Smartphone")
    parser.add_argument("--amount", type=float, default=799)
    parser.add_argument("--price-year", type=int, default=2023)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--replay")
    args = parser.parse_args()
    if args.replay:
        import json
        from pathlib import Path

        print(json.dumps(replay(Path(args.replay).read_text()), indent=2))
    else:
        print(
            replay_export(
                {
                    "category": args.category,
                    "amount": args.amount,
                    "price_year": args.price_year,
                    "seed": args.seed,
                }
            )
        )


if __name__ == "__main__":
    main()
