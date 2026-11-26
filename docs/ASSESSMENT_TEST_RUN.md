# Assessment test run — 12 purchases

## Scope and method

Executed a fresh, deterministic test on the repository's current everyday Python logic on 26 November 2026. The test enters 12 individually specified synthetic purchases through the same `add_purchase` function used for journal validation and insertion. These are deliberately invented test inputs, not actual shopping records or a hosted browser test. The mixture includes low and high prices, three conditions, packaging choices and low, medium and high model ratings.

Reproduce from the project root:

```bash
python tests/run_assignment_scenario.py
```

## Observed results

| # | Category | Condition | Minimal packaging | USD | kg CO₂e | Rating |
|---:|---|---|---|---:|---:|---|
| 1 | Clothing | New | No | 25.00 | 13.750 | Medium |
| 2 | Clothing | Second-hand | Yes | 20.00 | 1.485 | Low |
| 3 | Leather Shoes | New | No | 120.00 | 114.000 | High |
| 4 | Books & Stationery | Second-hand | Yes | 8.00 | 0.288 | Low |
| 5 | Laptop / Computer | New | No | 900.00 | 495.000 | Medium |
| 6 | Smartphone | Refurbished | No | 250.00 | 50.625 | Low |
| 7 | Groceries - Meat & Dairy | New | No | 45.00 | 72.000 | High |
| 8 | Groceries - Plant-based | New | Yes | 30.00 | 10.800 | Medium |
| 9 | Cleaning Products | New | Yes | 9.00 | 2.430 | Medium |
| 10 | Coffee & Tea | New | No | 12.00 | 6.600 | Medium |
| 11 | Furniture | Second-hand | No | 80.00 | 7.200 | Low |
| 12 | Cosmetics & Personal Care | New | Yes | 15.00 | 4.725 | Medium |

- Count: **12**
- Total spent: **$1,514.00**
- Estimated footprint: **778.90 kg CO₂e**
- Earned badges: **First Step** and **Second-Life Hero**, using an 80 kg illustrative goal.
- Result: **PASS**. All twelve additions, running totals, formula comparisons, category alternatives, empty month and four rejected invalid prices passed; badge identifiers also matched the expected set.

The high-priced laptop dominates the estimated total in this test. Second-hand items receive smaller illustrative model factors. These outcomes are a property of the model and do not establish actual emissions savings.

## Creative features and earlier verified refinement

The [historical test log](test_log.md) records real local browser testing, visual captures, reduced-motion behavior, event-specific sprout replay, validation improvements, responsive grid fixes, improved navigation and undo. These historical observations should not be treated as a fresh hosted-app audit. The [design plan](ASSESSMENT_DESIGN.md) maps these features to user needs and the assignment.

## Remaining live and usability evidence

| Check | Status |
|---|---|
| 12 sequential additions and totals | Passed, current logic |
| Invalid prices rejected without modifying journal | Passed, current logic |
| Badge awards and category suggestions | Passed, current logic |
| Turtle graphics and responsive pages | Earlier local browser evidence in the test log |
| Current deployed app: all eight routes, live update, low-impact animation, refresh, light/dark and mobile | Fresh browser check still required |
| Five people independently try the app and report recommendations | Pending; [review log](USABILITY_FEEDBACK.md) |

No screenshots or testimonials are fabricated. The current run tests the model, not the rendering or deployed service.
