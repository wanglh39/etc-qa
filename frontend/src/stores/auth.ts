import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(sessionStorage.getItem('token') ?? '')
  const role = ref(sessionStorage.getItem('userRole') ?? '')
  const username = ref(sessionStorage.getItem('userName') ?? '')
  const dept = ref(sessionStorage.getItem('userDept') ?? '')
  const impersonatorToken = ref(sessionStorage.getItem('impersonator_token') ?? '')
  const permissions = ref<string[]>(JSON.parse(sessionStorage.getItem('permissions') || '[]'))

  const isImpersonating = computed(() => !!impersonatorToken.value)

  const roleText = computed(() => {
    switch (role.value) {
      case 'admin': return '业务管理员'
      case 'superadmin': return '超级管理员'
      case 'ops': return '运维工程师'
      case 'service': return '客服'
      case 'dept': return '部门处理员'
      default: return role.value || '未知账号'
    }
  })

  function setAuth(t: string, r: string, d: string, u?: string) {
    token.value = t
    role.value = r
    dept.value = d
    if (u) username.value = u
    sessionStorage.setItem('token', t)
    sessionStorage.setItem('userRole', r)
    sessionStorage.setItem('userDept', d)
    if (u) sessionStorage.setItem('userName', u)
  }

  function startImpersonation(newToken: string, newRole: string, newDept: string, newUsername: string) {
    impersonatorToken.value = token.value
    sessionStorage.setItem('impersonator_token', token.value)
    sessionStorage.setItem('impersonator_role', role.value)
    setAuth(newToken, newRole, newDept, newUsername)
  }

  function exitImpersonation() {
    const origToken = impersonatorToken.value
    const origRole = sessionStorage.getItem('impersonator_role') ?? 'superadmin'
    if (origToken) {
      impersonatorToken.value = ''
      sessionStorage.removeItem('impersonator_token')
      sessionStorage.removeItem('impersonator_role')
      token.value = origToken
      role.value = origRole
      dept.value = ''
      sessionStorage.setItem('token', origToken)
      sessionStorage.setItem('userRole', origRole)
    }
  }

  function setPermissions(perms: string[]) {
    permissions.value = perms
    sessionStorage.setItem('permissions', JSON.stringify(perms))
  }

  function clearAuth() {
    token.value = ''
    role.value = ''
    username.value = ''
    dept.value = ''
    impersonatorToken.value = ''
    permissions.value = []
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('userRole')
    sessionStorage.removeItem('userDept')
    sessionStorage.removeItem('userName')
    sessionStorage.removeItem('impersonator_token')
    sessionStorage.removeItem('impersonator_role')
    sessionStorage.removeItem('permissions')
  }

  return {
    token,
    role,
    username,
    dept,
    impersonatorToken,
    permissions,
    isImpersonating,
    roleText,
    setAuth,
    setPermissions,
    startImpersonation,
    exitImpersonation,
    clearAuth,
  }
})