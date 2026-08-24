import { describe, it, expect, vi } from 'vitest'
import { formatTime, flattenTree } from '../../src/utils/common'

describe('formatTime', () => {
  it('returns string in YYYY-MM-DD HH:mm format', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 7, 24, 14, 5))
    const result = formatTime()
    expect(result).toBe('2026-08-24 14:05')
    vi.useRealTimers()
  })

  it('pads single digit month/day/hour/minute with leading zero', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 0, 1, 0, 0))
    const result = formatTime()
    expect(result).toBe('2026-01-01 00:00')
    vi.useRealTimers()
  })

  it('does not pad double digit values', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 11, 31, 23, 59))
    const result = formatTime()
    expect(result).toBe('2026-12-31 23:59')
    vi.useRealTimers()
  })
})

describe('flattenTree', () => {
  it('returns empty array for empty input', () => {
    expect(flattenTree([])).toEqual([])
  })

  it('flattens single level without children', () => {
    const input = [
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
    ]
    expect(flattenTree(input)).toEqual(input)
  })

  it('flattens two levels with default children key', () => {
    const input = [{ id: 1, name: 'parent', children: [{ id: 2, name: 'child' }] }]
    const result = flattenTree(input)
    expect(result).toHaveLength(2)
    expect(result[0].id).toBe(1)
    expect(result[1].id).toBe(2)
  })

  it('flattens three levels nested', () => {
    const input = [
      {
        id: 1,
        children: [{ id: 2, children: [{ id: 3 }] }],
      },
    ]
    const result = flattenTree(input)
    expect(result).toHaveLength(3)
    expect(result.map((r) => r.id)).toEqual([1, 2, 3])
  })

  it('supports custom key', () => {
    const input = [{ id: 1, subs: [{ id: 2 }] }]
    const result = flattenTree(input, 'subs')
    expect(result).toHaveLength(2)
  })

  it('handles mixed nodes with and without children', () => {
    const input = [
      { id: 1, children: [{ id: 2 }] },
      { id: 3 },
      { id: 4, children: [{ id: 5 }, { id: 6 }] },
    ]
    const result = flattenTree(input)
    expect(result).toHaveLength(6)
    expect(result.map((r) => r.id)).toEqual([1, 2, 3, 4, 5, 6])
  })
})
