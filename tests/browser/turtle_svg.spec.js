const { test, expect } = require("@playwright/test");
const path = require("node:path");

const base = "http://127.0.0.1:8512";
const screenshots = path.join(process.cwd(), "docs", "screenshots");
const modes = [
  { name: "Light", slug: "light" },
  { name: "Dark", slug: "dark" },
];
const drawings = {
  plant: 'img[alt^="Turtle-drawn plant with"]',
  footprints: 'img[alt^="Turtle-drawn footprint trail with"]',
  garden: 'img[alt^="Turtle-drawn eco garden"]',
};
const frameTimes = [0.4, 1, 2, 4];
function savedState(displayMode, reduceMotion = false) {
  return JSON.stringify({
    version: 3,
    purchases_csv:
      "date,product_type,brand,condition,packaging,price_usd,co2e_kg,recurring,recurring_group,source\n",
    guide_dismissed: true,
    achievements: [],
    plans: [],
    settings: { display_mode: displayMode, reduce_motion: reduceMotion },
  });
}

async function seedAndOpen(page, route = "/", mode = "Dark") {
  await page.addInitScript((initialState) => {
    const key = "shopimpact_saved_state_v1";
    if (localStorage.getItem(key) === null) localStorage.setItem(key, initialState);
  }, savedState(mode));
  await page.goto(`${base}${route}`);
  await page.getByRole("button", { name: "Continue as guest", exact: true }).click();
  const retryStorage = page.getByRole("button", {
    name: "Retry loading saved data",
  });
  if (await retryStorage.isVisible().catch(() => false)) {
    await retryStorage.click();
  }
  await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute(
    "data-test-script-state",
    "notRunning",
  );
}

async function loadDemo(page) {
  const demo = page.getByRole("button", { name: "Try with demo data" });
  await expect(demo).toBeVisible();
  await demo.click();
  await expect
    .poll(() =>
      page.evaluate(() => {
        const saved = localStorage.getItem("shopimpact_saved_state_v1");
        return saved ? JSON.parse(saved).purchases_csv.split("\n").length > 2 : false;
      }),
    )
    .toBe(true);
}

async function restartImage(image) {
  await image.evaluate(async (node) => {
    const clone = node.cloneNode(true);
    node.replaceWith(clone);
    await clone.decode();
  });
}

async function captureTimedDrawing(page, name, selector, mode, width) {
  await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute(
    "data-test-script-state",
    "notRunning",
  );
  const image = page.locator(`${selector}:visible`).first();
  await expect(image).toBeVisible();
  await page.waitForTimeout(300);
  await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute(
    "data-test-script-state",
    "notRunning",
  );
  await image.scrollIntoViewIfNeeded();
  await restartImage(image);
  const current = page.locator(selector).first();
  const metrics = await current.evaluate((node) => ({
    src: node.src,
    width: node.getBoundingClientRect().width,
    height: node.getBoundingClientRect().height,
    naturalWidth: node.naturalWidth,
    naturalHeight: node.naturalHeight,
  }));
  const svg = Buffer.from(metrics.src.split(",")[1], "base64").toString("utf8");
  expect(svg).toContain("<svg");
  expect(svg).toContain("viewBox");
  expect(svg).toContain("aria-label");
  expect(metrics.width).toBeLessThanOrEqual(width);
  expect(metrics.naturalWidth).toBeGreaterThan(0);
  expect(Buffer.byteLength(svg)).toBeLessThan(80 * 1024);
  expect(svg).toContain("@keyframes");

  let elapsed = 0;
  for (const time of frameTimes) {
    await page.waitForTimeout(Math.round((time - elapsed) * 1000));
    await current.screenshot({
      path: path.join(
        screenshots,
        `drawing-${name}-${mode.slug}-${width}-t${time.toFixed(1)}s.png`,
      ),
    });
    elapsed = time;
  }
  return {
    drawing: name,
    theme: mode.name,
    viewport: width,
    svgBytes: Buffer.byteLength(svg),
    renderedWidth: Math.round(metrics.width),
    renderedHeight: Math.round(metrics.height),
    naturalSize: [metrics.naturalWidth, metrics.naturalHeight],
  };
}

test("capture real animated SVG frames at all requested themes and sizes", async ({
  browser,
}) => {
  test.setTimeout(600_000);
  const measurements = [];
  for (const mode of modes) {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 1600 },
      reducedMotion: "no-preference",
    });
    const page = await context.newPage();
    await seedAndOpen(page, "/", mode.name);
    await loadDemo(page);
    await expect(page.locator(drawings.plant).first()).toBeVisible();
    for (const [index, width] of [360, 1280].entries()) {
      await page.setViewportSize({ width, height: 1600 });
      if (index > 0) {
        await page.goto(`${base}/`);
        await expect(page.getByRole("heading", { name: "Home", exact: true }))
          .toBeVisible();
      }
      await captureTimedDrawing(page, "plant", drawings.plant, mode, width)
        .then((result) => measurements.push(result));
      await captureTimedDrawing(page, "footprints", drawings.footprints, mode, width)
        .then((result) => measurements.push(result));

      await page.goto(`${base}/garden-badges`);
      await expect(page.getByRole("heading", { name: "Garden and badges" }))
        .toBeVisible();
      await captureTimedDrawing(page, "garden", drawings.garden, mode, width)
        .then((result) => measurements.push(result));
    }
    await context.close();
  }
  console.log(
    `TURTLE_SVG_MEASUREMENTS ${JSON.stringify({
      screenshots: measurements.length * frameTimes.length,
      drawings: measurements.length,
      minSvgBytes: Math.min(...measurements.map(({ svgBytes }) => svgBytes)),
      maxSvgBytes: Math.max(...measurements.map(({ svgBytes }) => svgBytes)),
      measurements,
    })}`,
  );
});

