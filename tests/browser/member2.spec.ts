import { test, expect, type Page } from '@playwright/test';

const password = 'browser test password 123';
async function login(page: Page, username: string) {
  await page.goto('/login');
  await page.getByLabel('Username or email', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Log In', exact: true }).click();
}

test('designer CRUD, search, cancel, refresh and logout revoke access', async ({ page }) => {
  await login(page, 'browser.designer');
  await expect(page).toHaveURL(/\/designer$/);
  await page.goto('/designer/company');
  await page.getByRole('button', { name: 'Create Company', exact: true }).click();
  await page.getByLabel('Company name').fill('Persistent Studio');
  await page.getByLabel('Business address').fill('12 Studio Road');
  await page.getByLabel('Contact details').fill('studio@example.test');
  await page.getByLabel('Description').fill('Residential interiors');
  await page.getByRole('button', { name: 'Save Company' }).click();
  await expect(page.locator('dl')).toContainText('Persistent Studio');
  await page.reload();
  await expect(page.locator('dl')).toContainText('Persistent Studio');
  await page.getByRole('button', { name: 'Edit Company' }).click();
  await expect(page.getByLabel('Company name')).toHaveValue('Persistent Studio');
  await page.getByLabel('Company name').fill('Cancelled name');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.locator('dl')).toContainText('Persistent Studio');
  await page.getByRole('button', { name: 'Edit Company' }).click();
  await page.getByLabel('Company name').fill('Updated Studio');
  await page.route('**/api/company/*', route => route.request().method() === 'PUT' ? route.fulfill({ status: 500, json: { error: { code: 'PERSISTENCE', message: 'Save failed. Please retry.', fields: {} } } }) : route.continue());
  await page.getByRole('button', { name: 'Save Company' }).click();
  await expect(page.getByRole('alert')).toContainText('Save failed');
  await expect(page.getByLabel('Company name')).toHaveValue('Updated Studio');
  await page.unroute('**/api/company/*');
  await page.getByRole('button', { name: 'Save Company' }).click();
  await expect(page.locator('dl')).toContainText('Updated Studio');
  await page.getByPlaceholder('Search your company information...').fill('no-such-company');
  await expect(page.getByText('No matching company information')).toBeVisible();
  await page.getByRole('button', { name: 'Clear search' }).click();
  await expect(page.locator('dl')).toContainText('Updated Studio');
  await page.getByRole('button', { name: 'Delete Company', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();
  await expect(page.locator('dl')).toContainText('Updated Studio');
  await page.getByRole('button', { name: 'Delete Company', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete Company' }).click();
  await expect(page.getByText('No company information yet')).toBeVisible();
  await page.reload();
  await expect(page.getByText('No company information yet')).toBeVisible();
  await page.goto('/logout');
  await page.getByRole('button', { name: 'Log Out', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goBack();
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Sign in required' })).toBeVisible();
  await page.goto('/designer/company');
  await expect(page.getByRole('heading', { name: 'Sign in required' })).toBeVisible();
  expect((await page.request.get('/api/company')).status()).toBe(401);
});

test('Member 1 account creation, username/email search, suspension cancel and active-session revocation', async ({ page, browser }) => {
  await login(page, 'browser.admin');
  await expect(page).toHaveURL(/\/admin$/);
  await page.goto('/admin/accounts');
  await page.getByRole('button', { name: 'Create User Account', exact: true }).click();
  const dialog = page.getByRole('dialog');
  const username = `integrated.${Date.now()}`;
  await dialog.getByRole('textbox', { name: 'Username', exact: true }).fill(username);
  await dialog.getByRole('textbox', { name: 'Email', exact: true }).fill(`${username}@example.test`);
  await dialog.getByLabel('Initial Password').fill(password);
  await dialog.getByLabel('Assigned User Profile').selectOption('dev-profile-designer');
  await dialog.getByRole('button', { name: 'Create User Account', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:4175' });
  const designer = await context.newPage();
  await login(designer, username);
  await expect(designer).toHaveURL(/\/designer$/);
  const search = page.getByPlaceholder('Search accounts by username or email...');
  await search.fill(`${username}@example.test`);
  let row = page.getByRole('row').filter({ hasText: username });
  await expect(row).toHaveCount(1);
  await row.getByRole('button', { name: 'Suspend', exact: true }).click();
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  expect((await designer.request.get('/api/company')).status()).toBe(200);
  await search.fill(username.toUpperCase());
  row = page.getByRole('row').filter({ hasText: username });
  await row.getByRole('button', { name: 'Suspend', exact: true }).click();
  await dialog.getByRole('button', { name: 'Suspend User Account', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(row).toContainText('Suspended');
  expect((await designer.request.get('/api/company')).status()).toBe(401);
  await designer.goto('/designer/company');
  await expect(designer.getByRole('heading', { name: 'Sign in required' })).toBeVisible();
  await login(designer, username);
  await expect(designer.getByRole('alert')).toContainText('cannot access');
  await search.fill('nonexistent-account');
  await expect(page.getByText('No matching accounts')).toBeVisible();
  await context.close();
});

test('role redirects and route guards use the authenticated role', async ({ page }) => {
  for (const [role, home] of [['customer', '/'], ['manager', '/manager']] as const) {
    await login(page, `${role}@browser.test`);
    await expect(page).toHaveURL(new RegExp(`${home === '/' ? '/$' : '/manager$'}`));
    await page.goto('/admin/accounts');
    await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
    expect((await page.request.get('/api/accounts')).status()).toBe(403);
    await page.locator('.header-end').getByRole('link', { name: 'Log Out', exact: true }).click();
    await page.getByRole('button', { name: 'Log Out', exact: true }).click();
    await expect(page).toHaveURL(/\/login$/);
  }
});
