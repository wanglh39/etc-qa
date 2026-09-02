<template>
  <div class="dept-detail-page">
    <el-card shadow="hover" class="header-card">
      <div class="header-wrap">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回{{ deptName }}工单列表
        </el-button>
        <span class="page-title">{{ deptName }}工单详情</span>
        <div class="header-right">
          <el-tag v-if="orderInfo.status === 'submitted'" type="info" effect="dark">
            待处理
          </el-tag>
          <el-tag v-else-if="orderInfo.status === 'answered'" type="primary" effect="dark">
            已回复
          </el-tag>
          <el-tag v-else-if="orderInfo.status === 'processed'" type="primary" effect="dark">
            已办结
          </el-tag>
          <el-tag v-if="priorityText" :type="priorityType" effect="dark" style="margin-left: 8px">
            {{ priorityText }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <div class="two-col">
      <!-- 左栏：工单信息+处理表单 -->
      <div class="left-col">
        <el-card shadow="hover" class="info-card">
          <template #header>
            <span class="section-title">工单基础信息</span>
          </template>
          <el-descriptions border :column="2">
            <el-descriptions-item label="工单ID">
              {{ orderInfo.id }}
            </el-descriptions-item>
            <el-descriptions-item label="工单编号">
              {{ orderInfo.external_id }}
            </el-descriptions-item>
            <el-descriptions-item label="提交时间">
              {{ orderInfo.created_at }}
            </el-descriptions-item>
            <el-descriptions-item label="问题类型">
              {{ orderInfo.problem_type || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="客户名称">
              {{ orderInfo.customer_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="客户手机号">
              {{ orderInfo.phone || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="问题描述" :span="2">
              <div class="question-text">
                {{ orderInfo.detail_desc || '-' }}
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 处理时间线 -->
        <el-card shadow="hover" class="timeline-card">
          <template #header>
            <span class="section-title">处理时间线</span>
          </template>
          <el-timeline>
            <el-timeline-item
              timestamp="工单提交"
              placement="top"
              :type="orderInfo.status ? 'primary' : 'info'"
            >
              <div class="timeline-content">
                <div class="tl-time">
                  {{ orderInfo.created_at || '-' }}
                </div>
                <div class="tl-desc">客服提交工单至{{ deptName }}</div>
              </div>
            </el-timeline-item>
            <el-timeline-item
              v-if="orderInfo.status === 'answered' || orderInfo.status === 'processed'"
              timestamp="已回复"
              placement="top"
              type="primary"
            >
              <div class="timeline-content">
                <div class="tl-time">
                  {{ orderInfo.updated_at || '-' }}
                </div>
                <div class="tl-desc">部门已回复处理</div>
              </div>
            </el-timeline-item>
            <el-timeline-item
              v-if="orderInfo.status === 'processed'"
              timestamp="已办结"
              placement="top"
              type="primary"
            >
              <div class="timeline-content">
                <div class="tl-time">
                  {{ orderInfo.updated_at || '-' }}
                </div>
                <div class="tl-desc">工单已办结</div>
              </div>
            </el-timeline-item>
            <el-timeline-item
              v-if="orderInfo.status === 'submitted'"
              timestamp="待处理"
              placement="top"
              type="info"
              hollow
            >
              <div class="timeline-content">
                <div class="tl-desc">等待部门处理</div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 处理表单 -->
        <el-card v-if="orderInfo.status !== 'processed'" shadow="hover" class="form-card">
          <template #header>
            <span class="section-title">处理备注</span>
          </template>

          <!-- 快捷模板 -->
          <div class="quick-templates">
            <span class="qt-label">快捷模板：</span>
            <el-button
              v-for="tpl in quickTemplates"
              :key="tpl.label"
              size="small"
              plain
              @click="applyTemplate(tpl.text)"
            >
              {{ tpl.label }}
            </el-button>
          </div>

          <el-input
            v-model="remarkText"
            type="textarea"
            :rows="5"
            placeholder="请填写工单处理过程、解决方案"
            style="margin-top: 12px"
          />

          <div class="btn-box">
            <el-button type="primary" :loading="submitting" @click="handleFinish">
              办结工单
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 右栏：知识库检索 -->
      <div class="right-col">
        <el-card shadow="hover" class="kb-card">
          <template #header>
            <div class="kb-header">
              <span class="section-title">知识库检索</span>
              <el-button text type="primary" size="small" :loading="kbLoading" @click="searchKB">
                重新搜索
              </el-button>
            </div>
          </template>

          <el-input
            v-model="kbQuery"
            placeholder="输入问题搜索知识库"
            clearable
            style="margin-bottom: 12px"
            @keyup.enter="searchKB"
          >
            <template #append>
              <el-button :loading="kbLoading" @click="searchKB"> 搜索 </el-button>
            </template>
          </el-input>

          <div v-if="kbResults.length === 0 && !kbLoading" class="kb-empty">
            <el-icon :size="32">
              <DocumentRemove />
            </el-icon>
            <p>暂无匹配结果</p>
            <p class="kb-hint">尝试用问题描述搜索，找到相似解决方案</p>
          </div>

          <div v-loading="kbLoading" class="kb-list">
            <div v-for="item in kbResults" :key="item.qa_id" class="kb-item">
              <div class="kb-item-header">
                <el-tag size="small" effect="plain">
                  {{ item.category_l1 || '未分类' }}
                </el-tag>
                <span class="kb-score">匹配度 {{ (item.score * 100).toFixed(0) }}%</span>
              </div>
              <div class="kb-question">Q: {{ item.question }}</div>
              <div class="kb-answer">A: {{ item.answer }}</div>
              <div class="kb-actions">
                <el-button text type="primary" size="small" @click="copyAnswer(item.answer)">
                  <el-icon><CopyDocument /></el-icon> 复制答案
                </el-button>
                <el-button text type="primary" size="small" @click="useAsRemark(item.answer)">
                  填入备注
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, CopyDocument, DocumentRemove } from '@element-plus/icons-vue'
import { getWorkOrderDetail, replyWorkOrder, type WorkOrderDetail } from '@/api/workorder'
import { queryQA, type CandidateResult } from '@/api/workbench'
import { copyText } from '@/utils/common'
import { getDeptList } from '@/api/system'

const route = useRoute()
const router = useRouter()

const deptNameMap = ref<Record<string, string>>({})

const deptCode = computed(() => route.params.deptCode as string)
const orderId = computed(() => route.params.orderId as string)
const deptName = computed(() => deptNameMap.value[deptCode.value] || '通用部门')

const orderInfo = ref<WorkOrderDetail>({
  id: 0,
  external_id: '',
  status: '',
  dept: '',
  service_id: '',
  customer_name: '',
  phone: '',
  problem_type: '',
  next_dept: '',
  priority: '',
  detail_desc: '',
  handle_remark: '',
})
const remarkText = ref('')
const submitting = ref(false)

const priorityText = computed(() => orderInfo.value.priority || '')
const priorityType = computed<'primary' | 'info'>(() => {
  const p = orderInfo.value.priority
  if (p === '高' || p === 'urgent') return 'primary'
  if (p === '中' || p === 'normal') return 'info'
  return 'info'
})

const quickTemplates = [
  { label: '已解决', text: '问题已核实并处理完成，已通知客户确认。' },
  { label: '需转交', text: '该问题需转交至其他部门处理，已发起转交流程，请相关部门跟进。' },
  { label: '待补充材料', text: '需要客户补充相关材料（身份证照片、订单截图等），已通知客户提供。' },
  { label: '已退款', text: '经核实符合退款条件，已发起退款流程，预计3-5个工作日到账。' },
]

const applyTemplate = (text: string) => {
  remarkText.value = text
}

const kbQuery = ref('')
const kbResults = ref<CandidateResult[]>([])
const kbLoading = ref(false)

const searchKB = async () => {
  if (!kbQuery.value.trim()) return
  kbLoading.value = true
  try {
    const res = await queryQA({ question: kbQuery.value })
    kbResults.value = res.candidates || []
  } catch {
    ElMessage.error('知识库检索失败')
  } finally {
    kbLoading.value = false
  }
}

const copyAnswer = async (answer: string) => {
  const ok = await copyText(answer)
  if (ok) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}

const useAsRemark = (answer: string) => {
  remarkText.value = answer
  ElMessage.success('已填入处理备注')
}

const getOrderDetail = async () => {
  const id = Number(orderId.value)
  if (!id) {
    ElMessage.error('缺少工单ID')
    return
  }
  try {
    const res = await getWorkOrderDetail(id)
    orderInfo.value = res
    remarkText.value = res.handle_remark || ''
    if (res.detail_desc) {
      kbQuery.value = res.detail_desc.slice(0, 50)
      searchKB()
    }
  } catch {
    ElMessage.error('加载工单详情失败')
  }
}

const handleFinish = async () => {
  if (!remarkText.value.trim()) {
    ElMessage.warning('办结前请先填写处理备注')
    return
  }
  submitting.value = true
  try {
    await replyWorkOrder(orderInfo.value.id, { handle_remark: remarkText.value })
    ElMessage.success('工单办结完成')
    router.back()
  } catch {
    ElMessage.error('办结失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const depts = await getDeptList()
    deptNameMap.value = Object.fromEntries(depts.map((d) => [d.dept_key, d.dept_name]))
  } catch {}
  getOrderDetail()
})
</script>

<style scoped>
.dept-detail-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f8fafc;
  padding: 20px;
  box-sizing: border-box;
}

.header-card {
  margin-bottom: 16px;
}
.header-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  flex: 1;
}
.header-right {
  display: flex;
  align-items: center;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 16px;
}

.left-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.right-col {
  display: flex;
  flex-direction: column;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.question-text {
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}

.timeline-content {
  font-size: 13px;
}
.tl-time {
  color: #bfbfbf;
  margin-bottom: 4px;
}
.tl-desc {
  color: #0f172a;
}

.quick-templates {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.qt-label {
  font-size: 13px;
  color: #bfbfbf;
}

.btn-box {
  text-align: right;
  margin-top: 16px;
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kb-empty {
  text-align: center;
  padding: 40px 0;
  color: #94a3b8;
}
.kb-hint {
  font-size: 12px;
  margin-top: 4px;
}

.kb-list {
  max-height: calc(100vh - 320px);
  overflow-y: auto;
}

.kb-item {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: box-shadow 0.2s;
}
.kb-item:hover {
}

.kb-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.kb-score {
  font-size: 12px;
  color: #1677ff;
  font-weight: 600;
}

.kb-question {
  font-size: 13px;
  color: #0f172a;
  font-weight: 500;
  margin-bottom: 4px;
  line-height: 1.5;
}
.kb-answer {
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-actions {
  display: flex;
  gap: 8px;
}
</style>
