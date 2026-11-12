# Clean-install verification

Checked 12 November 2026 against repository commit `811ecee4c6f22ed6a0ec525b6716adc8c2ec8545`.

## Why requirements.txt includes ./core

`./core` installs the repository's `shopimpact-core` package. It is a local directory dependency, not a package fetched from an unknown index. Keep `core/pyproject.toml`, `core/src/shopimpact_core/` and its packaged datasets in the repository. Run installation from the repository root.

Streamlit Community Cloud copies the repository and starts from its root directory, as documented in [file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization). Its dependency discovery is described in [app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## Executed checks

A fresh GitHub clone and new Python 3.14 virtual environment were used, without local secrets or the existing project virtual environment:

```sh
python3 -m venv /tmp/shopimpact-clean-venv
# Activate this environment, then from the cloned repository root:
python -m pip install --no-cache-dir -r requirements.txt
python -m pip check
shopimpact --amount 799
python -m streamlit run app.py
```

- Dependency installation succeeded, including a built wheel for `shopimpact-core==0.1.0`.
- `pip check` reported no broken requirements.
- The installed core imported from the new environment's site-packages, and the CLI returned a replay JSON with dataset identity and calculated results. This exercised packaged data outside the source package.
- Streamlit AppTest rendered the entry screen, guest Home and Research tools without exceptions, using the fresh environment and no secrets.
- GitHub Actions run [43153466618](https://github.com/adrian-hue-pixel/ShopImpact/actions/runs/43153466618) also completed its dependency-install step on Ubuntu/Python 3.14.10. The overall run failed later in browser tests; this is not a claim of green CI.

## Scope and Cloud setup

These results establish a fresh clone/install and startup check, including Linux dependency installation in CI. They do not represent a newly provisioned Streamlit Cloud deployment or a complete browser audit. A cloud reboot can reuse its existing environment and is not proof of a clean build.

Deploy branch `main` with main file `app.py` and select Python 3.14 to match the verified environment. Configure Supabase public authentication settings for accounts and Groq credentials for Ask Tilly in Streamlit Secrets; never commit secrets. Guest entry and offline research tools remain available without those services.

The live application is https://shopimpact-app.streamlit.app/. For a provider-side clean-build check, inspect the installation logs of a newly provisioned Cloud deployment, then verify entry, guest Home and Research tools. The existing live app has received separate browser checks; that does not replace a fresh-build log.
