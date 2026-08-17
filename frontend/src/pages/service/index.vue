<template>
  <div class="service-workbench">
    <!-- 左栏：辅助面板 -->
    <div class="left-panel">
      <!-- 快捷话术模板 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><ChatDotRound /></el-icon>
          快捷话术
        </div>
        <el-collapse v-model="activeReplyGroups">
          <el-collapse-item v-for="group in quickReplyGroups" :key="group.title" :title="group.title" :name="group.title">
            <div
              v-for="(msg, i) in group.items"
              :key="i"
              class="reply-item"
              @click="insertReply(msg)"
            >
              {{ msg }}
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 知识库分类 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><Files /></el-icon>
          知识库分类
        </div>
        <el-input
          v-model="categoryFilter"
          placeholder="搜索分类"
          size="small"
          clearable
          style="margin-bottom: 8px"
        />
        <el-tree
          :data="categoryTree"
          :props="{ label: 'label', children: 'children' }"
          :filter-node-method="filterCategoryNode"
          ref="categoryTreeRef"
          node-key="label"
          highlight-current
          @node-click="onCategoryClick"
          style="background: transparent"
        />
        <el-button v-if="selectedCategory" size="small" text type="primary" @click="clearCategoryFilter" style="margin-top: 8px">
          清除分类筛选
        </el-button>
      </div>
    </div>

    <!-- 主区：工作台 -->
    <div class="main-area">
      <el-card>
        <!-- 搜索区 -->
        <div class="search-section">
          <el-input
            v-model="searchText"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入或粘贴客户问题（Enter搜索，对话记录请先总结为标准问题）"
            @keydown.enter.exact.prevent="handleSearch"
          />
          <div class="button-row">
            <el-button
              :icon="Microphone"
              circle
              size="large"
              :type="asr.isRecording.value ? 'danger' : 'default'"
              @click="toggleRecording"
              :title="asr.isRecording.value ? '停止录音' : '语音转文字'"
            />
            <el-button type="danger" size="large" @click="openCreateDialog">创建工单</el-button>
            <el-button type="primary" size="large" :loading="searching" @click="handleSearch">搜索</el-button>
            <el-button size="large" @click="clearAll" :disabled="asr.isRecording.value">清空</el-button>
          </div>
          <div v-if="selectedCategory" class="category-hint">
            <el-tag type="warning" closable @close="clearCategoryFilter">
              分类筛选: {{ selectedCategory }}
            </el-tag>
          </div>
        </div>

        <!-- 实时识别区 -->
        <div v-if="asr.isRecording.value || asr.fullText.value" class="asr-section">
          <div class="asr-header">
            <span class="asr-title">
              <el-tag v-if="asr.isRecording.value" type="danger" size="small" effect="dark">录音中</el-tag>
              实时语音识别
            </span>
            <el-tag size="small" type="info">{{ asr.asrState.value }}</el-tag>
          </div>
          <div class="asr-text">
            <span class="asr-full">{{ asr.fullText.value }}</span>
            <span class="asr-partial">{{ asr.partialText.value }}</span>
          </div>
          <div v-if="asr.errorMsg.value" class="asr-error">{{ asr.errorMsg.value }}</div>
        </div>

        <!-- 空状态 -->
        <div v-if="!searched" class="empty-state">
          <el-empty description="输入客户问题，搜索匹配的标准回复话术" />
        </div>

        <!-- 结果区 -->
        <div v-if="searched" class="result-section">
          <!-- 最终回复区 -->
          <div class="reply-area">
            <div class="reply-header">
              <span class="reply-title">{{ hasCandidates ? '最终答复' : '无匹配结果' }}</span>
              <el-button v-if="hasCandidates && finalReply" size="small" type="primary" plain @click="copyToClipboard(finalReply)">
                <el-icon style="margin-right: 4px"><CopyDocument /></el-icon>
                复制答复
              </el-button>
            </div>
            <el-input
              v-if="hasCandidates"
              v-model="finalReply"
              type="textarea"
              :rows="5"
              placeholder="勾选候选答案后自动填充，可自行修改"
            />
            <el-empty
              v-else
              description="未检索到匹配结果，可创建工单流转到对应部门处理"
              :image-size="80"
            />
          </div>

          <!-- 检索信息 -->
          <div v-if="hasCandidates" class="meta-row">
            <div class="std-query">
              <span class="label">标准化问题：</span>
              <span>{{ queryResult.standardized_query || queryResult.query }}</span>
            </div>
            <div class="confidence-tag">
              置信度：
              <el-tag :type="confidenceType" size="small">{{ confidenceText }}</el-tag>
            </div>
          </div>

          <!-- 候选卡片 -->
          <div v-if="hasCandidates" class="candidate-list">
            <div
              v-for="(item, idx) in queryResult.candidates"
              :key="item.qa_id"
              class="candidate-card"
              :class="{ selected: isSelected(item.qa_id) }"
            >
              <div class="card-header">
                <el-button
                  size="small"
                  :type="isSelected(item.qa_id) ? 'primary' : 'default'"
                  @click="toggleSelect(item)"
                >
                  {{ isSelected(item.qa_id) ? '已选' : '选择' }}
                </el-button>
                <el-button size="small" text @click="copyToClipboard(item.answer)">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <span class="card-rank">#{{ idx + 1 }}</span>
                <span class="card-category" v-if="item.category_l1">
                  {{ item.category_l1 }}{{ item.category_l2 ? ' / ' + item.category_l2 : '' }}
                </span>
                <span class="card-score" :style="{ color: scoreColor(item.score) }">
                  {{ (item.score * 100).toFixed(1) }}%
                </span>
              </div>
              <div class="card-question">{{ item.question }}</div>
              <div class="card-answer">{{ item.answer }}</div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>

  <!-- 工单弹窗 -->
  <el-dialog v-model="dialogVisible" title="创建 CRM 工单" width="640px" destroy-on-close>
    <el-form ref="formRef" :model="workForm" :rules="workRules" label-width="120px">
      <el-form-item label="发起客服ID" prop="service_id">
        <el-input v-model="workForm.service_id" placeholder="输入当前客服工号" />
      </el-form-item>
      <el-form-item label="客户名称" prop="customer_name">
        <el-input v-model="workForm.customer_name" placeholder="填写客户称呼" />
      </el-form-item>
      <el-form-item label="客户联系电话" prop="phone">
        <el-input v-model="workForm.phone" placeholder="输入客户手机号码" />
      </el-form-item>
      <el-form-item label="问题分类" prop="problem_type">
        <el-select v-model="workForm.problem_type" placeholder="挑选问题分类" style="width: 100%">
          <el-option label="产品咨询" value="consult" />
          <el-option label="售后退换" value="refund" />
          <el-option label="系统故障" value="fault" />
          <el-option label="投诉建议" value="complaint" />
        </el-select>
      </el-form-item>
      <el-form-item label="转交处理部门" prop="next_dept">
        <el-select v-model="workForm.next_dept" placeholder="选择需要处理的部门" style="width: 100%">
          <el-option label="售后处理部" value="aftersale" />
          <el-option label="技术运维部" value="ops" />
          <el-option label="财务部" value="finance" />
          <el-option label="市场部" value="market" />
          <el-option label="人事部" value="human" />
        </el-select>
      </el-form-item>
      <el-form-item label="工单优先级" prop="priority">
        <el-radio-group v-model="workForm.priority">
          <el-radio value="low">低</el-radio>
          <el-radio value="mid">中等</el-radio>
          <el-radio value="high">紧急</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="问题描述" prop="detail_desc">
        <el-input
          v-model="workForm.detail_desc"
          type="textarea"
          :rows="4"
          placeholder="完整记录客户诉求、沟通情况"
          @keydown.ctrl.enter.prevent="submitWorkOrder"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitWorkOrder">提交工单 (Ctrl+Enter)</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Microphone, CopyDocument, ChatDotRound, Files } from '@element-plus/icons-vue'
