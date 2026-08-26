import { test, expect, type Page } from '@playwright/test'

const MOCK_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInJvbGUiOiJhZG1pbiIsInN1YiI6ImFkbWluIn0.mock'

async function mockAuth(page: Page) {
  await page.route('**/api/auth/verify', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/**', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.addInitScript((token) => {
    sessionStorage.setItem('token', token)
    sessionStorage.setItem('userRole', 'admin')
    sessionStorage.setItem('userDept', '')
    sessionStorage.setItem('userName', 'admin')
  }, MOCK_TOKEN)
}

test.describe('404 页面', () => {
  test('访问不存在的路由显示404', async ({ page }) => {
    await mockAuth(page)
    await page.goto('/this-page-does-not-exist')
    await expect(page.locator('body')).toContainText('404')
  })

  test('404页面有返回首页按钮', async ({ page }) => {
    await mockAuth(page)
    await page.goto('/this-page-does-not-exist')
    await expect(page.locator('button')).toBeVisible()
  })
})
