import { test, expect, type Page } from '@playwright/test';

const password = 'browser test password 123';
let serial = 0;
async function login(page: Page, username: string) {
  await page.goto('/login');
  await page.getByLabel('Username or email', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Log In', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}
async function newCustomer(page: Page) {
  await login(page, 'browser.admin');
  const session = await (await page.request.get('/api/auth/session')).json();
  const username = `customer.${Date.now()}.${serial++}`;
  const response = await page.request.post('/api/accounts', { headers: { 'X-CSRF-Token': session.csrfToken }, data: { username, email: `${username}@example.test`, password, profileId: 'dev-profile-customer' } });
  expect(response.status()).toBe(201);
  const account = await response.json();
  await login(page, username);
  await expect(page).toHaveURL(/\/$/);
  return { username, accountId: account.accountId };
}
async function catalogue(page: Page) {
  return (await page.request.get('/api/catalog/projects')).json() as Promise<Array<{ projectId: string; title: string; saved: boolean }>>;
}

test('US30 keyword/category/style AND filters, reset, empty and mobile layout', async ({ page }) => {
  await page.goto('/');
  const cards = page.locator('.project-card');
  await expect(cards).toHaveCount(4);
  await page.getByPlaceholder('Search projects by title, description or style...').fill('  COASTAL  ');
  await expect(cards).toHaveCount(2);
  await page.getByLabel('Category', { exact: true }).selectOption('CAT001');
  await expect(cards).toHaveCount(1); await expect(cards).toContainText('Coastal Loft');
  await page.getByLabel('Style', { exact: true }).selectOption('Modern');
  await expect(page.getByText('No matching projects found', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Reset Filters', exact: true }).click();
  await expect(cards).toHaveCount(4);
  await expect(page.getByLabel('Category', { exact: true })).toHaveValue('');
  await expect(page.getByLabel('Style', { exact: true })).toHaveValue('');
  await page.getByLabel('Style', { exact: true }).selectOption('Japandi');
  await expect(cards).toHaveCount(2);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByLabel('Style', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('US31-34 detail, save, duplicate protection, reload, login persistence and favourite search', async ({ page }) => {
  const account = await newCustomer(page);
  const card = page.locator('.project-card').filter({ hasText: 'Coastal Loft' });
  await card.getByRole('button', { name: 'View Details', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Calm coastal interiors');
  await expect(dialog.getByAltText('Coastal Loft, image 1')).toBeVisible();
  let saves = 0;
  await page.route('**/api/favourites', async route => {
    if (route.request().method() === 'POST') { saves++; await new Promise(resolve => setTimeout(resolve, 200)); }
    await route.continue();
  });
  await dialog.getByRole('button', { name: 'Add to Favourites', exact: true }).evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click(); });
  await expect(dialog.getByRole('button', { name: 'Saved', exact: true })).toBeDisabled();
  await expect(dialog.getByRole('status')).toContainText('Added to favourites');
  expect(saves).toBe(1); await page.unroute('**/api/favourites');
  const saved = (await catalogue(page)).find(p => p.title === 'Coastal Loft')!;
  const session = await (await page.request.get('/api/auth/session')).json();
  const repeated = await page.request.post('/api/favourites', { headers: { 'X-CSRF-Token': session.csrfToken }, data: { projectId: saved.projectId } });
  expect(repeated.status()).toBe(200); expect((await repeated.json()).created).toBe(false);
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await page.reload(); await expect(card.getByRole('button', { name: 'Saved', exact: true })).toBeDisabled();
  await page.goto('/favourites');
  await expect(page.locator('.project-card')).toHaveCount(1);
  await page.getByPlaceholder('Search your favourites by keyword...').fill(' COASTAL ');
  await expect(page.locator('.project-card')).toHaveCount(1);
  await page.getByPlaceholder('Search your favourites by keyword...').fill('City Cafe');
  await expect(page.getByText('No matching favourites', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Clear search', exact: true }).click();
  await expect(page.locator('.project-card')).toHaveCount(1);
  await page.goto('/logout'); await page.getByRole('button', { name: 'Log Out', exact: true }).click();
  await page.goto('/favourites'); await expect(page.getByRole('heading', { name: 'Sign in required' })).toBeVisible();
  await login(page, account.username); await page.goto('/favourites');
  await expect(page.locator('.project-card')).toContainText('Coastal Loft');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('favourites stay private across customers and reject forged customer IDs', async ({ page, browser }) => {
  const first = await newCustomer(page);
  const project = (await catalogue(page)).find(p => p.title === 'City Cafe')!;
  await page.locator('.project-card').filter({ hasText: 'City Cafe' }).getByRole('button', { name: 'Add to Favourites', exact: true }).click();
  await expect(page.locator('.project-card').filter({ hasText: 'City Cafe' }).getByRole('button', { name: 'Saved', exact: true })).toBeDisabled();
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:4177' });
  try {
    const other = await context.newPage(); await newCustomer(other);
    await other.goto('/favourites'); await expect(other.getByText('No favourites yet', { exact: true })).toBeVisible();
    expect((await other.request.get(`/api/favourites?customerId=${first.accountId}`)).status()).toBe(400);
    expect((await other.request.get(`/api/customers/${first.accountId}/favourites`)).status()).toBe(404);
    const session = await (await other.request.get('/api/auth/session')).json();
    expect((await other.request.post('/api/favourites', { headers: { 'X-CSRF-Token': session.csrfToken }, data: { projectId: project.projectId, customerId: first.accountId } })).status()).toBe(400);
    await other.goto('/'); await expect(other.locator('.project-card').filter({ hasText: 'City Cafe' }).getByRole('button', { name: 'Add to Favourites', exact: true })).toBeVisible();
  } finally { await context.close(); }
  await page.goto('/favourites'); await expect(page.locator('.project-card')).toHaveCount(1);
});

test('failed save never shows Saved; retry, list errors and missing details are explicit', async ({ page }) => {
  await newCustomer(page);
  const card = page.locator('.project-card').filter({ hasText: 'Work Studio' });
  await page.route('**/api/favourites', route => route.fulfill({ status: 500, json: { error: { code: 'PERSISTENCE', message: 'Save failed. Retry later.', fields: {} } } }));
  await card.getByRole('button', { name: 'Add to Favourites', exact: true }).click();
  await expect(card.getByRole('alert')).toContainText('Save failed');
  await expect(card.getByRole('button', { name: 'Saved', exact: true })).toHaveCount(0);
  await page.unroute('**/api/favourites');
  expect((await (await page.request.get('/api/favourites')).json()).length).toBe(0);
  await card.getByRole('button', { name: 'Add to Favourites', exact: true }).click();
  await expect(card.getByRole('button', { name: 'Saved', exact: true })).toBeDisabled();
  await page.route('**/api/favourites?q=*', route => route.fulfill({ status: 500, json: { error: { code: 'PERSISTENCE', message: 'Favourite list failed.', fields: {} } } }));
  await page.goto('/favourites'); await expect(page.getByRole('alert')).toContainText('Favourite list failed');
  await expect(page.getByText('No favourites yet', { exact: true })).toHaveCount(0);
  await page.unroute('**/api/favourites?q=*'); await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(page.locator('.project-card')).toHaveCount(1);
  await page.route('**/api/catalog/projects/*/views', route => route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Project is no longer available.', fields: {} } } }));
  await page.getByRole('button', { name: 'View Details', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('no longer available');
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Add to Favourites', exact: true })).toHaveCount(0);
});

test('designer updates and deletion flow into saved projects without broken references', async ({ page, browser }) => {
  await newCustomer(page);
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:4177' });
  try {
    const designer = await context.newPage(); await login(designer, 'browser.designer');
    const session = await (await designer.request.get('/api/auth/session')).json();
    const fields = { title: `Live favourite ${Date.now()}`, description: 'Original description', style: 'Modern', categoryId: 'CAT001', images: [] };
    const created = await designer.request.post('/api/designer/projects/current', { headers: { 'X-CSRF-Token': session.csrfToken }, data: fields });
    expect(created.status()).toBe(201); const project = await created.json();
    await page.reload();
    const card = page.locator('.project-card').filter({ hasText: fields.title });
    await card.getByRole('button', { name: 'Add to Favourites', exact: true }).click(); await expect(card.getByRole('button', { name: 'Saved', exact: true })).toBeDisabled();
    const changed = { ...fields, title: fields.title + ' Updated', description: 'New description from designer' };
    expect((await designer.request.put(`/api/designer/projects/current/${project.projectId}`, { headers: { 'X-CSRF-Token': session.csrfToken }, data: changed })).status()).toBe(200);
    await page.goto('/favourites'); await expect(page.locator('.project-card')).toContainText(changed.title);
    await page.getByRole('button', { name: 'View Details', exact: true }).click(); await expect(page.getByRole('dialog')).toContainText(changed.description);
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
    expect((await designer.request.delete(`/api/designer/projects/current/${project.projectId}`, { headers: { 'X-CSRF-Token': session.csrfToken }, data: {} })).status()).toBe(200);
    await page.reload(); await expect(page.getByText('No favourites yet', { exact: true })).toBeVisible();
  } finally { await context.close(); }
});

test('anonymous save prompts shared login and protected favourites require a session', async ({ page }) => {
  await page.goto('/');
  const card = page.locator('.project-card').filter({ hasText: 'Garden Home' });
  await card.getByRole('button', { name: 'View Details', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Log in to save', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get('/api/favourites')).status()).toBe(401);
  await page.goto('/favourites'); await expect(page.getByRole('heading', { name: 'Sign in required' })).toBeVisible();
});
