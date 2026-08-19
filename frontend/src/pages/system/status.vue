<template>
  <div class="status-wrap">
    <!-- 健康摘要横幅 -->
    <div class="health-banner" :class="overallClass">
      <div class="banner-left">
        <div class="banner-icon">
          <el-icon :size="32">
            <CircleCheck v-if="overall === 'healthy'" />
            <Warning v-else-if="overall === 'degraded'" />
            <CircleClose v-else />
          </el-icon>
        </div>
        <div class="banner-info">
          <div class="banner-title">{{ overallText }}</div>
          <div class="banner-sub" v-if="timestamp">最后检查: {{ timestamp }}</div>
        </div>
      </div>
      <div class="banner-right">
        <div class="healthy-count">
          <span class="hc-num">{{ healthyCount }}</span>
          <span class="hc-label">/ {{ components.length }} 正常</span>
        </div>
        <el-button type="primary" plain @click="loadData" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button type="primary" plain @click="openLangSmith">
          <el-icon><Link /></el-icon> LangSmith
        </el-button>
      </div>
    </div>

    <!-- 组件状态卡片 -->
    <el-row :gutter="16" class="component-row">
      <el-col v-for="comp in components" :key="comp.name" :span="6">
        <el-card class="comp-card" shadow="hover" :class="compCardClass(comp.status)">
          <div class="comp-header">
            <div class="comp-icon-wrap" :class="compCardClass(comp.status)">
              <el-icon :size="20">
                <Cpu v-if="comp.name.includes('API') || comp.name.includes('RAG')" />
                <Coin v-else-if="comp.name.includes('MySQL')" />
                <Box v-else-if="comp.name.includes('Milvus')" />
                <Microphone v-else-if="comp.name.includes('ASR')" />
                <Timer v-else-if="comp.name.includes('定时') || comp.name.includes('调度')" />
                <Bell v-else-if="comp.name.includes('告警')" />
                <Monitor v-else />
              </el-icon>
              <span class="pulse-ring" v-if="comp.status === 'healthy'"></span>
            </div>
            <div class="comp-info">
              <div class="comp-name">{{ comp.name }}</div>
              <el-tag :type="statusTagType(comp.status)" size="small" effect="dark">
                {{ statusText(comp.status) }}
              </el-tag>
            </div>
          </div>
          <div class="comp-detail">{{ comp.detail }}</div>
          <div class="comp-latency" v-if="comp.latency_ms > 0">
            <el-icon><Stopwatch /></el-icon> {{ comp.latency_ms }}ms
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 终端风格日志 -->
    <el-card class="log-card" shadow="never">
      <template #header>
        <div class="log-header">
          <div class="log-title">
            <el-icon><Document /></el-icon>
            <span>系统日志</span>
            <span class="log-count" v-if="logLines.length">({{ logLines.length }}条)</span>
          </div>
          <div class="log-actions">
            <el-select v-model="logLevel" placeholder="日志级别" clearable style="width: 120px" @change="loadLogs">
              <el-option label="ERROR" value="ERROR" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="INFO" value="INFO" />
            </el-select>
            <el-button size="small" @click="loadLogs">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
      </template>
      <div class="terminal">
        <div v-for="(log, i) in logLines" :key="i" class="terminal-line" :class="'term-' + log.level.toLowerCase()">
          <span class="term-prompt">$</span> {{ log.line }}
        </div>
        <div v-if="logLines.length === 0" class="terminal-empty">~ 暂无日志 ~</div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck, CircleClose, Warning, Refresh, Link, Document,
  Cpu, Coin, Box, Microphone, Timer, Bell, Monitor, Stopwatch
} from '@element-plus/icons-vue'
import { getSystemStatus, getSystemLogs, type SystemComponent, type SystemLogItem } from '@/api/system'

const components = ref<SystemComponent[]>([])
const overall = ref('')
const timestamp = ref('')
const logLines = ref<SystemLogItem[]>([])
const logLevel = ref('ERROR')
const loading = ref(false)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const healthyCount = computed(() => components.value.filter(c => c.status === 'healthy').length)

