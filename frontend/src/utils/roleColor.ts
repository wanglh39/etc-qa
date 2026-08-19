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

const extraShades = [
  '#2E8FFF', '#5AA8FF', '#78BAFF', '#A5D4FF', '#CCE8FF', '#D6E4FF'
]

function hashString(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0
  }
  return h
}

export function roleColor(key: string): string {
  if (roleColorMap[key]) return roleColorMap[key]
  return extraShades[hashString(key) % extraShades.length]
}

export function roleSortKey(key: string): number {
  return roleOrder[key] ?? 99
}
