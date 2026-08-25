import { test, expect } from '@playwright/test'

test.describe('路由守卫', () => {
  test('未登录访问受保护页面跳转登录', async ({ page }) => {
    await page.goto('/workbench/admin/dashboard')
    await page.waitForURL('**/login', { timeout: 5000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test('未登录访问客服页跳转登录', async ({ page }) => {
    await page.goto('/service')
    await page.waitForURL('**/login', { timeout: 5000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test('未登录访问账号管理跳转登录', async ({ page }) => {
    await page.goto('/workbench/admin/account')
    await page.waitForURL('**/login', { timeout: 5000 })
    await expect(page).toHaveURL(/\/login/)
  })
})