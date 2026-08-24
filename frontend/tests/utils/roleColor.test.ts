import { describe, it, expect } from 'vitest'
import { roleColor, roleSortKey } from '../../src/utils/roleColor'

describe('roleColor', () => {
  it('returns correct color for superadmin', () => {
    expect(roleColor('superadmin')).toBe('#0958D9')
  })

  it('returns correct color for admin', () => {
    expect(roleColor('admin')).toBe('#1677FF')
  })

  it('returns correct color for ops', () => {
    expect(roleColor('ops')).toBe('#4096FF')
  })

  it('returns correct color for service', () => {
    expect(roleColor('service')).toBe('#69B1FF')
  })

  it('returns correct color for dept', () => {
    expect(roleColor('dept')).toBe('#91CAFF')
  })

  it('returns a shade from extraShades for unknown role', () => {
    const extraShades = ['#2E8FFF', '#5AA8FF', '#78BAFF', '#A5D4FF', '#CCE8FF', '#D6E4FF']
    const result = roleColor('unknown_role')
    expect(extraShades).toContain(result)
  })

  it('returns consistent color for same unknown role', () => {
    expect(roleColor('custom_role')).toBe(roleColor('custom_role'))
  })

  it('returns different colors for different unknown roles (likely)', () => {
    const colors = new Set(
      ['role_a', 'role_b', 'role_c', 'role_d', 'role_e', 'role_f'].map(roleColor)
    )
    expect(colors.size).toBeGreaterThan(1)
  })
})

describe('roleSortKey', () => {
  it('returns 0 for superadmin', () => {
    expect(roleSortKey('superadmin')).toBe(0)
  })

  it('returns 1 for admin', () => {
    expect(roleSortKey('admin')).toBe(1)
  })

  it('returns 2 for ops', () => {
    expect(roleSortKey('ops')).toBe(2)
  })

  it('returns 3 for service', () => {
    expect(roleSortKey('service')).toBe(3)
  })

  it('returns 4 for dept', () => {
    expect(roleSortKey('dept')).toBe(4)
  })

  it('returns 99 for unknown role', () => {
    expect(roleSortKey('unknown')).toBe(99)
  })

  it('returns 99 for empty string', () => {
    expect(roleSortKey('')).toBe(99)
  })
})
