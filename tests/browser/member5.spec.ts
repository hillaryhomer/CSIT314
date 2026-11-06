import { test, expect, type Page } from '@playwright/test';

async function login(page: Page, username: string) {
  await page.goto('/login');
  await page.getByLabel('Username or email', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill('browser test password 123');
  await page.getByRole('button', { name: 'Log In', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

test('customer detail retries record once; favourite and designer counts use shared records', async ({ page, browser }) => {
  await login(page, 'browser.admin');
  const session = await (await page.request.get('/api/auth/session')).json();
  const username = 'analytics.customer';
  expect((await page.request.post('/api/accounts', { headers: { 'X-CSRF-Token': session.csrfToken }, data: {
    username, email: 'analytics@example.test', password: 'browser test password 123', profileId: 'dev-profile-customer',
  } })).status()).toBe(201);
  await login(page, username);
  const card = page.locator('.project-card').filter({ hasText: 'Coastal Loft' });
  let eventId = '';
  let requests = 0;
  await page.route('**/api/catalog/projects/*/views', async route => {
    const body = route.request().postDataJSON();
    if (eventId) expect(body.eventId).toBe(eventId);
    eventId = body.eventId;
    requests++;
    const response = await route.fetch();
    if (requests === 1) await route.fulfill({ status: 500, json: { error: { message: 'Simulated lost response' } } });
    else await route.fulfill({ response });
  });
  await card.getByRole('button', { name: 'View Details', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Simulated lost response');
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Calm coastal interiors');
  await dialog.getByRole('button', { name: 'Add to Favourites', exact: true }).click();
  await expect(dialog.getByRole('button', { name: 'Saved', exact: true })).toBeDisabled();
  expect(requests).toBe(2);
  const designerContext = await browser.newContext();
  const designer = await designerContext.newPage();
  await login(designer, 'browser.designer');
  await designer.goto('/designer/analytics');
  const row = designer.getByRole('row').filter({ hasText: 'Coastal Loft' });
  await expect(row.locator('td').nth(3)).toHaveText('1');
  await expect(row.locator('td').nth(4)).toHaveText('1');
  await designer.reload();
  await expect(row.locator('td').nth(3)).toHaveText('1');
  await row.getByRole('button', { name: 'View Project', exact: true }).click();
  await expect(designer.getByRole('dialog')).toContainText('Coastal Loft');
  await designer.getByRole('button', { name: 'Close', exact: true }).click();
  await designer.getByRole('button', { name: 'Refresh counts', exact: true }).click();
  await expect(row.locator('td').nth(3)).toHaveText('1');
  await designerContext.close();
});
