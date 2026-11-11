const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const path = require('node:path');
const routes = [['/','Home'],['/dashboard','Dashboard'],['/purchases','Purchases'],['/swaps-plan','Swaps and plan'],['/impact-lab','Impact Lab'],['/garden-badges','Garden and badges'],['/month-review','Month in review'],['/settings-about','Settings and about']];
const modes = ['Light','Dark'];
async function open(page, route, mode) {
  await page.addInitScript(mode => {
    if (!localStorage.getItem('shopimpact_saved_state_v1')) localStorage.setItem('shopimpact_saved_state_v1', JSON.stringify({version:3,purchases_csv:'date,product_type,brand,condition,packaging,price_usd,co2e_kg,recurring,recurring_group,source\n',guide_dismissed:true,achievements:[],plans:[],settings:{display_mode:mode}}));
  },mode);
  await page.goto(route);
  await expect(page.locator('.studio-scene')).toBeAttached();
  await expect(page.locator('[data-testid="stException"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute('data-test-script-state','notRunning');
}
for (const mode of modes) {
  for (const width of [360,768,1280]) {
    test(`${mode} studio renders every route at ${width}px`, async ({browser}) => {
      test.setTimeout(180000);
      const context = await browser.newContext({viewport:{width,height:1000}});
      const page = await context.newPage();
      for (const [route,title] of routes) {
        await open(page,`http://127.0.0.1:8512${route}`,mode);
        await expect(page.getByRole('heading',{name:title,exact:true})).toBeAttached();
        expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
        await expect(page.locator('[data-testid="stException"]')).toHaveCount(0);
        await page.screenshot({path:path.join('docs/screenshots',`studio-${route.slice(1)||'home'}-${mode.toLowerCase()}-${width}.png`),fullPage:true});
      }
      await context.close();
    });
  }
  test(`${mode} keyboard and accessibility smoke`, async ({page}) => {
    await open(page,'http://127.0.0.1:8512/impact-lab',mode);
    await page.keyboard.press('Tab');
    expect(await page.evaluate(()=>parseFloat(getComputedStyle(document.activeElement).outlineWidth))).toBeGreaterThanOrEqual(2);
    const scan=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze();
    expect(scan.violations).toEqual([]);
  });
}
test('motion settings stop the ambient background',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await open(page,'http://127.0.0.1:8512/','Dark');
  expect(await page.locator('.ambient-one').evaluate(e=>getComputedStyle(e).animationName)).toBe('none');
});
test('planner controls and export remain available without journal data',async({page})=>{
  await open(page,'http://127.0.0.1:8512/impact-lab','Light');
  await expect(page.getByRole('tab',{name:'Action planner'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Download experiment JSON'})).toBeEnabled();
  await page.getByRole('tab',{name:'Model explorer'}).click();
  await expect(page.getByText('Illustrative estimate',{exact:true})).toBeVisible();
  await page.getByRole('tab',{name:'Journal coverage'}).click();
  await expect(page.getByText('Purchase records',{exact:true})).toBeVisible();
});