import { queryQA, type QueryResponse, type CandidateResult } from '@/api/workbench'
import { createWorkOrder } from '@/api/workorder'
import { getCategories } from '@/api/knowledge'
import { useStreamingASR } from '@/composables/useStreamingASR'

// ===== 快捷话术模板 =====
const quickReplyGroups = [
  {
    title: '感谢语',
    items: [
      '感谢您的来电，请问还有其他可以帮到您的吗？',
      '感谢您的耐心等待，给您带来不便敬请谅解',
      '感谢您的配合，祝您生活愉快',
    ]
  },
  {
    title: '安抚语',
    items: [
      '非常抱歉给您带来不便，我马上为您处理',
      '请您不要着急，我帮您核实一下具体情况',
      '理解您的心情，我们会尽快为您解决此问题',
    ]
  },
  {
    title: '引导语',
    items: [
      '请问您方便提供一下订单号吗？',
      '请您详细描述一下遇到的问题，我好为您查询',
      '建议您先尝试重新登录，看问题是否解决',
    ]
  },
  {
    title: '结束语',
    items: [
      '如有其他问题随时欢迎致电，感谢您的来电',
      '已为您记录问题，后续有进展会第一时间通知您',
      '请您保持手机畅通，工作人员会尽快联系您',
    ]
  },
]
const activeReplyGroups = ref(['感谢语'])

