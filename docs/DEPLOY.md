# Deploy ShopImpact to Streamlit Community Cloud

## Before you deploy

1. Create or choose the GitHub repository for this project.
2. Upload the complete project, keeping `app.py`, `requirements.txt`, and `.streamlit/config.toml` at the repository root.
3. Confirm that `requirements.txt` includes Streamlit and `streamlit-js-eval`; no secrets, API keys, or database credentials are required.
4. Push the changes to the branch you intend to deploy.

## Create the Community Cloud app

1. Open [share.streamlit.io](https://share.streamlit.io/) and sign in with the GitHub account that can access the repository.
2. Choose **Create app** (or **New app**).
3. Select the repository, deployment branch, and `app.py` as the main file path.
4. Select **Deploy** and wait for the app build to finish. The build installs the dependencies from `requirements.txt`.
5. Open the generated app URL and complete the checklist below.
6. Copy the app URL into the clearly marked **Live application** placeholder in `README.md`.

## Post-deploy manual test checklist

- [ ] Open the app on desktop and at a narrow/mobile width.
- [ ] Change display mode, currency and the monthly goal; verify the displayed price and estimate update sensibly.
- [ ] Log a purchase and confirm exactly one clear success message appears.
- [ ] Edit a purchase, save it, and use **Undo last edit**.
- [ ] Delete a purchase and use **Undo last delete**.
- [ ] Export the CSV, restore it, and check that recurring and synthetic-demo labels are retained.
- [ ] Import a CSV with an invalid row and confirm the skipped-row reason is shown.
- [ ] Enable **Repeat monthly**, inspect the count preview, log the series, then remove the series and undo.
- [ ] Refresh the page in the same browser profile and origin; confirm locally saved purchases return.
- [ ] Use **Clear saved data**, cancel once, then confirm and verify the browser copy and session list are both empty.
- [ ] Check the Settings status when browser storage is available. If storage is blocked, confirm the app reports session-only behavior.
- [ ] Test Settings, goal presets, reduce motion, **Show guide again**, the compare view, summary download and rotating tip.

## Data and privacy note

The app does not use analytics, a project database, or a separate data service. Purchase records are mirrored to this browser's localStorage under a ShopImpact-specific key. Streamlit still sends active widget/session values to the Streamlit app process so it can calculate and render the interface; Community Cloud is a hosted server. Do not enter sensitive personal information. Use a local run if server-side session processing is not acceptable. Browser-local saves belong to that browser profile and app origin and are not shared across devices.
