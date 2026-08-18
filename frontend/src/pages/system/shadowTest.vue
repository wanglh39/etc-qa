<template>
  <div class="shadow-test-page">
    <div class="page-header-bar">
      <h2>提示词 A/B 影子测试</h2>
      <p class="page-desc">并行运行主版本与候选版本，对比输出差异，零风险验证提示词优化效果</p>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：提示词列表 -->
      <el-col :span="8">
        <el-card>
          <template #header>提示词列表</template>
          <el-table
            :data="promptKeys"
            @row-click="selectPrompt"
            highlight-current-row
            :row-class-name="rowClassName"
            style="width: 100%"
          >
            <el-table-column prop="prompt_key" label="键名" />
            <el-table-column prop="current_version" label="当前版本" width="80" />
            <el-table-column label="影子测试" width="90">
              <template #default="{ row }">
                <el-tag :type="row.shadow_count > 0 ? 'success' : 'info'" size="small">
                  {{ row.shadow_count > 0 ? '运行中' : '未启动' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：详情区 -->
      <el-col :span="16">
        <el-card v-if="selectedKey">
          <template #header>
            <div class="detail-header">
              <span>{{ selectedKey }} - 影子测试管理</span>
              <div class="detail-actions">
                <el-button
                  v-if="!shadowActive"
                  type="primary"
                  size="small"
                  @click="openStartDialog"
                >启动测试</el-button>
                <el-button
                  v-else
                  type="danger"
                  size="small"
                  @click="handleStop"
                >停止测试</el-button>
              </div>
            </div>
          </template>

          <!-- 统计卡片 -->
          <el-row :gutter="12" class="mb-4" v-if="shadowStats">
            <el-col :span="6">
              <div class="stat-mini">
                <span class="stat-value">{{ shadowStats.total_comparisons || 0 }}</span>
                <span class="stat-label">总对比次数</span>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-mini">
                <span class="stat-value">{{ shadowStats.different_count || 0 }}</span>
                <span class="stat-label">输出差异</span>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-mini">
                <span class="stat-value">{{ diffRate }}%</span>
                <span class="stat-label">差异率</span>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-mini">
                <el-tag :type="shadowActive ? 'success' : 'info'" size="small">
                  {{ shadowActive ? '运行中' : '已停止' }}
                </el-tag>
                <span class="stat-label">状态</span>
              </div>
            </el-col>
          </el-row>

          <!-- 对比记录表 -->
          <el-table :data="records" stripe style="width: 100%" v-loading="loadingRecords">
            <el-table-column prop="query" label="查询问题" show-overflow-tooltip />
            <el-table-column label="主版本输出" show-overflow-tooltip>
              <template #default="{ row }">
                <span :class="{ diff: row.main_output !== row.candidate_output }">{{ row.main_output || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="候选版本输出" show-overflow-tooltip>
              <template #default="{ row }">
                <span :class="{ diff: row.main_output !== row.candidate_output }">{{ row.candidate_output || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="是否一致" width="80">
              <template #default="{ row }">
                <el-tag :type="row.main_output === row.candidate_output ? 'success' : 'warning'" size="small">
                  {{ row.main_output === row.candidate_output ? '一致' : '不同' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
        </el-card>

        <el-card v-else>
          <el-empty description="选择左侧提示词查看影子测试详情" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 启动测试弹窗 -->
    <el-dialog v-model="startDialogVisible" title="启动影子测试" width="400px">
      <el-form label-width="100px">
        <el-form-item label="提示词键">
          <el-input :model-value="selectedKey" disabled />
        </el-form-item>
        <el-form-item label="候选版本">
          <el-input-number v-model="candidateVersion" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="starting" @click="handleStart">启动</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listPrompts, startShadowTest, stopShadowTest, getShadowStats, getShadowRecords } from '@/api/system'

const promptKeys = ref<any[]>([])
const selectedKey = ref('')
const shadowActive = ref(false)
const shadowStats = ref<any>(null)
const records = ref<any[]>([])
const loadingRecords = ref(false)
const startDialogVisible = ref(false)
const candidateVersion = ref(1)
const starting = ref(false)

const diffRate = computed(() => {
  if (!shadowStats.value || !shadowStats.value.total_comparisons) return '0'
  return ((shadowStats.value.different_count / shadowStats.value.total_comparisons) * 100).toFixed(1)
})

const loadPrompts = async () => {
  try {
    promptKeys.value = await listPrompts()
  } catch {
    promptKeys.value = []
  }
}

const selectPrompt = async (row: any) => {
  selectedKey.value = row.prompt_key
  shadowActive.value = row.shadow_count > 0
  await Promise.all([loadStats(), loadRecords()])
}

const loadStats = async () => {
  if (!selectedKey.value) return
  try {
    shadowStats.value = await getShadowStats(selectedKey.value)
  } catch {
    shadowStats.value = null
  }
}

const loadRecords = async () => {
  if (!selectedKey.value) return
  loadingRecords.value = true
  try {
    const res = await getShadowRecords({ prompt_key: selectedKey.value, page: 1, page_size: 20 })
    records.value = (res as any).records || (res as any).data || []
  } catch {
    records.value = []
  } finally {
    loadingRecords.value = false
  }
}

const rowClassName = ({ row }: any) => {
  return row.prompt_key === selectedKey.value ? 'current-row' : ''
}

const openStartDialog = () => {
  const current = promptKeys.value.find((p) => p.prompt_key === selectedKey.value)
  candidateVersion.value = (current?.current_version || 1) + 1
  startDialogVisible.value = true
}

const handleStart = async () => {
  starting.value = true
  try {
    await startShadowTest(selectedKey.value, candidateVersion.value)
    ElMessage.success('影子测试已启动')
    startDialogVisible.value = false
    shadowActive.value = true
    await loadPrompts()
  } catch {
    ElMessage.error('启动失败')
  } finally {
    starting.value = false
  }
}

const handleStop = async () => {
  try {
    await ElMessageBox.confirm('确认停止影子测试？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await stopShadowTest(selectedKey.value)
    ElMessage.success('影子测试已停止')
    shadowActive.value = false
    await loadPrompts()
  } catch {
    ElMessage.error('停止失败')
  }
}

onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.shadow-test-page {
  padding: 16px;
}
.page-header-bar {
  margin-bottom: 20px;
}
.page-header-bar h2 {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px;
}
.page-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mb-4 {
  margin-bottom: 16px;
}
.stat-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #409eff;
}
.stat-label {
  font-size: 13px;
  color: #909399;
}
.diff {
  color: #e6a23c;
  font-weight: 500;
}
</style>