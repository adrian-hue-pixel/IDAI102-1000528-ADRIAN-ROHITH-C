> Historical record: this document describes an earlier release. See REDESIGN_2026.md and the current README for the two-mode studio refresh.

# ShopImpact — Test Log

## Multi-page redesign and final visual verification (2026-10-24)

- Replaced the single long-page layout with seven routed pages while keeping Home's brief layout: inputs at the top, compact month snapshot in the centre and a narrow Companion/drawings side column.
- Corrected the product tile breakpoints after opening the screenshot matrix: six columns at 1280px, three at 768px, two at 360px, with the last row filling its width. Reduced redundant top padding below the fixed top bar.
- Captured 63 real page screenshots (7 pages × 3 themes × 3 widths) and 72 timed Turtle drawing frames (3 drawings × 3 themes × 2 widths × 4 times). Opened the page contact sheets and drawing frame sheets. Reviewed Home and Garden at 360, 768 and 1280px; Tilly's head, eyes, shell, legs and mood accessory remain visible, and the plant, footprints and garden animation are not clipped.
- SVG sizes measured 23,414–43,996 bytes. At 360px the rendered plant was 220×249px, footprint trail 220×292px and garden 328×219px; at 1280px the garden was 360×240px. These are under the 80KB budget. The timed captures show the plant stem/leaves unfurl, footprints appear in order and garden plants grow.
- System reduced motion initially remained animated when the media query lived only inside the SVG data URI. The render helpers now provide paired animated/static `<img>` elements; host CSS selects the static image for `prefers-reduced-motion`, while the app setting also requests style-free SVG. Chromium screenshots remain identical after a 1.2-second wait with system motion reduction enabled.
- Eco-win browser verification waits for the Streamlit rerun and confirms a new low-impact purchase changes the SVG's purchase-ID comment; ordinary reruns preserve the existing source.
- Responsive screenshots measured document width equal to the viewport at 360, 768 and 1280px. Axe scanned all 21 page/theme combinations. One known Streamlit 1.65.0 Home date-input `aria-allowed-attr` node is excluded by the browser test; every other violation remains a failure.
- Local Chromium page-load medians (three fresh browser-context navigations per route, app server warm, from `goto` through the page heading): Home 321ms, Dashboard 412ms, Purchases 395ms, Swaps and plan 390ms, Garden and badges 372ms, Month in review 380ms, Settings and about 393ms. These are local development measurements, not hosted-service SLAs.
- Workspace footprint: 15.37 MiB excluding `.venv`, `node_modules`, `.git`, Python/test caches and Playwright output; includes screenshots.
- Verification: `PYTHONPATH=. .venv/bin/python -m pytest -q` — 348 passed; `.venv/bin/ruff check .` — all checks passed; combined Playwright suites — 6 passed, with 63 page screenshots, 72 drawing frames, all 21 Axe scans and reduced-motion/eco-win replay checks passing.
- Changelog: corrected tablet/mobile product-grid behavior and top spacing; documented all pages, the SvgTurtle/TurtleCanvas split, real-browser evidence and remaining manual checks.

### Phone checks still to complete manually

- Open the deployed build on a real iPhone Safari and Android Chrome; check portrait/landscape and 360–430px layouts.
- Verify the two-column product grid, no horizontal scrolling, readable labels, tap targets, top-bar menu and skip-to-content flow.
- Navigate between pages and refresh after changing month, currency, theme, goal, Reduce motion and purchases; confirm browser-local state restores.
- Enable the device's Reduce motion preference and confirm Tilly and all Turtle drawings are static; also check the app's own Reduce motion switch.
- Test larger text and Atkinson Hyperlegible, VoiceOver/TalkBack labels, and color contrast in Ivory, Obsidian and High contrast.
- Try CSV import/export, share-image/PDF/poster downloads and the clear-saved-data confirmation on device.

## SvgTurtle on-screen drawings (2026-10-22)

