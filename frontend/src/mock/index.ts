// src/mock/index.ts
// 用户列表mock数据
export const mockUserList = [
  { userId: 'U0001' },
  { userId: 'U0002' },
  { userId: 'U0003' }
]

// 知识库列表mock数据，匹配页面K001/K002/K003
export const mockKnowledgeList = [
  {
    id: 'K001',
    questionTitle: '账号登录提示验证失败怎么办',
    category: '登录失败',
    status: '已上架'
  },
  {
    id: 'K002',
    questionTitle: '银行卡重复扣款如何退款',
    category: '重复扣款',
    status: '已上架'
  },
  {
    id: 'K003',
    questionTitle: '知识库搜索不到对应问题',
    category: '系统功能类',
    status: '已下架'
  }
]

// 分类树形mock数据
export const mockCategoryTree = [
  {
    id: 1,
    label: '登录账号类',
    children: [
      { id: 11, label: '登录失败' },
      { id: 12, label: '找回密码' }
    ]
  },
  {
    id: 2,
    label: '订单支付类',
    children: [
      { id: 21, label: '重复扣款' }
    ]
  },
  {
    id: 3,
    label: '系统功能类',
    children: []
  }
]
