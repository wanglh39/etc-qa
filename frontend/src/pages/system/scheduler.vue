<template>
  <div class="scheduler-wrap">
    <!-- 调度器状态横幅 -->
    <div class="status-banner" :class="status.running ? 'banner-running' : 'banner-stopped'">
      <div class="banner-left">
        <div class="banner-icon">
          <el-icon :size="28">
            <VideoPlay v-if="status.running" />
            <VideoPause v-else />
          </el-icon>
        </div>
        <div class="banner-info">
          <div class="banner-title">{{ status.running ? '调度器运行中' : '调度器已停止' }}</div>
          <div class="banner-sub">{{ status.jobs.length }} 个任务 · {{ successRate }}% 成功率</div>
        </div>
      </div>
      <el-button type="primary" plain @click="loadStatus" :loading="refreshing">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 任务卡片 -->
    <div class="task-cards" v-if="status.jobs.length > 0">
      <el-card v-for="job in status.jobs" :key="job.id" class="task-card" shadow="hover">
        <div class="task-header">
          <div class="task-name">
            <el-icon><Setting /></el-icon>
            {{ jobDisplayName(job.id) }}
          </div>
          <el-tag :type="status.running ? 'primary' : 'info'" size="small" effect="dark">
            {{ status.running ? '调度中' : '已停止' }}
          </el-tag>
        </div>

        <div class="task-body">
          <div class="task-info-row">
            <span class="ti-label">触发器:</span>
            <span class="ti-value">{{ job.trigger }}</span>
          </div>
          <div class="task-info-row">
            <span class="ti-label">下次执行:</span>
            <span class="ti-value" v-if="job.next_run_time">
              <el-icon><Clock /></el-icon> {{ formatTime(job.next_run_time) }}
              <el-tag size="small" type="info" style="margin-left:8px">{{ countdown(job.next_run_time) }}</el-tag>
            </span>
            <span class="ti-value" v-else>-</span>
          </div>

          <!-- 成功率进度条 -->
          <div class="success-rate" v-if="getTaskStats(job.id)">
            <span class="sr-label">成功率:</span>
            <el-progress
              :percentage="getTaskStats(job.id)?.success_rate ?? 0"
              :color="(getTaskStats(job.id)?.success_rate ?? 0) > 90 ? '#1677FF' : (getTaskStats(job.id)?.success_rate ?? 0) > 70 ? '#475569' : '#64748B'"
              :stroke-width="8"
              style="flex:1; margin: 0 8px"
            />
            <span class="sr-count">{{ getTaskStats(job.id)?.success ?? 0 }}/{{ getTaskStats(job.id)?.total ?? 0 }}</span>
          </div>
        </div>

        <div class="task-actions">
          <el-button type="info" size="small" :loading="triggering === job.id" @click="handleTrigger(job.id)">
            <el-icon><Lightning /></el-icon> 手动触发
          </el-button>
          <el-button type="primary" size="small" @click="openEditDialog(job.id)">
            <el-icon><Edit /></el-icon> 修改调度
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 执行日志 -->
    <el-card class="log-card" shadow="never">
      <template #header>
        <div class="log-header">
          <span class="section-title">执行日志</span>
          <el-button text type="primary" size="small" @click="loadLogs">刷新</el-button>
        </div>
      </template>
      <el-table border :max-height="'calc(100vh - 520px)'" :data="logData">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="任务" width="160">
          <template #default="{ row }">{{ jobDisplayName(row.task_name) }}</template>
        </el-table-column>
        <el-table-column label="执行统计" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">{{ formatStats(row.stats) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'primary' : 'info'" effect="dark">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="执行时间" width="180" />
      </el-table>

      <el-pagination
        v-model:current-page="logPage"
        v-model:page-size="logPageSize"
        :page-sizes="[10, 20, 50]"
        :total="logTotal"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 18px; justify-content: flex-end; display: flex"
        @current-change="loadLogs"
        @size-change="loadLogs"
      />
    </el-card>

    <el-dialog v-model="editDialogVisible" title="修改调度时间" width="420px">
      <el-form label-width="100px">
        <el-form-item label="任务名称">
          <span>{{ jobDisplayName(editJobId) }}</span>
        </el-form-item>
        <el-form-item label="调度单位">
          <el-select v-model="editUnit" style="width: 160px">
            <el-option label="小时" value="hours" />
            <el-option label="分钟" value="minutes" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度间隔">
          <el-input-number v-model="editValue" :min="1" :max="999" style="width: 160px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveSchedule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VideoPlay, VideoPause, Refresh, Setting, Clock, Edit, Lightning
} from '@element-plus/icons-vue'
import {
  getSchedulerStatus,
  triggerSchedulerJob,
  updateSchedulerConfig,
  getSchedulerLogs,
  type SchedulerStatus,
  type SchedulerLogItem
} from '@/api/system'

const status = ref<SchedulerStatus>({ running: false, jobs: [], task_stats: {} })
const refreshing = ref(false)
const triggering = ref('')