- Switched the on-screen Eco Garden, footprint trail, and growing plant/eco-win sprout to cached `turtle_svg.py` SVGs. Base64 image embedding preserves animation CSS; Reduce motion uses static SVGs, and animated output honors the browser's reduced-motion preference. Changed garden/footprint content updates statically rather than replaying during month changes; the eco-win event image includes its purchase ID so each new low-impact purchase can replay.
- Kept the original TurtleCanvas badge drawings and PNG drawing/export paths; removed the old raster rendering and cache paths from the three on-screen displays.
- Added exhaustive SVG validity/accessibility/size/determinism checks, frame-time rendering tests, SvgTurtle command tests, and app tests for static output, stable reruns and purchase-specific eco-win image changes.
- Captured 18 before screenshots and 72 after screenshots (0.4, 1, 2 and 4 seconds) across all three drawings, display modes and 360/1280px viewports. Opened the six after-contact-sheets and visually confirmed the plant grows, footprints appear in order, the garden grows, and no drawing is clipped. Browser checks also confirmed that switching the month updates changed footprint content without animation replay, while Dashboard view and text-size reruns preserve the images. Browser measurements: SVG sources were 24,964–44,001 bytes; rendered dimensions were 300×340px (plant), 328×218.7px (garden) and 280×372px (footprints). An ordinary rerun took 152ms and preserved all SVG image nodes and sources.
- Verification: `./.venv/bin/python -m pytest -q` — 318 passed; `./.venv/bin/ruff check .` — passed; `npx playwright test tests/browser/turtle_svg.spec.js` — 4 passed, including all 72 timed captures, reduced-motion behavior, rerun stability and purchase-specific replay.

## Vector mascot replacement (2026-10-22)

- Replaced the Companion's hand-built inline mascot with the themed vector SVG from `tilly_svg.py`, embedded as a base64 data-URI image. The current Ivory and Obsidian display modes select the SVG's Earth and Dark palettes; High contrast selects its matching palette. The existing five-mood logic and speech bubble remain in place.
- Removed the Pillow/TurtleCanvas mascot and idle-GIF renderers and their raster tests. TurtleCanvas remains for badge drawings and PNG drawing/export paths.
- Added XML/accessibility checks across every mood and SVG theme, static animation checks, an app-level Reduce motion check and an embedded data-URI decode check.
- Captured and visually inspected the Companion at 360px and 1280px in the three display modes. The head, eyes, shell, legs and mood accessory are fully visible.
- Verification: `./.venv/bin/python -m pytest -q` — 155 passed; `./.venv/bin/ruff check .` — passed. Three of four Playwright tests passed, including the Tilly reduced-motion check. The remaining test completed the responsive/theme capture checks but later failed its brand-selection helper-text assertion. The six requested screenshots were opened and visually checked.

## Premium design reset continuation (2026-10-21)

- Replaced the raster Tilly display with an inline, theme-aware SVG turtle. Its five moods have distinct facial/accessory details; four legs, a tail, shell rim and hexagonal scales are contained in the SVG. CSS handles the blink/head bob and respects both the saved Reduce motion setting and the browser preference.
- Styled Log/Plan as a compact segmented control while preserving the keyboard-operable radio group.
- Removed decorative emoji from companion headings and purchase/impact labels; kept the celebratory toast icon. `logic.py` and all estimate calculations, factors, product data, and badge rules remain untouched.
- Fixed the browser contrast check to wait for the theme transition to settle before measuring the Settings control. Made brand suggestion selection use a forced click on the visible exact option because the Streamlit 1.65 custom combobox does not consistently expose keyboard active-descendant state; keyboard reachability is separately audited. Stabilized that audit against async browser-storage hydration and Streamlit-generated heading links.
- Regenerated the screenshot set through Playwright. Opened the six first-screen captures (Ivory, Obsidian and High contrast at 360px and 1280px) and the 360px companion capture. The purchase hierarchy remains clear; the 360px form still requires scrolling to see all categories.
- Final verification: `python -m pytest -q` — 129 passed; `ruff check .` — passed; `npm run test:e2e` — 4 passed. The final browser run measured first meaningful render at 2,121 ms.
- Remaining QA limit: automated browser contrast assertions cover representative theme controls and the disabled primary action, not every hover/focus/disabled/selected state for every widget type. The high-contrast palette is intentionally vivid; a full state-by-state contrast audit remains outstanding.

