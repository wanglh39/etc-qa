import { describe, it, expect } from 'vitest'
import { mockUserList, mockKnowledgeList, mockCategoryTree } from '@/mock/index'

describe('mock/index', () => {
  it('mockUserList has 3 users', () => {
    expect(mockUserList).toHaveLength(3)
    mockUserList.forEach((u) => expect(u).toHaveProperty('userId'))
  })

  it('mockKnowledgeList has 3 items with required fields', () => {
    expect(mockKnowledgeList).toHaveLength(3)
    mockKnowledgeList.forEach((k) => {
      expect(k).toHaveProperty('id')
      expect(k).toHaveProperty('questionTitle')
      expect(k).toHaveProperty('category')
      expect(k).toHaveProperty('status')
    })
  })

  it('mockCategoryTree has 3 top-level categories', () => {
    expect(mockCategoryTree).toHaveLength(3)
    expect(mockCategoryTree[0].children).toHaveLength(2)
    expect(mockCategoryTree[1].children).toHaveLength(1)
    expect(mockCategoryTree[2].children).toHaveLength(0)
  })
})
