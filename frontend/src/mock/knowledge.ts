// 分类树形类型
export interface CategoryItem {
  id: string
  name: string
  parentId: string
  desc: string
  children?: CategoryItem[]
}
// 树形分类数据
export const categoryTree: CategoryItem[] = [
  {
    id: '1',
    name: '登录账号类',
    parentId: '',
    desc: '账号登录、密码重置、验证码相关问题',
    children: [
      { id: '1-1', name: '登录失败', parentId: '1', desc: '账号密码错误、风控拦截' },
      { id: '1-2', name: '找回密码', parentId: '1', desc: '忘记密码、收不到验证码' },
    ],
  },
  {
    id: '2',
    name: '订单支付类',
    parentId: '',
    desc: '扣款、退款、订单异常咨询',
    children: [{ id: '2-1', name: '重复扣款', parentId: '2', desc: '多次扣款未自动退回' }],
  },
  { id: '3', name: '系统功能类', parentId: '', desc: '知识库检索、页面功能报错' },
]

// 树形扁平化函数
export const getFlatTree = (tree: CategoryItem[]): CategoryItem[] => {
  let res: CategoryItem[] = []
  const loop = (list: CategoryItem[]) => {
    list.forEach((item) => {
      res.push(item)
      if (item.children) loop(item.children)
    })
  }
  loop(tree)
  return res
}

// 知识库列表类型
export interface KnowledgeRow {
  id: string
  question: string
  answer: string
  categoryId: string
  categoryName: string
  status: 0 | 1
}
// 知识库模拟数据
export const knowledgeList: KnowledgeRow[] = [
  {
    id: 'K001',
    question: '账号登录提示验证失败怎么办',
    answer: '清除浏览器缓存，重置密码后重试，持续失败可提交工单核验账号风控',
    categoryId: '1-1',
    categoryName: '登录失败',
    status: 1,
  },
  {
    id: 'K002',
    question: '银行卡重复扣款如何退款',
    answer: '系统1-3个工作日自动原路退回，加急可上传扣款凭证提交工单',
    categoryId: '2-1',
    categoryName: '重复扣款',
    status: 1,
  },
  {
    id: 'K003',
    question: '知识库搜索不到对应问题',
    answer: '更换关键词检索，检查分类层级是否配置错误',
    categoryId: '3',
    categoryName: '系统功能类',
    status: 0,
  },
]
