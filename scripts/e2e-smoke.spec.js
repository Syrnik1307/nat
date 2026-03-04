/**
 * E2E Smoke Test — Playwright
 * 
 * Проверяет критические пользовательские сценарии после деплоя:
 * 1. Сайт загружается
 * 2. Логин работает
 * 3. Конструктор ДЗ открывается
 * 4. Пикер групп рендерится и кликабелен
 * 5. Список уроков загружается
 * 
 * Запуск:
 *   npx playwright test scripts/e2e-smoke.spec.js
 * 
 * Или без установки:
 *   npx playwright test scripts/e2e-smoke.spec.js --project=chromium
 * 
 * Переменные окружения:
 *   SMOKE_URL         — базовый URL (default: https://lectiospace.ru)
 *   SMOKE_EMAIL       — email учителя
 *   SMOKE_PASSWORD    — пароль учителя
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.SMOKE_URL || 'https://lectiospace.ru';
const EMAIL = process.env.SMOKE_EMAIL || '';
const PASSWORD = process.env.SMOKE_PASSWORD || '';

test.describe('Post-deploy smoke tests', () => {

  test('1. Site loads and shows login page', async ({ page }) => {
    const response = await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    expect(response.status()).toBe(200);
    // Either we see login form or we're already logged in
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(50);
  });

  test('2. Health check API responds', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health/`);
    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.status).toBe('ok');
  });

  test('3. Login works and returns JWT', async ({ request }) => {
    test.skip(!EMAIL || !PASSWORD, 'SMOKE_EMAIL/SMOKE_PASSWORD not set');

    const response = await request.post(`${BASE_URL}/api/jwt/token/`, {
      data: { email: EMAIL, password: PASSWORD },
    });
    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.access).toBeTruthy();
    expect(json.refresh).toBeTruthy();
  });

  test('4. Homework constructor renders with group picker', async ({ page }) => {
    test.skip(!EMAIL || !PASSWORD, 'SMOKE_EMAIL/SMOKE_PASSWORD not set');
    test.setTimeout(30000);

    // Login via API
    const tokenResponse = await page.request.post(`${BASE_URL}/api/jwt/token/`, {
      data: { email: EMAIL, password: PASSWORD },
    });
    const { access } = await tokenResponse.json();

    // Set tokens in localStorage before navigating
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.evaluate((token) => {
      localStorage.setItem('tp_access_token', token);
    }, access);

    // Navigate to homework constructor
    await page.goto(`${BASE_URL}/homework/constructor`, { waitUntil: 'networkidle' });

    // Verify the page loaded (not a blank/error page)
    await expect(page.locator('body')).not.toHaveText(/Произошла ошибка/);

    // Look for the group picker trigger or group selector area
    const picker = page.locator('[data-tour="hw-group-selector"]');
    await expect(picker).toBeVisible({ timeout: 10000 });

    // Click the picker trigger — should open the group list
    const trigger = picker.locator('button, .sp-trigger, .sp-groups-header').first();
    if (await trigger.isVisible()) {
      await trigger.click();
      // After click, some group names or checkboxes should appear
      await page.waitForTimeout(1000);
    }
  });

  test('5. Teacher API endpoints respond', async ({ request }) => {
    test.skip(!EMAIL || !PASSWORD, 'SMOKE_EMAIL/SMOKE_PASSWORD not set');

    const tokenResponse = await request.post(`${BASE_URL}/api/jwt/token/`, {
      data: { email: EMAIL, password: PASSWORD },
    });
    const { access } = await tokenResponse.json();
    const headers = { Authorization: `Bearer ${access}` };

    // /api/me/
    const meResponse = await request.get(`${BASE_URL}/api/me/`, { headers });
    expect(meResponse.status()).toBe(200);

    // /api/homework/
    const hwResponse = await request.get(`${BASE_URL}/api/homework/`, { headers });
    expect(hwResponse.status()).toBe(200);

    // /api/schedule/lessons/
    const lessonsResponse = await request.get(`${BASE_URL}/api/schedule/lessons/`, { headers });
    expect(lessonsResponse.status()).toBe(200);

    // /api/groups/
    const groupsResponse = await request.get(`${BASE_URL}/api/groups/`, { headers });
    expect(groupsResponse.status()).toBe(200);
  });

});
