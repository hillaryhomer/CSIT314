import { test, expect, type Page } from '@playwright/test';

async function login(page: Page, username = 'browser.manager') {
  await page.goto('/login');
  await page.getByLabel('Username or email', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill('browser test password 123');
  await page.getByRole('button', { name: 'Log In', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

test('category CRUD, cancel, failures, duplicate validation and shared project relationships', async ({ page, browser }) => {
  await login(page); await page.goto('/manager/categories');
  await page.getByRole('button', { name: 'Add Category', exact: true }).click();
  await page.getByLabel('Category name', { exact: true }).fill('Cancelled Category');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  expect((await (await page.request.get('/api/manager/categories?q=Cancelled')).json()).length).toBe(0);
  await page.getByRole('button', { name: 'Add Category', exact: true }).click();
  await page.getByLabel('Category name', { exact: true }).fill('  Browser Garden  ');
  await page.getByLabel('Description', { exact: true }).fill('Synthetic greenery');
  await page.route('**/api/manager/categories', route => route.fulfill({ status: 500, json: { error: { message: 'Category storage unavailable' } } }));
  await page.getByRole('button', { name: 'Save Category', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Category storage unavailable');
  await expect(page.getByLabel('Category name', { exact: true })).toHaveValue('  Browser Garden  ');
  await page.unroute('**/api/manager/categories');
  await page.getByRole('button', { name: 'Save Category', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  let row = page.getByRole('row').filter({ hasText: 'Browser Garden' });
  await expect(row).toBeVisible();
  await page.reload(); await expect(row).toBeVisible();
  await row.getByRole('button', { name: 'View', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Synthetic greenery');
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  const category = (await (await page.request.get('/api/manager/categories?q=Browser Garden')).json())[0];
  const context = await browser.newContext();
  try {
    const designer = await context.newPage(); await login(designer, 'browser.designer');
    await designer.goto('/designer/current');
    await designer.getByRole('button', { name: 'Add Project', exact: true }).click();
    await expect(designer.getByRole('dialog').getByRole('option', { name: 'Browser Garden', exact: true })).toHaveCount(1);
    const auth = await (await designer.request.get('/api/auth/session')).json();
    const draft = { title: 'Shared Garden Project', description: 'Category integration', categoryId: category.categoryId, style: 'Modern', images: [] };
    expect((await designer.request.post('/api/designer/projects/current', { headers: { 'X-CSRF-Token': auth.csrfToken }, data: draft })).status()).toBe(201);
    await row.getByRole('button', { name: 'Edit', exact: true }).click();
    await page.getByLabel('Category name', { exact: true }).fill('Residential');
    await page.getByRole('button', { name: 'Save Category', exact: true }).click();
    await expect(page.getByRole('dialog').getByText('A category with this name already exists.', { exact: true })).toBeVisible();
    await page.getByLabel('Category name', { exact: true }).fill('Renamed Garden');
    await page.getByRole('button', { name: 'Save Category', exact: true }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    row = page.getByRole('row').filter({ hasText: 'Renamed Garden' });
    await row.getByRole('button', { name: 'Delete', exact: true }).click();
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'Delete', exact: true }).click();
    await page.getByRole('button', { name: 'Confirm Delete', exact: true }).click();
    await expect(row).toHaveCount(0);
    expect((await designer.request.post('/api/designer/projects/current', { headers: { 'X-CSRF-Token': auth.csrfToken }, data: draft })).status()).toBe(400);
    const projects = await (await page.request.get('/api/catalog/projects?categoryId=' + category.categoryId)).json();
    expect(projects[0].categoryName).toBe('Renamed Garden');
    expect(projects[0].categoryStatus).toBe('Suspended');
  } finally { await context.close(); }
  await page.getByPlaceholder('Search categories by name or description...').fill('no matching synthetic keyword');
  await expect(page.getByText('No matching categories', { exact: true })).toBeVisible();
});

test('daily weekly monthly real reports, calendar labels, empty and failure states', async ({ page }) => {
  await login(page); await page.goto('/manager/reports');
  async function generate(kind: string, value: string, projects: string, views: string) {
    await page.getByLabel('Report period', { exact: true }).selectOption(kind);
    await page.getByLabel(kind === 'monthly' ? 'Selected month' : kind === 'weekly' ? 'Week reference date' : 'Selected date', { exact: true }).fill(value);
    await page.getByRole('button', { name: 'Generate Report', exact: true }).click();
    await expect(page.getByRole('row').filter({ hasText: 'Projects created' }).locator('td').nth(1)).toHaveText(projects);
    await expect(page.getByRole('row').filter({ hasText: 'Customer view events' }).locator('td').nth(1)).toHaveText(views);
  }
  await generate('daily', '2024-02-29', '2', '2');
  await expect(page.getByText('Asia/Makassar (UTC+08:00)', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Incomplete historical coverage');
  await generate('weekly', '2024-02-29', '3', '3');
  await expect(page.getByText('2024-02-26T00:00:00+08:00', { exact: true })).toBeVisible();
  await generate('monthly', '2024-02', '2', '2');
  await generate('daily', '2020-01-01', '0', '0');
  await page.route('**/api/manager/reports/**', route => route.fulfill({ status: 500, json: { error: { message: 'Report query failed' } } }));
  await page.getByRole('button', { name: 'Generate Report', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Report query failed');
  await expect(page.getByRole('row').filter({ hasText: 'Projects created' })).toHaveCount(0);
});
