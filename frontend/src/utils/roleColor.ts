const roleColorMap: Record<string, string> = {
  superadmin: '#0958D9',
  admin: '#1677FF',
  ops: '#4096FF',
  service: '#69B1FF',
  dept: '#91CAFF'
}

const roleOrder: Record<string, number> = {
  superadmin: 0,
  admin: 1,
  ops: 2,
  service: 3,
  dept: 4
}

export function roleColor(key: string): string {
  return roleColorMap[key] || '#1677FF'
}

export function roleSortKey(key: string): number {
  return roleOrder[key] ?? 99
}