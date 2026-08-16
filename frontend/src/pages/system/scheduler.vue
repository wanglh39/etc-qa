<template>
  <div class="scheduler-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <h3>定时任务调度</h3>

        <el-card class="status-card" shadow="never">
          <div class="status-row">
            <div class="status-item">
              <span class="label">调度器状态：</span>
              <el-tag :type="status.running ? 'success' : 'danger'" size="large">
                {{ status.running ? '运行中' : '已停止' }}
              </el-tag>
            </div>
            <el-button type="primary" :loading="refreshing" @click="loadStatus">刷新</el-button>
          </div>

          <el-table border :data="status.jobs" style="margin-top: 16px">
            <el-table-column prop="id" label="任务名称" width="200" />
            <el-table-column label="触发器" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.trigger }}
              </template>
            </el-table-column>
            <el-table-column label="下次执行时间" width="200">
              <template #default="{ row }">
                {{ row.next_run_time || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button type="warning" size="small" :loading="triggering === row.id" @click="handleTrigger(row.id)">
                  手动触发
                </el-button>
                <el-button type="primary" size="small" @click="openEditDialog(row.id)" style="margin-left: 8px">
                  修改调度
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <h4 style="margin-top: 24px">执行日志</h4>
        <el-table border :max-height="'calc(100vh - 520px)'" :data="logData">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="task_name" label="任务名称" width="180" />
          <el-table-column label="执行统计" min-width="300" show-overflow-tooltip>
            <template #default="{ row }">
              {{ formatStats(row.stats) }}
            </template>
          </el-table-column>
          <el-table-column label="结果" width="100">
            <template #default="{ row }">
              <el-tag :type="row.result === 'success' ? 'success' : 'danger'">{{ row.result }}</el-tag>
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
      </div>
    </el-card>

    <el-dialog v-model="editDialogVisible" title="修改调度时间" width="420px">
      <el-form label-width="100px">
        <el-form-item label="任务名称">
          <span>{{ editJobId }}</span>
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
    await ElMessageBox.confirm(`确认手动触发任务 "${jobId}"？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  triggering.value = jobId
  try {
    await triggerSchedulerJob(jobId)
    ElMessage.success('任务已触发')
    setTimeout(() => {
      loadStatus()
      loadLogs()
    }, 3000)
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
  } catch {
    return stats
  }
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
})
</script>

<style scoped>
.scheduler-wrap {
  width: 100%;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}
.full-card {
  height: 100%;
}
:deep(.el-card__body) {
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-body-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.status-card {
  margin-bottom: 16px;
}
.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.status-item {
  display: flex;
  align-items: center;
}
.label {
  font-size: 14px;
  margin-right: 8px;
}
</style>
