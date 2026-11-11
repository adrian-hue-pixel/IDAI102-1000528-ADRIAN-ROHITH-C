const {test, expect} = require('@playwright/test');
const routes = ['/', '/dashboard', '/purchases', '/swaps-plan', '/impact-lab', '/garden-badges', '/month-review', '/settings-about', '/research', '/feedback'];
async function open(page, route, mode='Light') {
  await page.addInitScript(mode => {
    localStorage.setItem('shopimpact_saved_state_v1',JSON.stringify({version:3,purchases_csv:'date,product_type,brand,condition,packaging,price_usd,co2e_kg,recurring,recurring_group,source\n',guide_dismissed:true,achievements:[],plans:[],settings:{display_mode:mode}}));
  },mode);
  await page.goto(route);
  await expect(page.locator('.studio-scene')).toBeAttached();
  await expect(page.getByRole('heading',{level:1}).first()).toBeAttached();
  await expect(page.locator('[data-testid="stApp"]')).toHaveAttribute('data-test-script-state','notRunning');
  await expect(page.locator('[data-testid="stException"]')).toHaveCount(0);
}
for (const mode of ['Light','Dark']) for (const width of [360,768,1280]) {
  test(`${mode}: full app and embedded research at ${width}px`,async({page})=>{
    test.setTimeout(180000);
    await page.setViewportSize({width,height:1000});
    for (const route of routes) {
      await open(page,route,mode);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
    }
  });
}
test('home retains Tilly, plant and footprint trail',async({page})=>{
  await open(page,'/');
  await expect(page.getByText('Meet Tilly',{exact:true})).toBeAttached();
  await expect(page.locator('img[alt^="Tilly the turtle"]')).toHaveCount(2);
  await expect(page.locator('img[alt^="Turtle-drawn plant with"]')).toHaveCount(2);
  await expect(page.locator('img[alt^="Turtle-drawn footprint trail with"]')).toHaveCount(2);
});
test('original Impact Lab opens research within the same app shell',async({page})=>{
  await open(page,'/impact-lab');
  for (const name of ['Action planner','Model explorer','Journal coverage']) await expect(page.getByRole('tab',{name,exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Open research tools →',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Research tools',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Back to Impact Lab',exact:true})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'Selected month',exact:true})).toBeAttached();
});
test('feedback requires consent',async({page})=>{
  await open(page,'/feedback');
  await page.getByRole('button',{name:'Save anonymous response',exact:true}).click();
  await expect(page.getByText('Consent is required; no response was saved.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Download my anonymous responses'})).toHaveCount(0);
});