const overallClass = computed(() => {
  if (overall.value === 'healthy') return 'banner-healthy'
  if (overall.value === 'degraded') return 'banner-degraded'
  return 'banner-unhealthy'
})

const overallText = computed(() => {
  if (overall.value === 'healthy') return '系统运行正常'
  if (overall.value === 'degraded') return '系统部分降级'
  return '系统异常'
})

const statusTagType = (s: string): 'primary' | 'info' => {
  if (s === 'healthy') return 'primary'
  if (s === 'degraded' || s === 'standby') return 'info'
  if (s === 'unhealthy') return 'info'
  return 'info'
}

const statusText = (s: string) => {
  const map: Record<string, string> = {
    healthy: '正常', unhealthy: '异常', degraded: '降级',
    standby: '待加载', stopped: '已停止', unknown: '未知'
  }
  return map[s] || s
}

const compCardClass = (s: string) => {
  if (s === 'healthy') return 'comp-healthy'
  if (s === 'unhealthy') return 'comp-unhealthy'
  if (s === 'degraded' || s === 'standby') return 'comp-degraded'
  return 'comp-unknown'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getSystemStatus()
    components.value = res.components
    overall.value = res.overall
    timestamp.value = res.timestamp
  } catch {
    ElMessage.error('加载系统状态失败')
  } finally {
    loading.value = false
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
  refreshTimer = setInterval(() => {
    loadData()
  }, 10000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.status-wrap {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #F8FAFC;
}

.health-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-radius: 12px;
  margin-bottom: 20px;
  color: #fff;
  border-color: #CBD5E1 !important;
}
.banner-healthy { background: #F1F5F9; color: #1677FF; }
.banner-degraded { background: #F1F5F9; color: #1677FF; }
.banner-unhealthy { background: #F1F5F9; color: #1677FF; }

.banner-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.banner-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.banner-title {
  font-size: 22px;
  font-weight: 700;
}
.banner-sub {
  font-size: 13px;
  opacity: 0.85;
  margin-top: 4px;
}

.banner-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.healthy-count {
  text-align: center;
}
.hc-num {
  font-size: 28px;
  font-weight: 700;
}
.hc-label {
  font-size: 12px;
  opacity: 0.85;
  display: block;
}

.component-row {
  margin-bottom: 20px;
}

.comp-card {
  margin-bottom: 12px;
  transition: transform 0.2s;
}
.comp-card:hover {
  border-color: #CBD5E1;
}
.comp-healthy { border-left: 3px solid #1677FF; }
.comp-unhealthy { border-left: 3px solid #64748B; }
.comp-degraded { border-left: 3px solid #475569; }
.comp-unknown { border-left: 3px solid #bfbfbf; }

.comp-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.comp-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.comp-icon-wrap.comp-healthy { background: #E6F4FF; color: #1677FF; }
.comp-icon-wrap.comp-unhealthy { background: #F1F5F9; color: #64748B; }
.comp-icon-wrap.comp-degraded { background: #F1F5F9; color: #475569; }
.comp-icon-wrap.comp-unknown { background: #F8FAFC; color: #bfbfbf; }

.pulse-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  border: 2px solid #1677FF;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.3); opacity: 0; }
}

.comp-info {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.comp-name {
  font-weight: 600;
  font-size: 15px;
  color: #0F172A;
}
.comp-detail {
  color: #475569;
  font-size: 13px;
  margin-bottom: 4px;
  line-height: 1.5;
}
.comp-latency {
  color: #bfbfbf;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.log-card {
  margin-bottom: 20px;
}
.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.log-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}
.log-count {
  color: #bfbfbf;
  font-size: 13px;
  font-weight: 400;
}
.log-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  padding: 12px 16px;
  max-height: 350px;
  overflow-y: auto;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.8;
}
.terminal-line {
  color: #475569;
  word-break: break-all;
}
.term-prompt {
  color: #94A3B8;
  margin-right: 4px;
}
.term-error { color: #475569; }
.term-warning { color: #475569; }
.term-info { color: #475569; }
.terminal-empty {
  color: #94A3B8;
  text-align: center;
  padding: 20px;
}
</style>
