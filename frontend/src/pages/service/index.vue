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
          <el-collapse-item
            v-for="group in quickReplyGroups"
            :key="group.title"
            :title="group.title"
            :name="group.title"
          >
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
          ref="categoryTreeRef"
          :data="categoryTree"
          :props="{ label: 'label', children: 'children' }"
          :filter-node-method="filterCategoryNode"
          node-key="label"
          highlight-current
          style="background: transparent"
          @node-click="onCategoryClick"
        />
        <el-button
          v-if="selectedCategory"
          size="small"
          text
          type="primary"
          style="margin-top: 8px"
          @click="clearCategoryFilter"
        >
          清除分类筛选
        </el-button>
      </div>
    </div>

    <!-- 主区：工作台 -->
    <div class="main-area">
      <el-card>
        <!-- 搜索区 -->
        <div class="search-section">
          <div class="search-header">
            <div class="search-title-row">
              <span class="search-title">客服工作台</span>
              <el-tag
                v-if="asrHealth"
                :type="asrHealth.loaded ? 'primary' : 'info'"
                size="small"
                effect="plain"
                round
              >
                <el-icon style="margin-right: 2px">
                  <CircleCheck />
                </el-icon>
                ASR {{ asrHealth.loaded ? '已就绪' : '待加载' }}
              </el-tag>
            </div>
          </div>
          <el-input
            v-model="searchText"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入或粘贴客户问题（Enter搜索，对话记录请先总结为标准问题）"
            @keydown.enter.exact.prevent="handleSearch"
          />
          <div class="button-row">
            <div v-if="recordingState === 'recording'" class="recording-pulse-wrapper">
              <el-button
                :icon="VideoPause"
                circle
                size="large"
                type="info"
                title="暂停录音"
                @click="pauseRecording"
              />
              <span class="pulse-ring" />
            </div>
            <el-button
              v-if="recordingState === 'idle'"
              :icon="Microphone"
              circle
              size="large"
              title="开始录音"
              @click="startRecordingSession"
            />
            <el-button
              v-if="recordingState === 'paused'"
              :icon="VideoPlay"
              circle
              size="large"
              type="primary"
              title="继续录音"
              @click="resumeRecording"
            />
            <el-button
              v-if="recordingState !== 'idle'"
              :icon="VideoPause"
              circle
              size="large"
              type="primary"
              title="停止录音"
              @click="stopRecordingSession"
            />
            <el-button type="primary" size="large" @click="openCreateDialog"> 创建工单 </el-button>
            <el-button type="primary" size="large" :loading="searching" @click="handleSearch">
              搜索
            </el-button>
            <el-button size="large" :disabled="recordingState !== 'idle'" @click="clearAll">
              清空
            </el-button>
          </div>
          <div v-if="searchHistory.length" class="search-history">
            <span class="history-label">最近搜索：</span>
            <el-tag
              v-for="(q, i) in searchHistory"
              :key="i"
              size="small"
              class="history-tag"
              @click="searchFromHistory(q)"
            >
              {{ q.length > 12 ? q.slice(0, 12) + '…' : q }}
            </el-tag>
          </div>
          <div v-if="selectedCategory" class="category-hint">
            <el-tag type="info" closable @close="clearCategoryFilter">
              分类筛选: {{ selectedCategory }}
            </el-tag>
          </div>
        </div>

        <!-- 实时识别区 -->
        <div v-if="recordingState !== 'idle' || asr.fullText.value" class="asr-section">
          <div class="asr-header">
            <span class="asr-title">
              <el-tag
                v-if="recordingState === 'recording'"
                type="primary"
                size="small"
                effect="dark"
                >录音中</el-tag
              >
              <el-tag v-else-if="recordingState === 'paused'" type="info" size="small" effect="dark"
                >已暂停</el-tag
              >
              实时语音识别
            </span>
            <el-tag size="small" type="info">
              {{ asr.asrState.value }}
            </el-tag>
          </div>
          <div class="asr-text">
            <span class="asr-full">{{ asr.fullText.value }}</span>
            <span class="asr-partial">{{ asr.partialText.value }}</span>
          </div>
          <div v-if="asr.errorMsg.value" class="asr-error">
            {{ asr.errorMsg.value }}
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!searched && !finalReply" class="empty-state">
          <el-empty description="输入客户问题搜索匹配话术，也可直接点击左侧快捷话术" />
        </div>

        <!-- 结果区 -->
        <div v-if="searched || finalReply" class="result-section">
          <!-- 最终回复区 -->
          <div class="reply-area">
            <div class="reply-header">
              <span class="reply-title">最终答复</span>
              <el-button
                v-if="finalReply"
                size="small"
                type="primary"
                plain
                @click="copyToClipboard(finalReply)"
              >
                <el-icon style="margin-right: 4px">
                  <CopyDocument />
                </el-icon>
                复制答复
              </el-button>
            </div>
            <el-input
              v-model="finalReply"
              type="textarea"
              :rows="5"
              placeholder="勾选候选答案自动填充，也可点左侧快捷话术插入，可自行修改"
            />
          </div>

          <!-- 无匹配结果提示 -->
          <el-empty
            v-if="searched && !hasCandidates"
            description="未检索到匹配结果，可创建工单流转到对应部门处理"
            :image-size="80"
          />

          <!-- 检索信息 -->
          <div v-if="hasCandidates" class="meta-row">
            <div class="std-query">
              <span class="label">标准化问题：</span>
              <span>{{ queryResult.standardized_query || queryResult.query }}</span>
            </div>
            <div class="confidence-tag">
              置信度：
              <el-tag :type="confidenceType" size="small">
                {{ confidenceText }}
              </el-tag>
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
                <span v-if="item.category_l1" class="card-category">
                  {{ item.category_l1 }}{{ item.category_l2 ? ' / ' + item.category_l2 : '' }}
                </span>
                <div class="card-score-bar">
                  <div class="score-track">
                    <div
                      class="score-fill"
                      :style="{ width: item.score * 100 + '%', background: scoreColor(item.score) }"
                    />
                  </div>
                  <span class="score-value" :style="{ color: scoreColor(item.score) }">
                    {{ (item.score * 100).toFixed(1) }}%
                  </span>
                </div>
              </div>
              <div class="card-question">
                {{ item.question }}
              </div>
              <div class="card-answer">
                {{ item.answer }}
              </div>
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
        <el-select
          v-model="workForm.next_dept"
          placeholder="选择需要处理的部门"
          style="width: 100%"
        >
          <el-option label="售后处理部" value="aftersale" />
          <el-option label="技术运维部" value="ops" />
          <el-option label="财务部" value="finance" />
          <el-option label="市场部" value="market" />
          <el-option label="人事部" value="human" />
        </el-select>
      </el-form-item>
      <el-form-item label="工单优先级" prop="priority">
        <el-radio-group v-model="workForm.priority">
          <el-radio value="low"> 低 </el-radio>
          <el-radio value="mid"> 中等 </el-radio>
          <el-radio value="high"> 紧急 </el-radio>
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
      <el-button @click="dialogVisible = false"> 取消 </el-button>
      <el-button type="primary" :loading="submitting" @click="submitWorkOrder">
        提交工单 (Ctrl+Enter)
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Microphone,
  CopyDocument,
  ChatDotRound,
  Files,
  VideoPause,
  VideoPlay,
  CircleCheck,
} from '@element-plus/icons-vue'
import { queryQA, getAsrHealth, type QueryResponse, type CandidateResult } from '@/api/workbench'
import { createWorkOrder } from '@/api/workorder'
import { getCategories } from '@/api/knowledge'
import { useStreamingASR } from '@/composables/useStreamingASR'
import { copyText } from '@/utils/common'

