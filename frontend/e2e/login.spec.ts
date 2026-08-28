import { test, expect, type Page } from '@playwright/test'

const MOCK_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInJvbGUiOiJhZG1pbiIsInN1YiI6ImFkbWluIn0.mock'

async function mockAuthApis(page: Page) {
  await page.route('**/api/auth/login', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: MOCK_TOKEN,
        role: 'admin',
        dept: '',
        username: 'admin',
      }),
    })
  })
  await page.route('**/api/auth/verify', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/system/permissions', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/api/**', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
}

test.describe('登录流程', () => {
  test('页面正确渲染', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('.form-title')).toHaveText('欢迎登录')
    await expect(page.locator('input[placeholder="账号"]')).toBeVisible()
    await expect(page.locator('input[placeholder="密码"]')).toBeVisible()
    await expect(page.locator('.login-btn')).toBeVisible()
  })

  test('空表单提交显示校验错误', async ({ page }) => {
    await page.goto('/login')
    await page.locator('.login-btn').click()
    await expect(page.locator('.el-form-item__error')).toHaveCount(2)
  })

  test('登录成功后跳转到工作台', async ({ page }) => {
    await mockAuthApis(page)
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    await page.locator('input[placeholder="账号"]').fill('admin')
    await page.locator('input[placeholder="密码"]').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/workbench/admin/dashboard', { timeout: 10000 })
    await expect(page).toHaveURL(/\/workbench\/admin\/dashboard/)
  })
})