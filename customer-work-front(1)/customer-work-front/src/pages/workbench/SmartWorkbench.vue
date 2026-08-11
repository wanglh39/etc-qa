<template>
  <el-card>
    <div class="search-section">
      <el-input
        v-model="searchText"
        placeholder="输入客户问题，如：换手机号收不到验证码怎么办"
        size="large"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button type="primary" :loading="searching" @click="handleSearch">
            搜索
          </el-button>
        </template>
      </el-input>
    </div>

    <div v-if="searched" class="result-section">
      <el-divider />

      <div class="voice-section">
        <div class="voice-label">语音识别结果：</div>
        <div class="voice-text">{{ voiceText || searchText }}</div>
      </div>

      <div class="std-query">
        <span class="label">标准化问题：</span>
        <span>{{ queryResult.standardized_query || queryResult.query }}</span>
      </div>

      <div class="confidence-tag">
        置信度：
        <el-tag :type="confidenceType" size="small">{{ confidenceText }}</el-tag>
      </div>

      <div v-if="queryResult.candidates.length > 0" class="candidate-list">
        <div
          v-for="(item, idx) in queryResult.candidates"
          :key="item.qa_id"
          class="candidate-card"
        >
          <div class="card-header">
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

      <div v-if="queryResult.confidence === 'none'" class="no-match">
        <el-empty description="无匹配结果">
          <el-button type="primary" :loading="agentRunning" @click="runAgentProcess">
            提交 Agent 处理
          </el-button>
        </el-empty>
        <div v-if="agentResult" class="agent-result">
          <el-divider />
          <h4>Agent 处理结果</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="标准化问题">{{ agentResult.question }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ agentResult.category_l1 }}{{ agentResult.category_l2 ? ' / ' + agentResult.category_l2 : '' }}</el-descriptions-item>
            <el-descriptions-item label="分类置信度">{{ (agentResult.category_confidence * 100).toFixed(1) }}%</el-descriptions-item>
            <el-descriptions-item label="是否重复">
              <el-tag :type="agentResult.is_duplicate ? 'warning' : 'success'" size="small">
                {{ agentResult.is_duplicate ? '是 (ID:' + agentResult.duplicate_of + ')' : '否' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="是否需要审核">
              <el-tag :type="agentResult.needs_review ? 'danger' : 'success'" size="small">
                {{ agentResult.needs_review ? '是' : '否' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="反馈部门">{{ agentResult.feedback_dept || '-' }}</el-descriptions-item>
            <el-descriptions-item label="答复内容" :span="2">{{ agentResult.answer || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </div>

    <div v-if="!searched" class="empty-state">
      <el-empty description="输入客户问题，搜索匹配的标准回复话术" />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { queryQA, type QueryResponse } from '@/api/workbench'
import { processAgent, type AgentProcessResponse } from '@/api/audit'

const router = useRouter()
const searchText = ref('')
const voiceText = ref('')
const searching = ref(false)
const searched = ref(false)
const queryResult = ref<QueryResponse>({
  query: '',
  standardized_query: '',
  confidence: '',
  candidates: [],
  total_candidates: 0
})

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

const handleSearch = async () => {
  const q = searchText.value.trim()
  if (!q) {
    ElMessage.warning('请输入问题')
    return
  }
  searching.value = true
  try {
    const res = await queryQA({ question: q })
    queryResult.value = res
    voiceText.value = q
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

const agentRunning = ref(false)
const agentResult = ref<AgentProcessResponse | null>(null)

const runAgentProcess = async () => {
  agentRunning.value = true
  try {
    const res = await processAgent({ question: searchText.value })
    agentResult.value = res
  } catch {
    ElMessage.error('Agent 处理失败')
  } finally {
    agentRunning.value = false
  }
}

const goCrmPage = () => {
  router.push('/crm/create')
}
</script>

<style scoped>
:deep(.el-card__body) {
  padding: 20px;
}

.search-section {
  max-width: 800px;
  margin: 0 auto;
}

.result-section {
  max-width: 900px;
  margin: 0 auto;
}

.voice-section {
  background: #f0f9eb;
  border: 1px solid #b3e19d;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 18px;
}
.voice-label {
  font-size: 13px;
  color: #67C23A;
  margin-bottom: 6px;
}
.voice-text {
  font-size: 15px;
  color: #303133;
  line-height: 1.6;
}

.std-query {
  font-size: 15px;
  margin-bottom: 8px;
}
.std-query .label {
  color: #909399;
}

.confidence-tag {
  margin-bottom: 20px;
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.candidate-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  transition: box-shadow 0.2s;
}
.candidate-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
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
  background: #fafafa;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
}

.no-match {
  margin-top: 20px;
}

.agent-result {
  margin-top: 16px;
}
.agent-result h4 {
  margin-bottom: 12px;
  color: #303133;
}

.empty-state {
  margin-top: 60px;
}
</style>
