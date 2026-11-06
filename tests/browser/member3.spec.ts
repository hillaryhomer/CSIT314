import { test, expect, type Page } from '@playwright/test';

const password = 'browser test password 123';
const image = { name: 'project.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAEUlEQVR4nGP8z4AATEhsPBwAM9EBBzDn4UwAAAAASUVORK5CYII=', 'base64') };
async function login(page: Page, username = 'browser.designer') {
  await page.goto('/login');
  await page.getByLabel('Username or email', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Log In', exact: true }).click();
  await expect(page).toHaveURL(username.includes('designer') ? /\/designer$/ : /\/manager$/);
}
async function fillProject(page: Page, title: string) {
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Project title', { exact: true }).fill(title);
  await dialog.getByLabel('Category', { exact: true }).selectOption('CAT001');
  await dialog.getByLabel('Style', { exact: true }).fill('Japandi');
  await dialog.getByLabel('Project description', { exact: true }).fill('Material-led residential design');
}

for (const kind of ['current', 'past'] as const) {
  test(`${kind}: create/view/update/delete/search, images, cancel, reload and shared customer data`, async ({ page }) => {
    await login(page);
    const title = `${kind} Studio ${Date.now()}`;
    await page.goto(`/designer/${kind}`);
    await page.getByRole('button', { name: 'Add Project' }).click();
    await fillProject(page, 'Cancelled project');
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
    expect((await (await page.request.get(`/api/designer/projects/${kind}`)).json()).length).toBe(0);
    await page.getByRole('button', { name: 'Add Project' }).click();
    await fillProject(page, title);
    await page.getByLabel('Images (optional)', { exact: true }).setInputFiles(image);
    await expect(page.getByRole('dialog').getByAltText('Project image 1')).toBeVisible();
    await page.getByRole('button', { name: 'Save Project', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    let row = page.getByRole('row').filter({ hasText: title });
    await expect(row).toHaveCount(1);
    await page.reload();
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'View', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText('Material-led residential design');
    await expect(page.getByRole('dialog').getByAltText(`${title}, image 1`)).toBeVisible();
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
    await row.getByRole('button', { name: 'Edit', exact: true }).click();
    await expect(page.getByLabel('Project title', { exact: true })).toHaveValue(title);
    await page.getByLabel('Project title', { exact: true }).fill('Cancelled update');
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'Edit', exact: true }).click();
    await page.getByLabel('Project title', { exact: true }).fill(title + ' Updated');
    await page.getByRole('button', { name: 'Remove image 1' }).click();
    await page.getByLabel('Images (optional)', { exact: true }).setInputFiles({ ...image, name: 'replacement.png' });
    await page.getByRole('button', { name: 'Save Project', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    row = page.getByRole('row').filter({ hasText: title + ' Updated' });
    await expect(row).toBeVisible();
    const search = page.getByPlaceholder(`Search ${kind} projects by keyword...`);
    await search.fill('MATERIAL-LED'); await expect(row).toBeVisible();
    await search.fill('no-such-project'); await expect(page.getByText('No matching projects', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Clear search' }).click(); await expect(row).toBeVisible();
    await page.goto('/');
    await page.getByPlaceholder('Search projects by title, description or style...').fill(title);
    const card = page.locator('.project-card').filter({ hasText: title });
    await expect(card).toContainText(title + ' Updated');
    await card.getByRole('button', { name: 'View Details', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText(title + ' Updated');
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
    await page.goto(`/designer/${kind}`);
    await row.getByRole('button', { name: 'Delete', exact: true }).click();
    await expect(page.getByRole('dialog')).toContainText(title + ' Updated');
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'Delete', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Delete Project', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await page.reload();
    await expect(page.getByText(`No ${kind} projects yet`, { exact: true })).toBeVisible();
    const publicProjects = await (await page.request.get('/api/catalog/projects')).json();
    expect(publicProjects.some((p: { title: string }) => p.title === title + ' Updated')).toBe(false);
  });
}

test('invalid image, save failure, retry, missing detail and loading error remain distinct', async ({ page }) => {
  await login(page);
  await page.goto('/designer/current');
  await page.getByRole('button', { name: 'Add Project' }).click();
  const title = 'Retry Project';
  await fillProject(page, title);
  await page.getByLabel('Images (optional)', { exact: true }).setInputFiles({ name: 'fake.png', mimeType: 'image/png', buffer: Buffer.from('<svg/>') });
  await page.getByRole('button', { name: 'Save Project', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Use a valid');
  expect((await (await page.request.get('/api/designer/projects/current')).json()).length).toBe(0);
  await page.getByRole('button', { name: 'Remove image 1' }).click();
  await page.getByLabel('Images (optional)', { exact: true }).setInputFiles(image);
  let submissions = 0;
  await page.route('**/api/designer/projects/current', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    submissions++;
    await new Promise(resolve => setTimeout(resolve, 200));
    return route.fulfill({ status: 500, json: { error: { code: 'PERSISTENCE', message: 'The project could not be stored.', fields: {} } } });
  });
  await page.getByRole('button', { name: 'Save Project', exact: true }).evaluate(button => {
    const form = button.closest('form')!;
    form.requestSubmit(); form.requestSubmit();
  });
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('could not be stored');
  expect(submissions).toBe(1);
  await expect(page.getByLabel('Project title', { exact: true })).toHaveValue(title);
  await expect(page.locator('.toast')).not.toHaveClass(/visible/);
  await page.unroute('**/api/designer/projects/current');
  await page.getByRole('button', { name: 'Save Project', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  const row = page.getByRole('row').filter({ hasText: title }); await expect(row).toBeVisible();
  await page.route('**/api/designer/projects/current/*', route => route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Project was not found.', fields: {} } } }));
  await row.getByRole('button', { name: 'View', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('not found');
  await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click(); await page.unroute('**/api/designer/projects/current/*');
  await page.route('**/api/designer/projects/current?q=*', route => route.fulfill({ status: 500, json: { error: { code: 'PERSISTENCE', message: 'Project list failed.', fields: {} } } }));
  await page.reload(); await expect(page.getByRole('alert')).toContainText('Project list failed');
  await expect(page.getByText('No current projects yet', { exact: true })).toHaveCount(0);
  await page.unroute('**/api/designer/projects/current?q=*'); await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(row).toBeVisible();
});

test('shared category records and real project references replace category/analytics fixtures', async ({ page }) => {
  await login(page);
  const session = await (await page.request.get('/api/auth/session')).json();
  const created = await page.request.post('/api/designer/projects/current', { headers: { 'X-CSRF-Token': session.csrfToken }, data: { title: 'Analytics Reference Project', description: 'A stored project reference', categoryId: 'CAT001', style: 'Modern', images: [] } });
  expect(created.status()).toBe(201);
  await page.goto('/designer/analytics');
  await expect(page.getByRole('row').filter({ hasText: 'Analytics Reference Project' })).toBeVisible();
  const analytics = page.getByRole('row').filter({ hasText: 'Analytics Reference Project' });
  await expect(analytics.locator('td').nth(3)).toHaveText('0');
  await expect(analytics.locator('td').nth(4)).toHaveText('0');
  await page.goto('/logout'); await page.getByRole('button', { name: 'Log Out', exact: true }).click();
  await login(page, 'browser.manager'); await page.goto('/manager/categories');
  await expect(page.getByRole('row').filter({ hasText: 'CAT001' })).toContainText('Residential');
  expect((await (await page.request.get('/api/project-categories')).json()).length).toBe(3);
});
