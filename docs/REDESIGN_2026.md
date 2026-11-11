# ShopImpact studio refresh November 2026

## Product and visual changes

The current release has eight workspaces, a compact sidebar and exactly two appearances: Light and Dark. It replaces the earlier top bar and three-mode presentation. `studio.css` is the only active stylesheet; old stylesheets have been removed. Legacy saved preferences migrate without discarding the journal.

The interface follows the live AgroNova reference and its local source: centered landing copy, a discoverable tool grid, shared page-heading cards, rise-in entrances and perspective card reveals. Route containers have distinct animation names so navigation restarts the entrance while ordinary form reruns retain the current scene.

The fixed background uses three bounded aurora layers, two moving SVG light trails and 22 drifting particles. Light uses pale blue and green; Dark uses sage and indigo. It is decorative and does not intercept clicks. System reduced motion and the app setting stop the background, transitions and illustration motion.

Tilly is a renewed turtle mascot with a shaded patterned shell, soft rim, expressive face, blinking eyes, head movement, breathing and gentle foot motion. The internal `tilly_svg.py`/`render_tilly` names remain compatible for imports. Plant and garden graphics use muted ceramic/sage colours. The formerly tall footprint illustration is now a compact horizontal stepping-stone trail. The Turtle drawing engine and PNG badge/export paths remain intact.

Home's summary uses a balanced overview/companion row and three compact cards for the plant, trail and a tip. It no longer leaves a long blank column next to a stack of drawings. Dashboard removes duplicate footprint/goal displays and uses consistent chart, goal and insight cards. Shorter copy emphasizes user actions and keeps technical/model details available in expanders.

## Functional additions

Impact Lab includes a constrained action planner, one-input sensitivity explorer, journal coverage and reproducible experiment JSON. The planner uses at most one alternative per purchase and excludes brand-only changes using machine-readable alternative metadata, independent of display wording. Exports record inputs, factors, model version, assumptions and source labels. Demo entries are disclosed before planner results.

Month in review adds session reflection notes with a Markdown download. Existing journal, plans, undo, recurrence, import/export, goals, badges and browser persistence remain available.

Main settings controls are synchronized with canonical preferences before creation. A regression test alternates sidebar and main appearance controls, then checks currency synchronization. Home input defaults are explicit so displayed price/condition/brand values match the live estimate. A fresh browser session was checked at USD 25.00 with the matching 13.8 kg model preview. Progress-bar track and fill styling were also checked against the native 66% value.

## Verification

- 478 Python tests passed in the latest completed run; Ruff passed.
- Tests cover all eight routes in both modes, validated import/export, model arithmetic, planner optimality against exhaustive enumeration, no double counting, unchanged journal records, reproducible exports and theme migration.
- Browser review covered the live AgroNova reference, Light/Dark switching, pale background layers, the populated demo dashboard and planner, model/coverage tabs, and all eight routes at 390px without horizontal document overflow. The final eight-workspace pass also measured exactly 360px document width on a 360px viewport with no rendered exceptions.
- Browser style measurements confirmed aurora transforms and trail dash offsets changed across observations. Reduced motion produced `animation-name: none` for both aurora and trails.
- Route animation names were verified on Home and Settings. Tilly and the compact summary were inspected in the real app.
- The automated Playwright runner could not launch Chromium because of host process permissions. Its route/viewport/Axe matrix has been updated but is **not reported as passing**. A full accessibility audit and physical-device checks remain outstanding.

Current manual previews are named `studio-manual-*` in `docs/screenshots/`. Earlier screenshot files and design/test logs describe earlier releases.

## Assessment and evidence limits

The model is illustrative and spend-based, not a life-cycle assessment, statistical estimator or trained AI system. Model differences are not measured savings. A hosted Streamlit app processes session inputs on its server; browser-local persistence describes where the journal is saved, not an absence of server processing.

The supplied CRS AI Y1C1 assessment document concerns Dialogflow chatbots, not ShopImpact. The project retains the existing ShopImpact feature map but full marking alignment requires the correct rubric. Student identity, real feedback, wireframe and actual deployment/repository links remain student evidence to provide. No mark, admission outcome, institutional recognition, user research or environmental measurement is fabricated.
