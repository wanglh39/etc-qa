<template>
  <div class="status-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <div class="header-bar">
          <h3>系统状态总览</h3>
          <div class="header-actions">
            <el-button type="primary" plain @click="loadData">刷新</el-button>
            <el-button type="success" plain @click="openLangSmith">LangSmith 追踪</el-button>
          </div>
        </div>

        <div class="overall-bar">
          <el-tag :type="overallTagType" size="large">
            {{ overallText }}
          </el-tag>
          <span class="timestamp" v-if="timestamp">最后检查: {{ timestamp }}</span>
        </div>

        <el-row :gutter="16" class="component-row">
          <el-col v-for="comp in components" :key="comp.name" :span="6">
            <el-card class="comp-card" shadow="hover">
              <div class="comp-header">
                <span class="comp-name">{{ comp.name }}</span>
                <el-tag :type="statusTagType(comp.status)" size="small">
                  {{ statusText(comp.status) }}
                </el-tag>
              </div>
              <div class="comp-detail">{{ comp.detail }}</div>
              <div class="comp-latency" v-if="comp.latency_ms > 0">
                延迟: {{ comp.latency_ms }}ms
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-card class="log-card" shadow="never">
          <template #header>
            <div class="log-header">
              <span>最近错误日志</span>
              <div class="log-actions">
                <el-select v-model="logLevel" placeholder="日志级别" clearable style="width: 120px" @change="loadLogs">
                  <el-option label="ERROR" value="ERROR" />
                  <el-option label="WARNING" value="WARNING" />
                  <el-option label="INFO" value="INFO" />
                </el-select>
                <el-button size="small" style="margin-left: 8px" @click="loadLogs">刷新日志</el-button>
              </div>
            </div>
          </template>
          <div class="log-list">
            <div v-for="(log, i) in logLines" :key="i" class="log-line" :class="'log-' + log.level.toLowerCase()">
              {{ log.line }}
            </div>
            <div v-if="logLines.length === 0" class="log-empty">暂无日志</div>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemStatus, getSystemLogs, type SystemComponent, type SystemLogItem } from '@/api/system'

const components = ref<SystemComponent[]>([])
const overall = ref('')
const timestamp = ref('')
const logLines = ref<SystemLogItem[]>([])
const logLevel = ref('ERROR')

const overallTagType = ref<'success' | 'warning' | 'danger'>('success')
const overallText = ref('')

const statusTagType = (s: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (s === 'healthy') return 'success'
  if (s === 'degraded' || s === 'standby') return 'warning'
  if (s === 'unhealthy') return 'danger'
  return 'info'
}

const statusText = (s: string) => {
  const map: Record<string, string> = {
    healthy: '正常',
    unhealthy: '异常',
    degraded: '降级',
    standby: '待机',
    stopped: '已停止',
    unknown: '未知'
  }
  return map[s] || s
}

const loadData = async () => {
  try {
    const res = await getSystemStatus()
    components.value = res.components
    overall.value = res.overall
    timestamp.value = res.timestamp
    if (res.overall === 'healthy') {
      overallTagType.value = 'success'
      overallText.value = '系统运行正常'
    } else if (res.overall === 'degraded') {
      overallTagType.value = 'warning'
      overallText.value = '系统部分降级'
    } else {
      overallTagType.value = 'danger'
      overallText.value = '系统异常'
    }
  } catch {
    ElMessage.error('加载系统状态失败')
  }
}

const loadLogs = async () => {
  try {
    const res = await getSystemLogs({ lines: 50, level: logLevel.value || undefined })
    logLines.value = res.logs
  } catch {
    ElMessage.error('加载日志失败')
  }
}

const openLangSmith = () => {
  window.open('https://smith.langchain.com', '_blank')
}

onMounted(() => {
  loadData()
  loadLogs()
})
</script>

<style scoped>
.status-wrap {
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
  overflow-y: auto;
}
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.overall-bar {
  margin: 16px 0;
  display: flex;
  align-items: center;
  gap: 16px;
}
.timestamp {
  color: #999;
  font-size: 13px;
}
.component-row {
  margin-bottom: 16px;
}
.comp-card {
  margin-bottom: 12px;
}
.comp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.comp-name {
  font-weight: 600;
  font-size: 15px;
}
.comp-detail {
  color: #666;
  font-size: 13px;
  margin-bottom: 4px;
}
.comp-latency {
  color: #999;
  font-size: 12px;
}
.log-card {
  flex: 1;
  overflow: hidden;
}
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.log-actions {
  display: flex;
  align-items: center;
}
.log-list {
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}
.log-line {
  padding: 2px 4px;
  border-bottom: 1px solid #f0f0f0;
  word-break: break-all;
}
.log-error {
  color: #f56c6c;
  background: #fef0f0;
}
.log-warning {
  color: #e6a23c;
  background: #fdf6ec;
}
.log-info {
  color: #666;
}
.log-empty {
  text-align: center;
  color: #999;
  padding: 20px;
}
</style>