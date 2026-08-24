import { describe, it, expect } from 'vitest'
import { categoryTree, getFlatTree, knowledgeList } from '@/mock/knowledge'

describe('mock/knowledge', () => {
  it('categoryTree has 3 top-level categories', () => {
    expect(categoryTree).toHaveLength(3)
    categoryTree.forEach((c) => {
      expect(c).toHaveProperty('id')
      expect(c).toHaveProperty('name')
      expect(c).toHaveProperty('parentId')
      expect(c).toHaveProperty('desc')
    })
  })

  it('first category has 2 children', () => {
    expect(categoryTree[0].children).toHaveLength(2)
  })

  it('getFlatTree flattens tree correctly', () => {
    const flat = getFlatTree(categoryTree)
    expect(flat.length).toBe(6)
    expect(flat[0].id).toBe('1')
    expect(flat[1].id).toBe('1-1')
    expect(flat[2].id).toBe('1-2')
    expect(flat[3].id).toBe('2')
    expect(flat[4].id).toBe('2-1')
    expect(flat[5].id).toBe('3')
  })

  it('getFlatTree handles empty tree', () => {
    expect(getFlatTree([])).toEqual([])
  })

  it('getFlatTree handles tree without children', () => {
    const tree = [{ id: 'x', name: 'X', parentId: '', desc: '' }]
    expect(getFlatTree(tree)).toEqual(tree)
  })

  it('knowledgeList has 3 items', () => {
    expect(knowledgeList).toHaveLength(3)
    knowledgeList.forEach((k) => {
      expect(k).toHaveProperty('id')
      expect(k).toHaveProperty('question')
      expect(k).toHaveProperty('answer')
      expect(k).toHaveProperty('categoryId')
      expect(k).toHaveProperty('categoryName')
      expect(k).toHaveProperty('status')
      expect([0, 1]).toContain(k.status)
    })
  })
})