const insertReply = (msg: string) => {
  if (finalReply.value) {
    finalReply.value += '\n\n' + msg
  } else {
    finalReply.value = msg
  }
  ElMessage.success('已插入话术')
}

// ===== 知识库分类 =====
interface CategoryNode {
  label: string
  children?: CategoryNode[]
}
const categoryTree = ref<CategoryNode[]>([])
const categoryFilter = ref('')
const selectedCategory = ref('')
const categoryTreeRef = ref()

const loadCategories = async () => {
  try {
    const res = await getCategories()
    const cats = (res as any).categories || res || []
    const tree: CategoryNode[] = []
    const map = new Map<string, CategoryNode>()
    for (const c of cats) {
      const label = c.label || c.name || c.category_l1
      if (!label) continue
      if (c.parent_id == null || c.parent_id === 0) {
        const node: CategoryNode = { label, children: [] }
        map.set(c.id ?? label, node)
        tree.push(node)
      }
    }
    for (const c of cats) {
      const label = c.label || c.name || c.category_l2
      if (!label) continue
      if (c.parent_id != null && c.parent_id !== 0) {
        const parent = map.get(c.parent_id)
        if (parent) {
          parent.children!.push({ label })
        }
      }
    }
    categoryTree.value = tree.length > 0 ? tree : cats.map((c: any) => ({ label: c.label || c.name || String(c) }))
  } catch {
    categoryTree.value = []
  }
}

watch(categoryFilter, (val) => {
  categoryTreeRef.value?.filter(val)
})

const filterCategoryNode = (value: string, data: CategoryNode) => {
  if (!value) return true
  return data.label.includes(value)
}

const onCategoryClick = (node: CategoryNode) => {
  selectedCategory.value = node.label
  if (searchText.value.trim()) {
    handleSearch()
  }
}

const clearCategoryFilter = () => {
  selectedCategory.value = ''
  if (searchText.value.trim()) {
    handleSearch()
  }
}

// ===== 复制到剪贴板 =====
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

// ===== 输入 & 检索 =====
const searchText = ref('')
const searching = ref(false)
const searched = ref(false)
const queryResult = ref<QueryResponse>({
  query: '',
  standardized_query: '',
  confidence: '',
  candidates: [],
  total_candidates: 0
})
const hasCandidates = computed(() => queryResult.value.candidates.length > 0)

