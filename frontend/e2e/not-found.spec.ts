import { test, expect } from '@playwright/test'

test.describe('404 页面', () => {
  test('访问不存在的路由显示404', async ({ page }) => {
    await page.goto('/this-page-does-not-exist')
    await expect(page.locator('body')).toContainText('404')
  })

  test('404页面有返回首页按钮', async ({ page }) => {
    await page.goto('/this-page-does-not-exist')
    await expect(page.locator('button')).toBeVisible()
  })
})