// ===== 快捷话术模板 =====
const quickReplyGroups = [
  {
    title: '感谢语',
    items: [
      '感谢您的来电，请问还有其他可以帮到您的吗？',
      '感谢您的耐心等待，给您带来不便敬请谅解',
      '感谢您的配合，祝您生活愉快',
    ],
  },
  {
    title: '安抚语',
    items: [
      '非常抱歉给您带来不便，我马上为您处理',
      '请您不要着急，我帮您核实一下具体情况',
      '理解您的心情，我们会尽快为您解决此问题',
    ],
  },
  {
    title: '引导语',
    items: [
      '请问您方便提供一下订单号吗？',
      '请您详细描述一下遇到的问题，我好为您查询',
      '建议您先尝试重新登录，看问题是否解决',
    ],
  },
  {
    title: '结束语',
    items: [
      '如有其他问题随时欢迎致电，感谢您的来电',
      '已为您记录问题，后续有进展会第一时间通知您',
      '请您保持手机畅通，工作人员会尽快联系您',
    ],
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
    categoryTree.value =
      tree.length > 0 ? tree : cats.map((c: any) => ({ label: c.label || c.name || String(c) }))
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
  const ok = await copyText(text)
  if (ok) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

// ===== ASR文本清洗 =====
const FILLER_WORDS = [
  '嗯',
  '啊',
  '哦',
  '噢',
  '唉',
  '诶',
  '呃',
  '额',
  '哈',
  '嘿',
  '那个',
  '这个',
  '然后',
  '就是',
  '就是说',
  '那么',
  '对吧',
  '你知道吗',
  '怎么说呢',
  '事实上',
  '其实',
]

const cleanAsrText = (text: string): string => {
  let result = text
  for (const word of FILLER_WORDS) {
    result = result.replace(new RegExp(word, 'g'), '')
  }
  result = result.replace(/[。]{2,}/g, '。')
  result = result.replace(/[，]{2,}/g, '，')
  result = result.replace(/[！]{2,}/g, '！')
  result = result.replace(/[？]{2,}/g, '？')
  result = result.replace(/[、]{2,}/g, '、')
  result = result.replace(/\s+/g, ' ')
  result = result.replace(/^[\s。，、！？]+/g, '')
  result = result.replace(/[\s。，、！？]+$/g, '')
  return result
}

const isMeaningfulQuery = (text: string): boolean => {
  const cleaned = cleanAsrText(text)
  if (cleaned.length < 4) return false
  const contentOnly = cleaned.replace(/[\s。，、！？.,!?]/g, '')
  if (contentOnly.length < 3) return false
  if (/^\d+$/.test(contentOnly)) return false
  return true
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
  total_candidates: 0,
})
const hasCandidates = computed(() => queryResult.value.candidates.length > 0)

// ===== 置信度 =====
const confidenceType = ref<'primary' | 'info'>('info')
const confidenceText = ref('')
const confidenceMap: Record<string, { type: 'primary' | 'info'; text: string }> = {
  high: { type: 'primary', text: '高' },
  mid: { type: 'info', text: '中' },
  low: { type: 'info', text: '低' },
  none: { type: 'info', text: '无匹配' },
}

const scoreColor = (score: number) => {
  if (score >= 0.8) return '#1677FF'
  if (score >= 0.6) return '#475569'
  return '#64748B'
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
const recordingState = ref<'idle' | 'recording' | 'paused'>('idle')
const consumedTextLength = ref(0)

const clearAll = () => {
  searchText.value = ''
  searched.value = false
  selectedIds.value = []
  finalReply.value = ''
  queryResult.value = {
    query: '',
    standardized_query: '',
    confidence: '',
    candidates: [],
    total_candidates: 0,
  }
  confidenceType.value = 'info'
  confidenceText.value = ''
  asr.fullText.value = ''
  asr.partialText.value = ''
  asr.queryResult.value = null
  asr.errorMsg.value = ''
  consumedTextLength.value = 0
  asr.reset()
}

const handleRecordingError = (e: any) => {
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

const startRecordingSession = async () => {
  clearAll()
  try {
    await asr.startRecording()
    recordingState.value = 'recording'
  } catch (e: any) {
    handleRecordingError(e)
  }
}

const pauseRecording = () => {
  asr.stopRecording()
  const full = asr.fullText.value
  const newText = full.slice(consumedTextLength.value)
  if (newText.trim()) {
    searchText.value = cleanAsrText(newText)
  }
  consumedTextLength.value = full.length
  recordingState.value = 'paused'
}

const resumeRecording = async () => {
  try {
    await asr.startRecording()
    recordingState.value = 'recording'
  } catch (e: any) {
    handleRecordingError(e)
  }
}

const stopRecordingSession = () => {
  asr.stopRecording()
  asr.disconnect()
  const full = asr.fullText.value
  const newText = full.slice(consumedTextLength.value)
  if (newText.trim()) {
    searchText.value = cleanAsrText(newText)
  }
  consumedTextLength.value = 0
  recordingState.value = 'idle'
}

// ===== 搜索 =====
const handleSearch = async () => {
  const raw = searchText.value.trim()
  if (!raw) {
    ElMessage.warning('请输入问题')
    return
  }
  const q = cleanAsrText(raw)
  if (!isMeaningfulQuery(raw)) {
    ElMessage.warning('问题文本过短或无意义，请编辑后重试')
    return
  }
  searching.value = true
  try {
    const res = await queryQA({
      question: q,
      category_l1: selectedCategory.value || undefined,
    } as any)
    queryResult.value = res
    selectedIds.value = []
    finalReply.value = ''
    const info = confidenceMap[res.confidence] || confidenceMap.none
    confidenceType.value = info.type
    confidenceText.value = info.text
    searched.value = true
    addSearchHistory(q)
  } catch {
    ElMessage.error('查询失败')
  } finally {
    searching.value = false
  }
}

const searchFromHistory = (q: string) => {
  searchText.value = q
  handleSearch()
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
  detail_desc: '',
})

const workRules: FormRules = {
  service_id: [{ required: true, message: '请填写发起客服ID', trigger: 'blur' }],
  customer_name: [{ required: true, message: '客户名称不能为空', trigger: 'blur' }],
  phone: [
    { required: true, message: '手机号必填', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式有误', trigger: 'blur' },
  ],
  problem_type: [{ required: true, message: '需要选择问题分类', trigger: 'change' }],
  next_dept: [{ required: true, message: '请选择转交处理部门', trigger: 'change' }],
  detail_desc: [{ required: true, message: '填写客户问题详情', trigger: 'blur' }],
}

const openCreateDialog = () => {
  const full = asr.fullText.value
  workForm.value.detail_desc = full ? cleanAsrText(full) : cleanAsrText(searchText.value)
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
      detail_desc: workForm.value.detail_desc,
    })
    ElMessage.success('工单已提交，转交对应业务部门处理')
    dialogVisible.value = false
  } catch {
    ElMessage.error('工单提交失败')
  } finally {
    submitting.value = false
  }
}

