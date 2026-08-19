<template>
  <div class="monitor-wrap">
    <div class="header-bar">
      <h3>性能监控看板</h3>
      <div class="header-actions">
        <el-radio-group v-model="refreshInterval" size="small" @change="resetTimer">
          <el-radio-button :label="0">关闭</el-radio-button>
          <el-radio-button :label="5">5s</el-radio-button>
          <el-radio-button :label="10">10s</el-radio-button>
          <el-radio-button :label="30">30s</el-radio-button>
        </el-radio-group>
        <el-button type="primary" plain @click="loadData" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 渐变KPI卡片 -->
    <div class="kpi-row">
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677FF">
            <el-icon :size="24"><DataLine /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ totalCalls }}</div>
            <div class="kpi-label">总调用量 (近10分钟)</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677FF">
            <el-icon :size="24"><WarningFilled /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ totalFailures }}</div>
            <div class="kpi-label">总失败数</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677FF">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ highFailureRate }}</div>
            <div class="kpi-label">高失败率组件 (>10%)</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677FF">
            <el-icon :size="24"><Timer /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ highLatency }}</div>
            <div class="kpi-label">高延迟组件 (P95>3s)</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 图表区 -->
    <el-row :gutter="16" class="chart-row" align="stretch">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>各组件失败率 (%)</template>
          <div ref="failureChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>各组件 P95 延迟 (ms)</template>
          <div ref="latencyChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row" align="stretch">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>调用量分布</template>
          <div ref="distributionChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>指标明细</template>
          <el-table :data="metricTable" border size="small" style="width: 100%" :max-height="280">
            <el-table-column prop="name" label="指标" width="120" />
            <el-table-column prop="total" label="总调用" width="80" align="center" />
            <el-table-column prop="failures" label="失败数" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.failures > 0 ? '#64748B' : '#bfbfbf' }">{{ row.failures }}</span>
              </template>
            </el-table-column>
            <el-table-column label="失败率" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.failure_rate > 10 ? '#64748B' : row.failure_rate > 0 ? '#475569' : '#1677FF' }">
                  {{ row.failure_rate.toFixed(1) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="P95延迟" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.p95_latency > 3000 ? '#64748B' : '#475569' }">
                  {{ row.p95_latency != null ? row.p95_latency.toFixed(0) + 'ms' : '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="平均延迟" align="center">
              <template #default="{ row }">
                {{ row.avg_latency != null ? row.avg_latency.toFixed(0) + 'ms' : '-' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, DataLine, WarningFilled, TrendCharts, Timer } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getAlertMetrics } from '@/api/system'

const failureChartRef = ref<HTMLElement>()
const latencyChartRef = ref<HTMLElement>()
const distributionChartRef = ref<HTMLElement>()
let failureChart: echarts.ECharts | null = null
let latencyChart: echarts.ECharts | null = null
let distributionChart: echarts.ECharts | null = null

interface MetricRow {
  name: string
  total: number
  failures: number
  failure_rate: number
  p95_latency: number | null
  avg_latency: number | null
}

const metricTable = ref<MetricRow[]>([])
const totalCalls = ref(0)
const totalFailures = ref(0)
const highFailureRate = ref(0)
const highLatency = ref(0)
const loading = ref(false)
const refreshInterval = ref(10)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const metricNameMap: Record<string, string> = {
  rag_query: 'RAG查询',
  milvus_search: 'Milvus搜索',
  llm_call: 'LLM调用',
  mysql_query: 'MySQL查询',
  scheduler_task: '定时任务'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertMetrics()
    const rows: MetricRow[] = []
    let tc = 0, tf = 0, hf = 0, hl = 0

    for (const [key, stats] of Object.entries(res)) {
      const s = stats as any
      const name = metricNameMap[key] || key
      const total = s.total || 0
      const failures = s.failures || 0
      const failureRate = total > 0 ? (failures / total) * 100 : 0
      rows.push({
        name, total, failures, failure_rate: failureRate,
        p95_latency: s.p95_latency ?? null, avg_latency: s.avg_latency ?? null
      })
      tc += total
      tf += failures
      if (failureRate > 10) hf++
      if ((s.p95_latency ?? 0) > 3000) hl++
    }

    metricTable.value = rows
    totalCalls.value = tc
    totalFailures.value = tf
    highFailureRate.value = hf
    highLatency.value = hl

    await nextTick()
    drawCharts(rows)
  } catch {
    ElMessage.error('加载监控数据失败')
  } finally {
    loading.value = false
  }
}

const drawCharts = (rows: MetricRow[]) => {
  const names = rows.map(r => r.name)
  const failureRates = rows.map(r => Number(r.failure_rate.toFixed(1)))
  const latencies = rows.map(r => r.p95_latency != null ? Math.round(r.p95_latency) : 0)
  const totals = rows.map(r => r.total)

  if (failureChart) {
    failureChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: names },
      yAxis: { type: 'value', name: '%' },
      series: [{
        type: 'bar', data: failureRates,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#64748B' }, { offset: 1, color: '#91CAFF' }
          ])
        },
        markLine: { data: [{ yAxis: 10, name: '阈值' }], lineStyle: { color: '#64748B', type: 'dashed' } }
      }]
    })
  }

  if (latencyChart) {
    latencyChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: names },
      yAxis: { type: 'value', name: 'ms' },
      series: [{
        type: 'bar', data: latencies,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#1677FF' }, { offset: 1, color: '#91CAFF' }
          ])
        },
        markLine: { data: [{ yAxis: 3000, name: '阈值' }], lineStyle: { color: '#4096FF', type: 'dashed' } }
      }]
    })
  }

  if (distributionChart) {
    const distPalette = ['#1677FF', '#4096FF', '#69B1FF', '#91CAFF', '#BAE0FF', '#64748B']
    distributionChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        data: rows.map((r, i) => ({ name: r.name, value: r.total, itemStyle: { color: distPalette[i % distPalette.length] } }))
      }]
    })
  }
}

const initCharts = () => {
  if (failureChartRef.value) failureChart = echarts.init(failureChartRef.value)
  if (latencyChartRef.value) latencyChart = echarts.init(latencyChartRef.value)
  if (distributionChartRef.value) distributionChart = echarts.init(distributionChartRef.value)
}

const resetTimer = () => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (refreshInterval.value > 0) {
    refreshTimer = setInterval(loadData, refreshInterval.value * 1000)
  }
}

onMounted(() => {
  nextTick(() => {
    initCharts()
    loadData()
    resetTimer()
  })
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  failureChart?.dispose()
  latencyChart?.dispose()
  distributionChart?.dispose()
})
</script>

<style scoped>
.monitor-wrap {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #F8FAFC;
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.kpi-card { transition: transform 0.2s; height: 100%; }
.kpi-card:hover { border-color: #CBD5E1 !important; }
.kpi-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.kpi-num {
  font-size: 24px;
  font-weight: 700;
  color: #0F172A;
  line-height: 1.2;
}
.kpi-label {
  font-size: 13px;
  color: #bfbfbf;
  margin-top: 6px;
}

.chart-row {
  margin-bottom: 16px;
}
.chart-card {
  height: 100%;
}
.chart-box {
  height: 280px;
}
</style>