## Round 3 update

### Before and after
- Before: the mascot artwork was a simple shell and face, with no documented badge tiers, no explicit settings persistence for text/dyslexia/sound, and incomplete README integration instructions. After: the shell is more clearly turtle-shaped, the badge shelf exposes tier progress, settings persist in the app's browser payload, and the documentation is explicit about module responsibilities and deployment steps.
- Before: the README lacked the required integration and deployment headings and did not document the badge-tier mapping for the existing rules. After: it includes the required sections and a clear note that tiers are derived from existing count thresholds without changing the underlying badge calculations.
- Before: the app did not surface a dedicated shortcut cheat sheet or text-size/dyslexia/sound settings. After: settings now include text size, a dyslexia-friendly font mode, a badge-unlock sound toggle, and a keyboard-shortcuts expander.

### Short changelog
- Updated README with the required `## Integration details`, `## Deployment instructions`, and `## Live web app link` sections.
- Kept the logic model intact while adding badge tier metadata derived from existing thresholds without changing the quoted badge rules.
- Added persisted UI settings for text size, dyslexia mode, sound, and helper shortcuts and kept the saved-state version compatible with existing browsers.
- Extended the turtle art to a clearer, more compact turtle silhouette with a cleaner shell and more readable mood cues.

## Automated checks

Run from the project root:

```bash
python -m pytest -q
python tests/run_scenarios.py
```

**Phase 0 result:** 91 pytest tests passed (`python -m pytest -q`). Ruff passed on the changed Python files. The Playwright Chromium test passed (1 browser test), checking Earth, Dark and High contrast at 360, 768 and 1280px, the single-page layout, sticky bar, mobile stacking, no horizontal overflow and rendered widget colors. It regenerated 13 genuine Dashboard, Log purchase and Badges & tips PNG captures.

**Phase 0 change log (2026-10-07):** removed top-level Log/Dashboard/Badges tabs. Purchase inputs remain at the top; the monthly dashboard is centre-left with the Turtle-and-badges Companion alongside it and stacked below on narrow screens. Added the compact fixed ShopImpact/month/Settings bar, abbreviated month labels and support for viewing a newly logged purchase's month. Pinned Streamlit to the tested 1.65.0 release. No `logic.py` calculations, factors, thresholds or product records changed.

**Responsive follow-up:** the real-browser run exposed wide Altair SVG and browser-storage component frames in the mobile app's internal scroll area. The stylesheet now constrains both to the available content width. The refreshed 360px Log purchase and Badges captures were opened and visually checked in Earth mode; the dashboard was checked at all three widths in all three display modes.

**Phase 1 result:** 97 pytest tests passed; Ruff passed; the Playwright matrix passed and regenerated the 13 real screenshots. The browser check verifies the served SVG mark, loaded local font, four labelled KPI sparklines, labelled goal progress, accent-palette switching, and the in-app reduced-motion switch. It also emulates the system reduced-motion preference. The new 360px Dashboard, Log purchase and Badges captures were opened for visual review.

**Phase 1 change log (2026-10-07):** added a branded SVG mark/favicon and bundled Source Sans 3 with its OFL notice, static-asset serving, reusable spacing/radius/motion tokens, two seasonal accents, reduced-motion-aware CSS transitions and skeleton treatment, an animated accessible goal ring, four accessible trend sparklines, and a dismissible achievement inbox included in version-2 browser saves (version-1 saves remain readable). Toast confirmations remain in place. The numeric KPI glyphs still update immediately rather than counting up; no embedded JavaScript/iframe was added solely for that effect.

