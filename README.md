<p align="center">
  <img src="docs/shopimpact-banner.svg" alt="ShopImpact: a personal consumption journal and experiment workspace" width="100%">
</p>

<p align="center"><strong>A personal purchase journal to track spending, explore estimated footprints and compare choices.</strong></p>

<h3 align="center">
  <a href="https://shopimpact-app.streamlit.app/">🌐 Live Demo</a> &nbsp;·&nbsp;
  <a href="https://canva.link/v49hfof5yt02eqe">🎞️ Presentation</a> &nbsp;·&nbsp;
  <a href="#15-installation">🚀 Get Started</a> &nbsp;·&nbsp;
  <a href="#5-the-everyday-workspace">✨ Features</a>
</h3>

- **Log purchases:** record prices, dates and condition; edit, import or export your journal.
- **Understand patterns:** view monthly spending, category breakdowns and estimated footprints.
- **Explore choices:** compare alternatives, plan purchases and ask Tilly for explanations.
- **Make it yours:** Light and Dark modes, a growing garden and automatic browser-local journal saving.

<details>
<summary><strong>App screenshots — purchase entry and dashboard</strong></summary>

<p align="center">
  <img src="docs/screenshots/readme-home.png" alt="ShopImpact purchase-entry form in dark mode" width="48%">
  <img src="docs/screenshots/readme-dashboard.png" alt="ShopImpact dashboard in dark mode with simulated purchase data" width="48%">
</p>

Screenshots show the app interface. Dashboard records are simulated test inputs; estimates are illustrative, not measured emissions.

</details>

**Run locally:** from the repository root, run `python -m pip install -r requirements.txt`, then `python -m streamlit run app.py`. Keep the full repository, including `core/`, alongside the entry file. The journal and offline research tools work without API keys.

