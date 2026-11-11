const fs = require("node:fs");
const path = require("node:path");
const { defineConfig } = require("@playwright/test");

const venvPython = path.join(__dirname, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = process.env.PYTHON || (fs.existsSync(venvPython) ? venvPython : "python3");

module.exports = defineConfig({
  testDir: "./tests/browser",
  timeout: 120_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://127.0.0.1:8512",
    browserName: "chromium",
    viewport: { width: 1280, height: 900 },
  },
  webServer: {
    command: `${python} -m streamlit run app.py --server.headless true --server.port 8512 --browser.gatherUsageStats false`,
    url: "http://127.0.0.1:8512/_stcore/health",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