**Phase 2 result:** 102 pytest tests passed; Ruff check and format check passed. Playwright passed in Chromium, re-generated all responsive captures, and verified Tilly's alt text, garden alt text, the immediate eco-win illustration and the system reduced-motion static fallback. The in-app Reduce motion path also passed its AppTest. The captured normal-motion and reduced-motion eco-win images were opened and visually checked.

**Phase 2 change log (2026-10-07):** added five theme-aware Tilly moods, a month-selectable Eco Garden with six stages driven only by existing low-impact ratings, a cached 12-frame sprout GIF for immediate low-impact logging with static fallbacks for both motion preferences, and an accessible, one-time badge-unlock card/burst using existing badge rules. Eco-win feedback now survives browser-storage reruns and remains dismissible; the drawing itself plays only once. Added alt text to the Turtle graphics, tests for moods/stages/GIF size and reduced-motion styles, and actual browser-generated 360px Companion and eco-win screenshots. `logic.py`, all calculations, thresholds and product data remain unchanged.

**Phase 2 deferred:** badge details remain in the current inline shelf rather than a dialog; the drawing moment is a cached Turtle sprout GIF rather than Tilly visibly animating a pen stroke. The unlock treatment is CSS-only rather than a separate sandboxed component. No new dependencies or external assets were introduced.

**Phase 3 result:** 106 pytest tests passed; Ruff check and format check passed. Playwright passed at the responsive/theme matrix and regenerated all 16 actual screenshots. AppTest and unit coverage check XP level progression, weekly challenge date windows, one-rest-day activity streaks, and challenge dismiss/restore controls.

**Phase 3 change log (2026-10-07):** added the pure-Python `gamification.py` module for non-decaying XP/levels, optional current-week challenges and a best purchase-date activity streak with a one-day grace. New features read purchase records and ratings only; the existing monthly goal streak remains. No reminder or loss mechanics were added.

**Phase 3 deferred:** no silver/gold badge criteria were added because the existing badge rules have no tiers and changing thresholds is prohibited. A true logging-day streak also remains deferred because stored records do not include a log timestamp; the visible activity streak clearly uses purchase dates. Existing badge progress remains unchanged. Level-up/challenge-completion animations were omitted in favor of stable progress feedback.

Coverage includes:

- The price × category factor calculation and each adjustment factor.
- Negative, non-numeric, NaN, infinite and unusually large prices; unknown categories/conditions.
- Missing brand, invalid date type, invalid packaging value and successful purchase validation/insertion.
- Empty-month handling; month filtering, year boundary, average impact and category spend/impact/count totals.
- Badge thresholds, month-over-month comparison and earned explanations.
- Alternative suggestions, scenario savings, and category-specific tips that avoid immediate repetition.
- Headless Turtle leaf, footprint, mascot, garden and badge images as valid PNGs; the 12-frame live sprout GIF budget; and theme-matched scene backgrounds.
- XP/level boundaries, purchase-date week challenges, optional challenge dismissal/restoration, and a one-rest-day activity-streak allowance.
- Streamlit empty-state actions, disabled logging without a brand, purchase logging, display modes, currency reset, demo/clear, month navigation, delete/undo and CSV UI restore.
- Browser-save payload versioning, restore/clear behavior, confirmed browser clear, edit-and-undo, recurring-series bounds/removal, recurring CSV round-trip, insights, compare, goal presets/streak, onboarding, summary-image validity and daily-tip stability.
- Chart builders for empty, single-month and multi-month data, including both category measures.
- Theme text, impact-pill and chart-mark contrast checks.

The app interaction tests use Streamlit's `AppTest`. The Playwright test exercises a real local Chromium browser and the live Streamlit UI, but neither replaces manual checks of the deployed Community Cloud app.

## Responsive browser evidence

