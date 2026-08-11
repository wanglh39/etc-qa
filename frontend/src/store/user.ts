import { defineStore } from 'pinia'
export const useUserStore = defineStore('user', {
  state: () => ({
    role: 'admin', // admin / operator
    permission: ['workbench', 'knowledge', 'audit', 'dashboard', 'system']
  }),
  actions: {
    hasPerm(key: string): boolean {
      return this.permission.includes(key)
    },
    switchRole(val: string) {
      this.role = val
      if (val === 'operator') {
        this.permission = ['workbench', 'knowledge', 'audit', 'dashboard']
      } else {
        this.permission = ['workbench', 'knowledge', 'audit', 'dashboard', 'system']
      }
    }
  }
})