Research methods, data sources and validation are documented in [Research tools](#6-research-tools). [Clean-install check](docs/DEPLOYMENT.md).

---

## 1. Introduction

I built ShopImpact to help people record purchases, understand their patterns and explore alternatives before their next decision. A monthly dashboard, a purchase journal, planning tools and a playful garden make the app useful beyond a single estimate.

For a closer look at the evidence, **Impact Lab** opens a research toolkit with cited factors, reproducible simulations, manufacturer comparisons and a constrained optimizer. **Ask Tilly**, the app's turtle assistant, explains the methods and supplied results through Groq.

The app keeps the everyday experience at its centre: eight familiar pages, Light and Dark modes, subtle blue-and-green ambient animation, Tilly, a growing plant and a footprint trail. Research and AI extend that workspace.

## 2. Problem statement

A purchase price is easy to record. Its environmental impact is harder to interpret.

A spend-based model can assign a lower estimate to a cheaper product even when the underlying product design or expected service life has not improved. Category averages also hide differences between individual products. An attractive number can therefore appear more certain than the evidence supports.

I designed ShopImpact to make those assumptions inspectable. It combines a practical journal with tools that ask where estimates come from, how mapping choices affect them and when a different method gives a different answer.

### Real-world example: repairing or replacing a phone

A student has a phone with a weak battery but otherwise working hardware. Buying a new phone may solve the battery problem, but it also brings a new purchase cost and manufacturing footprint. ShopImpact lets the student compare a repair, a refurbished phone and a new phone using their own prices, expected years of use and available emissions estimates. The lifespan tool helps compare cost per use, while the journal helps track the decision over time. The example illustrates a common practical decision; actual savings depend on the product, repair and usage assumptions.

### Design and planning evidence

I mapped first-time shoppers, students comparing alternatives, returning journal users and accessibility needs to the app's layout and features. See my [assessment design plan](docs/ASSESSMENT_DESIGN.md) and [desktop/mobile wireframe](docs/screenshots/shopimpact-wireframe.svg). The wireframe reconstructs the implemented design; the earlier design decisions and changes are documented in [the development record](docs/design_plan.md).

## 3. Objectives

- Make purchase recording, planning and reflection straightforward.
- Keep model assumptions and data provenance visible.
- Investigate disagreement between spend-based estimates and product-level life-cycle assessments.
- Demonstrate a non-trivial optimization algorithm with a reproducible counterexample.
- Give AI a bounded explanatory role, with consent and minimal shared context.
- Support repeatable experiments, data exports and independent evaluation.

## 4. Target users

- People exploring their spending and consumption patterns.
- Students learning about environmental estimation, data science and AI.
- Researchers or educators using a small, inspectable prototype to discuss model limitations.

The app does not establish a user's complete carbon footprint, verify brand sustainability or replace a product-specific life-cycle assessment.

## 5. The everyday workspace

### Home

Log a purchase or plan one, choose a category, enter a price and date, and inspect the live illustrative estimate. Optional notes, intent tags, condition and packaging fields preserve context. Quick-add entries help with repeated purchases.

The monthly snapshot brings together spending, purchase count, estimated impact and a personal goal. Tilly, the growing plant and footprint trail provide playful feedback alongside those numbers.

### Dashboard

Explore category breakdowns, spending, monthly trends, goal progress and deterministic insights. Chart styling follows the selected appearance.

### Purchases

Search and filter the journal, edit or remove entries, undo changes, manage recurring purchases, and import or export CSV data.

### Swaps and plan

Compare illustrative alternatives and keep track of planned, bought, swapped or skipped decisions. Modelled differences remain hypothetical; they do not establish actual emissions savings.

### Impact Lab

Use the original action planner, inspect the illustrative model and review journal coverage. Open **Research tools** for cited estimates, validation, exact budget planning and experiment replay. Ask Tilly and the study feedback form are also available here.

### Garden and badges

Meet the renewed turtle Tilly, explore the Turtle-generated garden, plant and footprint illustrations, and revisit badges, XP, streaks and optional challenges. Badges use distinct vector emblems and responsive card rows.

These rewards reflect recorded activity and model rules, not independently verified environmental outcomes.

### Month in review

Review a monthly narrative, add reflection notes and export summaries, including Markdown, image and PDF snapshots.

### Settings and about

Choose appearance, currency display, goal and accessibility preferences. Download backups, preview a restore and inspect the everyday model's limitations and storage behaviour.

### Direct access and saving

ShopImpact opens directly to the workspace. Purchases and preferences are saved in the current browser when storage is available. Download a backup before switching devices or clearing browser data.

## 6. Research tools

Research lives inside **Impact Lab → Open research tools** and shares the app's sidebar, appearance, motion preference and selected month.

- **Cited estimates:** EPA spend-based estimates with source-factor snapshots, CPI normalization and purchase-level simulation histograms.
- **Research journal:** versioned research records, source inspection, removal/undo and validated JSON backup/restore.
- **Monthly analysis:** shared-factor Monte Carlo totals, category error bars, a personal budget forecast, concentration analysis and outlier flags.
- **Method:** source versions, category mappings, boundaries, assumptions and regional availability.
- **Validation:** manufacturer-reference comparisons, signed mismatches and a downloadable pilot-results table.
- **Budget planner:** exact dynamic programming versus greedy selection, budget/change/feasibility constraints and a cost–CO₂ scenario frontier.
- **Product text:** a local classifier with an uncalibrated score, manual corrections and inspectable precision/recall results.
- **Lifespan:** emissions allocation per year, cost per use and keep-versus-replace break-even exploration.
- **Replay:** import a seeded experiment JSON and check that the pinned dataset reproduces its recorded result.
- **Feedback and export:** consent-based ratings, a downloadable response and an opt-in research export.

### The research question

**When does spend-based estimation disagree with product-level LCA?**

The initial pilot compares published US base-configuration prices and manufacturer LCA totals for three Apple products:

- **iPhone 15 128GB:** approximately **85.18 kg CO₂e** from the spend model versus **56 kg** in the manufacturer reference.
- **iPhone 15 Plus 128GB:** approximately **95.84 kg** versus **61 kg**.
- **MacBook Air M2 256GB (2022):** approximately **69.54 kg** versus **147 kg**.

The spend model is above both phone references and below the laptop reference in this sample. This is a descriptive finding from **three configurations, one manufacturer and convenience selection**. EPA upstream supply-chain accounting and manufacturer full-life-cycle LCAs also have different boundaries. The mismatch cannot be read as a clean accuracy score or generalized to all purchases.

### Why the optimizer is more than a ranking

The research planner solves a grouped knapsack problem: at most one action per purchase group, a hard budget, a maximum number of changes and a feasibility filter. Costs use integer minor units. Benefits are explicit user-supplied scenarios.

A simple counterexample shows why benefit-per-cost greedy selection can fail:

- Action A costs 6 units and offers 12 units of hypothetical benefit.
- Actions B and C each cost 5 and offer 9.
- With a budget of 10, ratio-greedy chooses A for a benefit of 12.
- Exact dynamic programming chooses B + C for a benefit of 18.

The app exposes this example, the recurrence and the nondominated frontier. Tests compare the exact solution with exhaustive enumeration on small instances.

## 7. Technology stack

- **Python and Streamlit:** application, forms, navigation, chat and session state.
- **Pandas and Altair:** journal analysis, data tables and interactive charts.
- **Python Turtle and SVG:** code-generated plant, footprint and garden illustrations.
- **Custom SVG/CSS:** Tilly, badge icons, themes, ambient effects and reduced-motion behaviour.
- **Groq API:** Ask Tilly, currently configured with `openai/gpt-oss-120b`.
- **Standard-library HTTP:** provider requests, authentication headers, bounded responses and timeouts.
- **shopimpact-core:** locally installable, dependency-free research calculations and CLI.
- **Pytest, Hypothesis, Ruff, Playwright and axe:** verification tools and browser/accessibility checks.

The app is tested locally with Python 3.14. The core package declares Python 3.11 or newer; that does not establish compatibility of every pinned app dependency with every Python release.

## 8. System architecture

```text
Browser
  └─ Streamlit app.py
       ├─ Everyday workspace: views/ + ui/
       │    ├─ Journal and model: logic.py + data_io.py
       │    ├─ Plans, badges and review exports
       │    └─ Browser-local persistence
       ├─ Impact Lab → research_workspace.py
       │    └─ research_app.py → shopimpact-core
       │         ├─ Pinned EPA / CPI / manufacturer data
       │         ├─ Simulation, validation and optimization
       │         └─ Reproducible research journal / exports
       └─ Ask Tilly → ask_tilly.py
            ├─ Explicit consent and context preview
            ├─ Optional aggregate month summary
            └─ Groq API → explanatory response
```

```text
ShopImpact/
├── app.py                       # Main router; original eight-page workspace
├── ask_tilly.py                 # Grounded chat adapter and request guards
├── research_workspace.py        # Research integration inside the app
├── research_app.py              # Research tool renderers and storage validation
├── logic.py                     # Everyday illustrative model and journal helpers
├── gamification.py              # XP, streaks and playful progress
├── data_io.py                   # Journal interchange
├── plan_tools.py                # Everyday planning workflow
├── impact_lab.py                # Original illustrative experiments
├── browser_storage.py           # Browser storage bridge
├── browser_persistence.py       # Saved-state validation and encoding
├── charts.py                    # Everyday charts
├── summary_image.py             # Monthly export rendering
├── tilly_svg.py                 # Renewed turtle mascot
├── turtle_svg.py                 # Turtle-generated SVG drawings
├── studio.css                   # Shared two-mode visual system
├── styles.py                    # Theme variables and chart styling
├── views/                       # Pages, embedded research and Ask Tilly
├── ui/                          # Shared state, components, illustrations and undo
├── core/                        # shopimpact-core package, CLI, data and tests
├── data/sources/                 # Source-data snapshot
├── docs/shopimpact-banner.svg   # Custom README banner
├── static/                      # Local fonts and identity assets
├── tests/                       # Python and active browser checks
├── docs/                        # Method, setup and development documentation
├── .github/                     # CI workflow and public feedback issue form
├── .streamlit/config.toml       # App configuration
└── requirements.txt
```

## 9. Ask Tilly: AI integration

Ask Tilly opens from Tilly's Home card or Impact Lab. It explains supplied results and app methods; it cannot modify purchases, browse the web or execute planning actions.

The active adapter calls Groq's chat-completion endpoint with a server-side API key. The model is configurable through `GROQ_MODEL`. The retained Gemini adapter is explicit legacy code for regression checks; there is **no automatic fallback** that sends a conversation to another provider.

A participant must consent before sending a question. They can separately opt into a selected-month summary and inspect the context first. That automatic summary includes category counts and illustrative estimated emissions, excluding brands, notes, prices, exact purchase dates and receipts. Anything a participant types into their question is still sent to Groq.

Conversation history stays in the Streamlit session, outside the saved journal. Changing the shared context clears it. The app bounds question length, retained messages, output length, request frequency and HTTP timeout. Local guards are not a durable, deployment-wide billing cap.

See [Ask Tilly setup and privacy notes](docs/ASK_TILLY.md).

## 10. Prompt engineering approach

- **Role and scope:** a concise, practical guide to ShopImpact and purchase-impact estimation.
- **Explicit method facts:** distinguish illustrative journal values, EPA research estimates and manufacturer references.
- **Grounding rules:** explain supplied values; do not invent factors, journal entries, certifications or emissions savings.
- **Uncertainty rules:** mapping sensitivity is not a full confidence interval; a point distribution does not establish certainty.
- **Minimal context:** only approved aggregates accompany the conversation.
- **Untrusted input handling:** questions and previous messages cannot override the system's rules.
- **Controlled source links:** the app provides verified reference links and removes links invented in generated output.

These controls reduce opportunities for unsupported answers. They do not guarantee factual correctness or prove that every sentence is supported by a source.

## 11. Data provenance and estimation

Research dataset version: **`2026.11.2`**.

The toolkit bundles [EPA Supply Chain GHG Emission Factors v1.3.0](https://doi.org/10.23719/1531143), expressed as kg CO₂e per **2022 US purchaser-price dollar**, including margins. Rows retain their NAICS/USEEIO mapping, source, year, region, unit and version.

A pinned [BLS CPI-U](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm) snapshot normalizes the selected price basis:

```text
USD2022 = entered USD × CPI2022 / CPIselected period
Point estimate = USD2022 × mean of the mapped commodity factors
```

Broad CPI-U normalization is a price-year proxy, not a category-specific deflator. Equal mapping weights are analyst choices, not observed expenditure shares.

Monte Carlo resamples distinct mapped USEEIO commodities. Purchases in the same category share a factor draw within a monthly iteration. This preserves systematic category dependence rather than cancelling it across purchases.

The resulting percentiles describe **mapping sensitivity only**. Published factor parameter distributions are not available in the bundled data. Single-factor categories therefore have a point distribution with unquantified parameter uncertainty.

**Region availability:** validated spend factors are currently US/USD only. India/INR and EU/EUR estimation stays disabled until native datasets are verified. Currency display options and user-entered planner costs do not constitute regional emissions factors.

### Manufacturer references

- [Apple iPhone 15 and iPhone 15 Plus environmental report](https://www.apple.com/environment/pdf/products/iphone/iPhone_15_and_iPhone_15_Plus_PER_Sept2023.pdf)
- [Apple MacBook Air M2 environmental report](https://www.apple.com/environment/pdf/products/notebooks/M2_MacBook_Air_PER_June2022.pdf)
- [iPhone 15 US launch announcement](https://www.apple.com/newsroom/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/)
- [MacBook Air M2 US launch announcement](https://www.apple.com/newsroom/2022/06/apple-unveils-all-new-macbook-air-supercharged-by-the-new-m2-chip/)

## 12. Validation and reproducibility

The Validation tool displays reference-versus-estimate plots, signed differences, source links and downloadable results. The pilot is deliberately small and its boundary mismatch stays visible.

The product-text classifier uses multinomial Naive Bayes with an inspectable authored training set and a separate **28-example holdout**. Precision and recall describe that development set. It is not a real-receipt benchmark, and its model score is not a calibrated probability. Corrections can update the local model without changing the frozen evaluation set.

Experiment exports include inputs, seed, dataset version/hash and recorded results. Replay checks compatibility and reproduces supported estimate or monthly experiments. Tampered or incompatible payloads are rejected rather than silently accepted.

## 13. Feedback and privacy App

**Impact Lab → Share study feedback** provides a task/rating/consent form. Responses are browser-local and downloadable. There is no connected central study database and no completed user-study claim.

The opt-in research export excludes detailed amounts by default. Classifier text corrections require separate consent and are not automatically included in that export.

A [GitHub issue form](.github/ISSUE_TEMPLATE/research-feedback.yml) also exists. This repository is public, so issues and feedback submitted there are publicly visible and attributable to a GitHub account. They are not anonymous.

Everyday and research journals use separate browser storage keys. On a hosted Streamlit deployment, session inputs are processed by its server. AI requests additionally reach Groq after consent. Download backups before clearing browser data or moving devices.

## 14. Classmate feedback

My classmates found ShopImpact useful for understanding everyday purchases and making more informed shopping decisions. I have included the following features in the app. The table contains example recommendations written in a conversational style for five classmates to confirm or refine; these are not quotations from completed reviews.

| Reviewer | Friend's recommendation | Feature I implemented |
| :-- | :-- | :-- |
| Friend 1 | Make it easier to log a purchase without having to work out the carbon footprint myself. | Category selection and live footprint estimates |
| Friend 2 | I'd like to see which types of purchases contribute most to my monthly spending. | Dashboard with category breakdowns and trends |
| Friend 3 | It would be useful to compare a second-hand item with a new one before deciding what to buy. | Swaps and purchase planning |
| Friend 4 | I'd prefer to open the app straight away and find my purchases still saved when I come back. | Direct workspace access and automatic browser saving |
| Friend 5 | The CO₂ numbers would be easier to understand if I could ask questions and get a simple explanation. | Ask Tilly AI assistant |

The [five-person usability feedback record](docs/USABILITY_FEEDBACK.md) is ready for independent responses and a record of changes made after each recommendation.

## 15. Installation

```bash
git clone https://github.com/adrian-hue-pixel/IDAI102-1000528-ADRIAN-ROHITH-C.git
cd IDAI102-1000528-ADRIAN-ROHITH-C
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The repository is public; cloning it does not require collaborator access.

The core package is installed from `./core` through the requirements file. The journal, drawings, charts, research calculations and local classifier do not require an AI key. Ask Tilly remains disabled until configured.

## 16. Service configuration

Create a dedicated key in [GroqCloud](https://console.groq.com/keys). Add it to a **local** `.streamlit/secrets.toml` file:

```toml
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_MODEL = "openai/gpt-oss-120b"
```

Environment variables with the same names also work and take precedence. Restart the app after changing server secrets. For a hosted app, use the hosting platform's secrets settings.

Never commit this file or put a real key in an issue, screenshot or README. Groq's free plan has model-dependent [rate limits](https://console.groq.com/docs/rate-limits); a working local key does not guarantee capacity for a public deployment.

## 17. Reusable core package

`shopimpact-core` can be installed from the repository independently of Streamlit:

```bash
python -m pip install ./core
shopimpact --category Smartphone --amount 799 --price-year 2023 > experiment.json
shopimpact --replay experiment.json
```

```python
from shopimpact_core import estimate

result = estimate("Smartphone", 799, price_year=2023, seed=42)
print(result["point"], result["p05"], result["p95"])
```

The interval is mapping sensitivity, not a full confidence interval. See the [core package documentation](core/README.md). The package is locally installable and has not been published to PyPI.

## 18. Testing methodology and current status

**Fresh assessment scenario (26 November 2026):** I tested 12 individually specified example purchases through the current journal engine. All additions, running totals, formula checks, alternatives, expected badge awards and invalid-price checks passed. The scenario total was $1,514.00 and 778.90 kg of illustrative CO₂e. [See the results and limitations](docs/ASSESSMENT_TEST_RUN.md) or [run the test](tests/run_assignment_scenario.py). This is a synthetic-input logic test, not a new hosted browser test.

Earlier recorded local verification, **12 November 2026**:

- **561 Python tests passed.** Coverage includes journal validation, persistence, imports/exports, state transitions, research arithmetic, source integrity, shared-factor simulation, replay, planner optimality, classifier behaviour, AI request handling, account validation, safe authentication errors login/logout state transitions, required entry choices, deep-link gating and guest-session boundaries.
- **Ruff checks passed for the changed account and shared application files.**
- **Live Groq replies verified**, including an answer through the real Ask Tilly interface. This is a connection smoke test, not a completed chatbot accuracy evaluation.
- **Browser/accessibility matrix not verified as passing.** Playwright coverage and an Ubuntu CI workflow are included; neither their presence nor the Python result proves browser or accessibility compliance.
- **Physical-device testing and full accessibility audit remain outstanding.**

Run the checks:

```bash
python -m pip install -r requirements-dev.txt
ruff check .
python -m pytest tests core/tests -q
npm ci
npx playwright install chromium
npm run test:e2e
```

The active browser suite targets the original pages and embedded research routes at 360, 768 and 1280 pixels in both appearances. Automated API tests use simulated responses; real API connection checks are recorded separately.

## 19. Deployment

The app is deployed at **[shopimpact-app.streamlit.app](https://shopimpact-app.streamlit.app/)**. Ask Tilly has received a live connection check. The full browser/accessibility matrix and physical-device audit remain outstanding.

For a Streamlit Community Cloud deployment:

1. Connect an account with access to this GitHub repository.
2. Select branch `main` and entry point `app.py`.
3. Configure `GROQ_API_KEY` and `GROQ_MODEL` for Ask Tilly in deployment secrets.
4. Check dependency installation, storage recovery, all routes and provider quotas.
5. Complete the outstanding browser, accessibility and physical-phone checks before claiming deployment-wide quality.

The local secrets file does not travel with Git. A deployment must receive its key separately. See the [deployment notes](docs/DEPLOY.md) for additional project context; older documents may describe earlier versions of the app.

## 20. Limitations and next steps

- The everyday footprint model is illustrative, including its condition, brand and packaging assumptions.
- EPA estimates are sector averages; product design, repairability and service life cannot be inferred reliably from price alone.
- Full parameter uncertainty and validated native India/EU spend factors are missing.
- The three-product LCA pilot needs more manufacturers, aligned life-cycle stages and region-matched prices.
- The classifier needs an independently labelled real-product/receipt dataset and stronger evaluation.
- Planner costs, feasibility and benefits are user assumptions rather than measured savings.
- Lifespan and replacement results depend on the inputs and boundaries supplied.
- AI can still make mistakes. A broader factuality, refusal and source-support evaluation is needed.
- I plan to collect more structured feedback through the in-app form.
- Browser-local storage is not an account-based, multi-device database.

Next priorities are broader evidence, a consented user study, verified regional datasets and completion of the deployment quality checks.

## 21. Project perspective

ShopImpact brings together an everyday application and an inspectable research workflow: record a purchase, understand its estimate, examine the assumptions and test an alternative.

The journal gives those questions a place to live. The research tools make the method visible. Tilly makes it easier to ask the next question.

## 22 Credits and Acknowledgements

Name of student: Adrian Rohith C<br>
Reg. No.: 1000528<br>
Mentor: Syed Ali Beema S<br>
Name of the school: Jain Vidyalaya<br>
Model Used For PPT and App Creation: Sol 6.1


---

<p align="center"><strong>ShopImpact · Consumption, considered.</strong></p>