// ===== 置信度 =====
const confidenceType = ref<'success' | 'warning' | 'danger' | 'info'>('info')
const confidenceText = ref('')
const confidenceMap: Record<string, { type: 'success' | 'warning' | 'danger' | 'info'; text: string }> = {
  high: { type: 'success', text: '高' },
  mid: { type: 'warning', text: '中' },
  low: { type: 'danger', text: '低' },
  none: { type: 'info', text: '无匹配' }
}

const scoreColor = (score: number) => {
  if (score >= 0.8) return '#67C23A'
  if (score >= 0.6) return '#E6A23C'
  return '#F56C6C'
}

// ===== 候选多选 & 最终答复 =====
const selectedIds = ref<number[]>([])
const finalReply = ref('')

const isSelected = (qaId: number) => selectedIds.value.includes(qaId)

const toggleSelect = (item: CandidateResult) => {
  const idx = selectedIds.value.indexOf(item.qa_id)
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1)
  } else {
    selectedIds.value.push(item.qa_id)
  }
  rebuildFinalReply()
}

const rebuildFinalReply = () => {
  const parts = queryResult.value.candidates
    .filter((c) => selectedIds.value.includes(c.qa_id))
    .map((c) => c.answer)
  finalReply.value = parts.join('\n\n')
}

// ===== 流式语音识别 =====
const asr = useStreamingASR()

const clearAll = () => {
  searchText.value = ''
  searched.value = false
  selectedIds.value = []
  finalReply.value = ''
  queryResult.value = { query: '', standardized_query: '', confidence: '', candidates: [], total_candidates: 0 }
  confidenceType.value = 'info'
  confidenceText.value = ''
  asr.fullText.value = ''
  asr.partialText.value = ''
  asr.queryResult.value = null
  asr.errorMsg.value = ''
  asr.reset()
}

const toggleRecording = async () => {
  if (asr.isRecording.value) {
    asr.stopRecording()
    if (asr.fullText.value) {
      searchText.value = asr.fullText.value
    }
  } else {
    clearAll()
    try {
      await asr.startRecording()
    } catch (e: any) {
      const msg = e?.message || ''
      if (msg.includes('非安全上下文') || msg.includes('mediaDevices')) {
        ElMessage.error(msg)
      } else if (msg.includes('NotAllowed') || msg.includes('Permission')) {
        ElMessage.error('麦克风权限被拒绝，请在浏览器设置中允许访问麦克风后重试')
      } else if (msg.includes('NotFound') || msg.includes('DevicesNotFoundError')) {
        ElMessage.error('未检测到麦克风设备，请确认麦克风已连接')
      } else if (msg.includes('WebSocket')) {
        ElMessage.error('WebSocket连接失败，请确认后端服务已启动')
      } else {
        ElMessage.error(`录音启动失败: ${msg || '请检查麦克风权限'}`)
      }
    }
  }
}

watch(() => asr.queryResult.value, (result) => {
  if (result && result.candidates.length > 0) {
    queryResult.value = {
      query: result.query_text,
      standardized_query: result.standardized_query || result.query_text,
      confidence: result.confidence,
      candidates: result.candidates as CandidateResult[],
      total_candidates: result.candidates.length
    }
    const info = confidenceMap[result.confidence] || confidenceMap.none
    confidenceType.value = info.type
    confidenceText.value = info.text
    selectedIds.value = []
    finalReply.value = ''
    searched.value = true
  }
})

// ===== 搜索 =====
const handleSearch = async () => {
  const q = searchText.value.trim()
  if (!q) {
    ElMessage.warning('请输入问题')
    return
  }
  searching.value = true
  try {
    const res = await queryQA({
      question: q,
      category_l1: selectedCategory.value || undefined
    } as any)
    queryResult.value = res
    selectedIds.value = []
    finalReply.value = ''
    const info = confidenceMap[res.confidence] || confidenceMap.none
    confidenceType.value = info.type
    confidenceText.value = info.text
    searched.value = true
  } catch {
    ElMessage.error('查询失败')
  } finally {
    searching.value = false
  }
}