const asrHealth = ref<{ loaded: boolean; model?: string; device?: string } | null>(null)
const searchHistory = ref<string[]>([])

const checkAsrHealth = async () => {
  try {
    asrHealth.value = await getAsrHealth()
  } catch {
    asrHealth.value = null
  }
}

const addSearchHistory = (q: string) => {
  const trimmed = q.trim()
  if (!trimmed) return
  searchHistory.value = [trimmed, ...searchHistory.value.filter((h) => h !== trimmed)].slice(0, 6)
}

onMounted(() => {
  loadCategories()
  checkAsrHealth()
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
  border: 1px solid #e2e8f0;
}
.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.reply-item {
  padding: 6px 8px;
  font-size: 13px;
  color: #475569;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.5;
}
.reply-item:hover {
  background: #e6f4ff;
  color: #1677ff;
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
.search-header {
  margin-bottom: 16px;
}
.search-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.search-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}
.button-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: flex-end;
  margin-top: 16px;
}
.recording-pulse-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.pulse-ring {
  position: absolute;
  width: 48px;
  height: 48px;
  border: 3px solid #475569;
  border-radius: 50%;
  animation: pulse-ring 1.5s ease-out infinite;
  pointer-events: none;
}
@keyframes pulse-ring {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.8);
    opacity: 0;
  }
}
.search-history {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.history-label {
  font-size: 13px;
  color: #bfbfbf;
}
.history-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.history-tag:hover {
  border-color: #cbd5e1;
}
.category-hint {
  margin-top: 8px;
}

/* 实时识别区 */
.asr-section {
  max-width: 900px;
  margin: 16px auto 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
}
.asr-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.asr-title {
  font-weight: 600;
  color: #0f172a;
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
  color: #0f172a;
}
.asr-partial {
  color: #bfbfbf;
  font-style: italic;
}
.asr-error {
  color: #64748b;
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
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
}
.reply-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.reply-title {
  font-weight: 600;
  color: #0f172a;
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
  color: #bfbfbf;
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
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.candidate-card:hover {
  border-color: #cbd5e1;
}
.candidate-card.selected {
  border-color: #1677ff;
  background: #f8fafc;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.card-rank {
  font-weight: 600;
  color: #1677ff;
}
.card-category {
  font-size: 12px;
  color: #bfbfbf;
  background: #f8fafc;
  padding: 2px 8px;
  border-radius: 4px;
}
.card-score-bar {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}
.score-track {
  flex: 1;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}
.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.score-value {
  font-weight: 600;
  font-size: 14px;
  min-width: 48px;
  text-align: right;
}
.card-question {
  font-weight: 500;
  color: #0f172a;
  margin-bottom: 8px;
}
.card-answer {
  color: #475569;
  line-height: 1.7;
  background: #fff;
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  border: 1px solid #f1f5f9;
}
</style>