`PYTHON=.venv/bin/python npm run test:e2e` passed on the local app. It writes 16 actual screenshots: Dashboard at 360, 768 and 1280 pixels in Earth, Dark and High contrast modes, plus Log purchase and Badges & tips at both 360 and 1280 pixels in Earth mode, the 360px Companion view, and immediate eco-win screens at 360px with normal and reduced motion. The eco-win images are captured after a real browser interaction; the rest use labelled synthetic demo data.

## Reproducible 15-purchase demonstration

`python tests/run_scenarios.py` creates synthetic example records for three months. These are demonstration inputs only, not actual user data. With the scenario runner's fixed reference date and the default 80 kg goal:

| Example month | Purchases | Spend (USD) | Estimated CO₂e (kg) |
|---|---:|---:|---:|
| August 2026 | 5 | 1,150.00 | 730.42 |
| September 2026 | 5 | 240.00 | 87.11 |
| October 2026 | 5 | 300.00 | 53.06 |

The scenario is useful for demonstrating month selection, multi-month charts, badge rules and large/small examples. It must be cleared before entering actual demonstration purchases.

## Manual checks for the student

- [x] Check the local responsive layout at 360, 768 and 1280 pixels in Earth, Dark and High contrast modes.
- [ ] Inspect the captures on your own device and collect feedback from 2–3 real users.
- [ ] Deploy to Streamlit Community Cloud and run the checklist in [docs/DEPLOY.md](./DEPLOY.md).
- [ ] Add your own hand-drawn or Canva wireframe; it must not be fabricated.

| Tester (initials only) | What they liked or found confusing | Change made |
|---|---|---|
| Tester 1 | | |
| Tester 2 | | |
| Tester 3 (optional) | | |

## Fixes made during this review

The table records the earlier UX/robustness review (Round 1) and the persistence/features/submission review (Round 2).

| Round | Finding | Resolution |
|---|---|---|
| Round 1 | Formula inputs accepted malformed, non-finite or unreasonably large prices; blank brands could be accepted | Validate purchase inputs, bound large entries, and require a brand/shop without changing the illustrative formula or factors |
| Round 1 | The dashboard was difficult to navigate; mobile settings and empty-state routes were hard to find | Separate Log, Dashboard and Badges & tips views; add main-content settings and direct first-purchase/demo actions |
| Round 1 | Estimates, brand matches, rating language and celebration copy could be misread | Make the estimate caveat visible, label brand examples as non-endorsements, use non-judgemental copy and a single confirmation |
| Round 1 | Charts, goal progress, badges and turtle art lacked consistent responsive/theme behavior | Add over-goal treatment, equivalents, ranked swaps, responsive badge progress, theme-aware art/charts and reduce-motion support |
| Round 1 | CSV, delete, chart edge cases and Streamlit interactions had limited coverage | Add validated CSV restore/export, delete/undo, chart empty/single-month handling, and expanded `AppTest` coverage |
| Round 1 | Presentation, charts, CSV and styles were concentrated in `app.py` | Extract chart builders, CSV interchange and stylesheet logic into focused modules and update project documentation |
| Round 2 | Purchases and guide preference disappeared on refresh; restore/clear acknowledgement needed verification | Add versioned localStorage persistence, visible availability status, confirmed clearing, and a real-browser write/refresh/clear check |
| Round 2 | Edits, recurring purchases and CSV needed reliable validation and reversible actions | Revalidate/recalculate edits with undo; add capped monthly series, bulk removal, recurring/demo labels and CSV round-trip coverage |
| Round 2 | The app lacked accessible, deterministic ways to understand and compare activity | Add monthly insights, goal streak/presets, a two-option comparison, stable category-aware tips and dismissible/replayable onboarding |
| Round 2 | Users needed a portable month snapshot and deployment guidance | Generate a valid theme-aware PNG and document Community Cloud setup plus a post-deployment checklist |
| Round 2 | Responsive screenshots and final quality checks were missing or stale | Add a dev-only Playwright Chromium matrix, generate 11 genuine screenshots, update README/design/test docs, and pass Ruff plus the full suite |
