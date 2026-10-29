import { test, expect } from '@playwright/test';
const origins=['https://my.ndsp.app','https://bot.ndsp.app'];
test.beforeEach(async ({context})=>{
 await context.route('**/*',async route=>{
  const r=route.request(), u=new URL(r.url());
  if(!['GET','HEAD','OPTIONS'].includes(r.method())) return route.abort('blockedbyclient');
  if(!['https:','http:'].includes(u.protocol)) return route.continue();
  if(!['ndsp.app','www.ndsp.app','my.ndsp.app','bot.ndsp.app','api.ndsp.app','admin.ndsp.app'].includes(u.hostname)) return route.abort('blockedbyclient');
  return route.continue();
 });
});
test('NDSP login inputs, password visibility and recovery navigation', async ({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const r=await page.goto(origins[0],{waitUntil:'load'});
 expect(r.status()).toBeLessThan(400);
 const email=page.locator('input[type=email]'), password=page.locator('input[autocomplete=current-password]');
 await expect(email).toBeVisible(); await expect(password).toBeVisible();
 await expect(page.locator('button[type=submit]')).toBeDisabled();
 await email.fill('qa@example.test');await password.fill('Synthetic-UI-only-12345');
 await expect(page.locator('button[type=submit]')).toBeEnabled();
 await page.getByRole('button',{name:/Show password|إظهار كلمة المرور/i}).click();
 await expect(password).toHaveAttribute('type','text');
 await page.getByRole('button',{name:/Hide password|إخفاء كلمة المرور/i}).click();
 await expect(password).toHaveAttribute('type','password');
 await page.locator('a[href="/forgot-password"]').click();
 await expect(page).toHaveURL(/forgot-password/);
 await expect(page.locator('input[type=email]')).toBeVisible();
 expect(errors).toEqual([]);
});
test('NDSP trial registration link opens actual registration form',async({page})=>{
 await page.goto(origins[0],{waitUntil:'load'});
 await page.locator('a[href="/register"]').click();
 await expect(page).toHaveURL(/register/);
 await expect(page.locator('input[type=email]')).toBeVisible();
});
test('Bot language controls and registration navigation',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origins[1],{waitUntil:'load'});
 const english=page.getByRole('button',{name:'English',exact:true});
 await expect(english).toBeVisible();await english.click();
 await expect(english).toHaveAttribute('aria-pressed','true');
 const arabic=page.getByRole('button',{name:'العربية',exact:true});
 await arabic.click();await expect(arabic).toHaveAttribute('aria-pressed','true');
 await page.locator('a[href*="/registration/"]').click();
 await expect(page).toHaveURL(/registration/);
 await expect(page.locator('body')).toContainText(/حساب|register|تسجيل/i);
 expect(errors).toEqual([]);
});
test('Bot user guide and subscription routes have meaningful content',async({page})=>{
 for(const path of ['/user-guide/','/subscription/']){
  const r=await page.goto(origins[1]+path,{waitUntil:'load'});
  expect(r.status()).toBe(200);
  await expect(page.locator('body')).not.toContainText(/Application error|Internal Server Error|404.*not found/i);
  expect((await page.locator('body').innerText()).trim().length).toBeGreaterThan(80);
 }
});