const logData = ref<SchedulerLogItem[]>([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = ref(20)

const editDialogVisible = ref(false)
const editJobId = ref('')
const editUnit = ref('hours')
const editValue = ref(1)
const saving = ref(false)

let countdownTimer: ReturnType<typeof setInterval> | null = null
const now = ref(Date.now())

const jobNameMap: Record<string, string> = {
  sync_and_ingest: '工单同步入库',
  cleanup: '过期数据清理',
  alert_check: '告警规则检查'
}

const jobDisplayName = (id: string) => jobNameMap[id] || id

interface TaskStat {
  success: number
  fail: number
  total: number
  success_rate: number
}

const getTaskStats = (jobId: string): TaskStat | null => {
  const raw = status.value.task_stats?.[jobId]
  if (!raw) return null
  const s = typeof raw === 'string' ? JSON.parse(raw) : raw
  const success = s.success || 0
  const fail = s.fail || 0
  const total = success + fail
  if (total === 0) return null
  return { success, fail, total, success_rate: Math.round((success / total) * 100) }
}

const overallStats = computed(() => {
  let success = 0, total = 0
  for (const job of status.value.jobs) {
    const st = getTaskStats(job.id)
    if (st) { success += st.success; total += st.total }
  }
  return { success, total, rate: total > 0 ? Math.round((success / total) * 100) : 100 }
})

const successRate = computed(() => overallStats.value.rate)

const formatTime = (iso: string) => {
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

const countdown = (iso: string) => {
  const target = new Date(iso).getTime()
  const diff = target - now.value
  if (diff <= 0) return '即将执行'
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  if (h > 0) return `${h}时${m}分后`
  if (m > 0) return `${m}分${s}秒后`
  return `${s}秒后`
}

const loadStatus = async () => {
  refreshing.value = true
  try {
    status.value = await getSchedulerStatus()
  } catch {
    ElMessage.error('加载调度器状态失败')
  } finally {
    refreshing.value = false
  }
}

const handleTrigger = async (jobId: string) => {
  try {
    await ElMessageBox.confirm(`确认手动触发任务 "${jobDisplayName(jobId)}"？`, '提示', { type: 'info' })
  } catch { return }
  triggering.value = jobId
  try {
    await triggerSchedulerJob(jobId)
    ElMessage.success('任务已触发')
    setTimeout(() => { loadStatus(); loadLogs() }, 3000)
  } catch {
    ElMessage.error('触发失败')
  } finally {
    triggering.value = ''
  }
}

const openEditDialog = (jobId: string) => {
  editJobId.value = jobId
  editUnit.value = 'hours'
  editValue.value = 1
  editDialogVisible.value = true
}

const handleSaveSchedule = async () => {
  saving.value = true
  try {
    const hours = editUnit.value === 'hours' ? editValue.value : undefined
    const minutes = editUnit.value === 'minutes' ? editValue.value : undefined
    await updateSchedulerConfig(editJobId.value, hours, minutes)
    ElMessage.success('调度时间已更新')
    editDialogVisible.value = false
    loadStatus()
  } catch {
    ElMessage.error('更新失败')
  } finally {
    saving.value = false
  }
}

const formatStats = (stats: string) => {
  try {
    const obj = JSON.parse(stats)
    return JSON.stringify(obj)
  } catch { return stats }
}

const loadLogs = async () => {
  try {
    const res = await getSchedulerLogs({ page: logPage.value, page_size: logPageSize.value })
    logData.value = res.items
    logTotal.value = res.total
  } catch {
    ElMessage.error('加载日志失败')
  }
}

onMounted(() => {
  loadStatus()
  loadLogs()
  countdownTimer = setInterval(() => { now.value = Date.now() }, 1000)
})

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.scheduler-wrap {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #F8FAFC;
}

.status-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-radius: 12px;
  margin-bottom: 20px;
  color: #fff;
  border-color: #CBD5E1 !important;
}
.banner-running { background: #F1F5F9; color: #1677FF; }
.banner-stopped { background: #F1F5F9; color: #1677FF; }

.banner-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.banner-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.banner-title {
  font-size: 20px;
  font-weight: 700;
}
.banner-sub {
  font-size: 13px;
  opacity: 0.85;
  margin-top: 4px;
}

.task-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.task-card {
  transition: transform 0.2s;
}
.task-card:hover {
  border-color: #CBD5E1;
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.task-name {
  font-size: 16px;
  font-weight: 600;
  color: #0F172A;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-body {
  margin-bottom: 12px;
}
.task-info-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}
.ti-label {
  color: #bfbfbf;
  width: 70px;
}
.ti-value {
  color: #0F172A;
  display: flex;
  align-items: center;
  gap: 4px;
}

.success-rate {
  display: flex;
  align-items: center;
  margin-top: 8px;
}
.sr-label {
  font-size: 13px;
  color: #bfbfbf;
}
.sr-count {
  font-size: 12px;
  color: #475569;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.log-card {
  margin-bottom: 20px;
}
.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
}
</style>