// ===== 工单弹窗 =====
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const workForm = ref({
  service_id: '',
  customer_name: '',
  phone: '',
  problem_type: '',
  next_dept: '',
  priority: 'mid',
  detail_desc: ''
})

const workRules: FormRules = {
  service_id: [{ required: true, message: '请填写发起客服ID', trigger: 'blur' }],
  customer_name: [{ required: true, message: '客户名称不能为空', trigger: 'blur' }],
  phone: [
    { required: true, message: '手机号必填', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式有误', trigger: 'blur' }
  ],
  problem_type: [{ required: true, message: '需要选择问题分类', trigger: 'change' }],
  next_dept: [{ required: true, message: '请选择转交处理部门', trigger: 'change' }],
  detail_desc: [{ required: true, message: '填写客户问题详情', trigger: 'blur' }]
}

const openCreateDialog = () => {
  workForm.value.detail_desc = searchText.value
  dialogVisible.value = true
}

const submitWorkOrder = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请完善全部必填信息后再提交')
    return
  }
  submitting.value = true
  try {
    await createWorkOrder({
      service_id: workForm.value.service_id,
      customer_name: workForm.value.customer_name,
      phone: workForm.value.phone,
      problem_type: workForm.value.problem_type,
      next_dept: workForm.value.next_dept,
      priority: workForm.value.priority,
      detail_desc: workForm.value.detail_desc
    })
    ElMessage.success('工单已提交，转交对应业务部门处理')
    dialogVisible.value = false
  } catch {
    ElMessage.error('工单提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.service-workbench {
  display: flex;
  gap: 16px;
  height: 100%;
}

/* 左栏 */
.left-panel {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}
.panel-section {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #ebeef5;
}
.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.reply-item {
  padding: 6px 8px;
  font-size: 13px;
  color: #606266;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.5;
}
.reply-item:hover {
  background: #ecf5ff;
  color: #409eff;
}

/* 主区 */
.main-area {
  flex: 1;
  overflow-y: auto;
}
.main-area :deep(.el-card__body) {
  padding: 24px;
}

.search-section {
  max-width: 900px;
  margin: 0 auto;
}
.button-row {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 16px;
}
.category-hint {
  margin-top: 8px;
}

/* 实时识别区 */
.asr-section {
  max-width: 900px;
  margin: 16px auto 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #f8f9fa;
}
.asr-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.asr-title {
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 6px;
}
.asr-text {
  font-size: 16px;
  line-height: 1.8;
  min-height: 28px;
}
.asr-full {
  color: #303133;
}
.asr-partial {
  color: #909399;
  font-style: italic;
}
.asr-error {
  color: #f56c6c;
  font-size: 13px;
  margin-top: 8px;
}

.empty-state {
  margin-top: 60px;
}

.result-section {
  max-width: 900px;
  margin: 24px auto 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 最终回复区 */
.reply-area {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fafafa;
}
.reply-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.reply-title {
  font-weight: 600;
  color: #303133;
}

/* 检索信息 */
.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.std-query {
  font-size: 15px;
}
.std-query .label {
  color: #909399;
}
.confidence-tag {
  font-size: 14px;
}

/* 候选卡片 */
.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.candidate-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.candidate-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.candidate-card.selected {
  border-color: #409eff;
  background: #f5f9ff;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.card-rank {
  font-weight: 600;
  color: #409eff;
}
.card-category {
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 2px 8px;
  border-radius: 4px;
}
.card-score {
  margin-left: auto;
  font-weight: 600;
  font-size: 15px;
}
.card-question {
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}
.card-answer {
  color: #606266;
  line-height: 1.7;
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
}
</style>
