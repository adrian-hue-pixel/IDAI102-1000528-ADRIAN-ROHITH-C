# ShopImpact implementation and evidence map

This records the existing ShopImpact brief, not an assertion of a teacher's final grade. The supplied CRS AI Y1C1 document is a different Dialogflow chatbot assignment.

- Purchase/plan inputs, price/date/brand/condition/packaging validation and live working: `views/home.py`, `logic.py`.
- Monthly spending, estimates, count, category and trend charts: `views/dashboard.py`, `charts.py`.
- Alternative suggestions, comparison and planning: `views/swaps_plan.py`, `plan_tools.py`.
- Turtle plant, footprint and garden drawings: `turtle_svg.py`, `turtle_art.py`, Home and Garden views.
- Tilly, earned badges and optional journal-based progress: `tilly_svg.py`, `gamification.py`, `views/garden_badges.py`.
- Journal edits, undo, recurrence, CSV import/export and saved state: `views/purchases.py`, `ui/undo.py`, `purchase_series.py`, `data_io.py`, browser persistence modules.
- Monthly reflection, raster/PDF snapshots and report export: `views/month_review.py`, `summary_image.py`.
- Inspectable constrained planner, one-factor sensitivity analysis, source coverage and reproducible JSON: `impact_lab.py`, `views/impact_lab.py`.
- Responsive sidebar, exactly Light/Dark modes, visible focus, ambient animation and reduced motion: `ui/common.py`, `ui/studio.py`, `styles.py`, `studio.css`.
- Full backup preview/restore, accessibility preferences, model limits and privacy explanation: `views/settings_about.py`.

Home's Log a purchase action jumps directly to purchase inputs; the monthly snapshot and narrow Tilly/drawing companion column follow the input workspace. All eight routes initialize shared state through `app.py`, including direct URLs.

## Evidence still requiring the student

Supply identity and school details, the actual repository and deployed URL, the student's wireframe, real independent feedback, and physical-device/deployment verification. No user feedback, life-cycle measurement, institutional recognition or mark is invented.

Current automated and browser verification is recorded in `docs/REDESIGN_2026.md`. Earlier captures in `docs/screenshots/` are historical unless named `studio-*`.