test("app Reduce motion setting returns static SVG and system preference prevents motion", async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 360, height: 1400 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await seedAndOpen(page);
  await loadDemo(page);
  const animated = page.locator(`${drawings.plant}:visible`).first();
  await expect(animated).toBeVisible();
  expect(
    await page.evaluate(() =>
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    ),
  ).toBe(true);
  const selectedSystemSvg = Buffer.from(
    (
      await animated.evaluate((node) => node.currentSrc)
    ).split(",")[1],
    "base64",
  ).toString("utf8");
  expect(selectedSystemSvg).not.toContain("<style");
  const initial = await animated.screenshot({
    path: path.join(screenshots, "reduced-motion-system-plant-first.png"),
  });
  await page.waitForTimeout(1200);
  const later = await animated.screenshot({
    path: path.join(screenshots, "reduced-motion-system-plant-later.png"),
  });
  expect(later).toEqual(initial);

  await page.getByRole("button", { name: "Settings" }).click();
  const reduceMotion = page.getByRole("checkbox", { name: "Reduce motion" });
  await reduceMotion.check({ force: true });
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("shopimpact_saved_state_v1")))
    .toContain('"reduce_motion":true');
  await page.getByRole("button", { name: "Settings" }).click();
  for (const selector of [drawings.plant, drawings.footprints]) {
    const image = page.locator(`${selector}:visible`).first();
    const svg = Buffer.from(
      (await image.getAttribute("src")).split(",")[1],
      "base64",
    ).toString("utf8");
    expect(svg).not.toContain("<style");
  }
  await page.goto(`${base}/garden-badges`);
  const garden = page.locator(`${drawings.garden}:visible`).first();
  await expect(garden).toBeVisible();
  const staticGarden = Buffer.from(
    (await garden.getAttribute("src")).split(",")[1],
    "base64",
  ).toString("utf8");
  expect(staticGarden).not.toContain("<style");
  await context.close();
});

test("ordinary Home reruns preserve the plant image and each low purchase replays the eco-win", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 1500 });
  await seedAndOpen(page);
  const form = page.locator(".st-key-purchase-entry");

  async function logLowPurchase(price) {
    const product = form.getByRole("radio", { name: "Books & Stationery" });
    await product.click({ force: true });
    await expect(product).toBeChecked();
    await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute(
      "data-test-script-state",
      "notRunning",
    );
    const brand = form.locator('[aria-label="Brand or shop"]:visible').first();
    await brand.locator("xpath=..").getByRole("button", { name: "Open" }).click();
    await expect(brand).toHaveAttribute("aria-expanded", "true");
    await page
      .getByRole("option", { name: "Second-hand bookshop", exact: true })
      .click();
    await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute(
      "data-test-script-state",
      "notRunning",
    );
    await expect(brand).toHaveValue("Second-hand bookshop");
    const priceInput = form.locator('[aria-label="Price ($)"]:visible').first();
    await priceInput.fill(String(price));
    await priceInput.press("Enter");
    await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute(
      "data-test-script-state",
      "notRunning",
    );
    const logButton = form
      .getByRole("button", { name: "Log this purchase" })
      .first();
    await expect(logButton).toBeEnabled();
    await logButton.click();
  }

  const eventPlant = page.locator(
    'img.svg-motion-animated[alt^="Animated Turtle-drawn sprout celebrating"]',
  );
  await logLowPurchase(1);
  await expect(eventPlant).toBeVisible();
  const firstSrc = await eventPlant.getAttribute("src");
  const firstSvg = Buffer.from(firstSrc.split(",")[1], "base64").toString("utf8");
  expect(firstSvg).toContain("<!-- purchase:");

  await page.getByRole("radio", { name: "Plan a purchase" }).click({ force: true });
  await page.getByRole("radio", { name: "Log a purchase" }).click({ force: true });
  await expect(eventPlant).toHaveAttribute("src", firstSrc);

  await logLowPurchase(2);
  await expect.poll(() => eventPlant.getAttribute("src")).not.toBe(firstSrc);
  const secondSrc = await eventPlant.getAttribute("src");
  const secondSvg = Buffer.from(secondSrc.split(",")[1], "base64").toString("utf8");
  expect(secondSvg).toContain("<!-- purchase:");
});
