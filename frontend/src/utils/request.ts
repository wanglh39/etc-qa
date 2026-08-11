import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { WorkUser, PendingAuditItem, CategoryItem, KnowledgeItem } from '@/types'

// Mock 模拟数据
export const mockUserList: WorkUser[] = [
  { userId: 'U0001' },
  { userId: 'U0002' },
  { userId: 'U0003' }
]

export const mockPendingList: PendingAuditItem[] = [
  { orderId: 'AUD001', question: '更换手机号收不到验证码怎么办', confidence: 0.62, submitTime: '2026-07-08 09:22' },
  { orderId: 'AUD002', question: '优惠券无法正常核销', confidence: 0.83, submitTime: '2026-07-08 10:15' },
  { orderId: 'AUD003', question: '提现一直处于审核状态', confidence: 0.57, submitTime: '2026-07-08 11:36' },
  { orderId: 'AUD004', question: '购物地址修改失败', confidence: 0.74, submitTime: '2026-07-09 08:42' }
]

export const mockCategoryTree: CategoryItem[] = [
  {
    id: 'c1',
    label: '登录账号类',
    parentId: null,
    children: [
      { id: 'c1-1', label: '登录失败', parentId: 'c1' },
      { id: 'c1-2', label: '找回密码', parentId: 'c1' }
    ]
  },
  {
    id: 'c2',
    label: '订单支付类',
    parentId: null,
    children: [
      { id: 'c2-1', label: '重复扣款', parentId: 'c2' }
    ]
  },
  { id: 'c3', label: '系统功能类', parentId: null }
]

export const mockKnowledgeList: KnowledgeItem[] = [
  { ID: 'K001', questionTitle: '账号登录提示验证失败怎么办', belongClass: '登录失败', status: '已上架' },
  { ID: 'K002', questionTitle: '银行卡重复扣款如何退款', belongClass: '重复扣款', status: '已上架' },
  { ID: 'K003', questionTitle: '知识库搜索不到对应问题', belongClass: '系统功能类', status: '已下架' }
]

const service = axios.create({
  baseURL: '/api',
  timeout: 8000
})

service.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

service.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('userRole')
      localStorage.removeItem('userDept')
      window.location.href = '/login'
      return Promise.reject(err)
    }
    ElMessage.error(err.response?.data?.detail || '操作请求出错')
    return Promise.reject(err)
  }
)

// 严格类型映射，消除any
type MockUrlKey = '/workbench/users' | '/knowledge/list' | '/knowledge/categoryTree' | '/audit/pending'
const mockMap: Record<MockUrlKey, unknown[]> = {
  '/workbench/users': mockUserList,
  '/knowledge/list': mockKnowledgeList,
  '/knowledge/categoryTree': mockCategoryTree,
  '/audit/pending': mockPendingList
}

export const mockDispatch = async (url: MockUrlKey) => {
  return Promise.resolve({ data: mockMap[url] })
}

export default service
