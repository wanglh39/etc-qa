<template>
  <div class="monitor-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <div class="header-bar">
          <h3>性能监控看板</h3>
          <el-button type="primary" plain @click="loadData">刷新</el-button>
        </div>

        <el-row :gutter="16" class="metric-cards">
          <el-col v-for="m in metricCards" :key="m.name" :span="6">
            <el-card shadow="hover" class="metric-card">
              <div class="metric-name">{{ m.name }}</div>
              <div class="metric-value" :style="{ color: m.color }">{{ m.value }}</div>
              <div class="metric-label">{{ m.label }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" class="chart-row">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>各组件失败率 (%)</template>
              <div ref="failureChartRef" class="chart-box"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>各组件 P95 延迟 (ms)</template>
              <div ref="latencyChartRef" class="chart-box"></div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" class="chart-row">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>调用量分布</template>
              <div ref="distributionChartRef" class="chart-box"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>指标明细</template>
              <el-table :data="metricTable" border size="small" style="width: 100%">
                <el-table-column prop="name" label="指标" width="150" />
                <el-table-column prop="total" label="总调用" width="80" />
                <el-table-column prop="failures" label="失败数" width="80" />
                <el-table-column label="失败率" width="80">
                  <template #default="{ row }">
                    <span :style="{ color: row.failure_rate > 10 ? '#f56c6c' : '#666' }">
                      {{ row.failure_rate.toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="P95延迟" width="90">
                  <template #default="{ row }">
                    {{ row.p95_latency != null ? row.p95_latency.toFixed(0) + 'ms' : '-' }}
                  </template>
                </el-table-column>
                <el-table-column prop="avg_latency" label="平均延迟">
                  <template #default="{ row }">
                    {{ row.avg_latency != null ? row.avg_latency.toFixed(0) + 'ms' : '-' }}
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
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
const metricCards = ref<{ name: string; value: string; label: string; color: string }[]>([])

const metricNameMap: Record<string, string> = {
  rag_query: 'RAG查询',
  milvus_search: 'Milvus搜索',
  llm_call: 'LLM调用',
  mysql_query: 'MySQL查询',
  scheduler_task: '定时任务'
}

const loadData = async () => {
  try {
    const res = await getAlertMetrics()
    const rows: MetricRow[] = []
    let totalCalls = 0
    let totalFailures = 0
    let highFailureRate = 0
    let highLatency = 0

    for (const [key, stats] of Object.entries(res)) {
      const s = stats as any
      const name = metricNameMap[key] || key
      const total = s.total || 0
      const failures = s.failures || 0
      const failureRate = total > 0 ? (failures / total) * 100 : 0
      const row: MetricRow = {
        name,
        total,
        failures,
        failure_rate: failureRate,
        p95_latency: s.p95_latency ?? null,
        avg_latency: s.avg_latency ?? null
      }
      rows.push(row)
      totalCalls += total
      totalFailures += failures
      if (failureRate > 10) highFailureRate++
      if ((s.p95_latency ?? 0) > 3000) highLatency++
    }

    metricTable.value = rows

    metricCards.value = [
      { name: '总调用量', value: String(totalCalls), label: '近10分钟', color: '#409eff' },
      { name: '总失败数', value: String(totalFailures), label: '近10分钟', color: totalFailures > 0 ? '#f56c6c' : '#67c23a' },
      { name: '高失败率组件', value: String(highFailureRate), label: '失败率>10%', color: highFailureRate > 0 ? '#f56c6c' : '#67c23a' },
      { name: '高延迟组件', value: String(highLatency), label: 'P95>3s', color: highLatency > 0 ? '#e6a23c' : '#67c23a' }
    ]

    await nextTick()
    drawCharts(rows)
  } catch {
    ElMessage.error('加载监控数据失败')
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
      series: [{ type: 'bar', data: failureRates, itemStyle: { color: '#f56c6c' } }]
    })
  }

  if (latencyChart) {
    latencyChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: names },
      yAxis: { type: 'value', name: 'ms' },
      series: [{ type: 'bar', data: latencies, itemStyle: { color: '#409eff' } }]
    })
  }

  if (distributionChart) {
    distributionChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: rows.map(r => ({ name: r.name, value: r.total }))
      }]
    })
  }
}

const initCharts = () => {
  if (failureChartRef.value) failureChart = echarts.init(failureChartRef.value)
  if (latencyChartRef.value) latencyChart = echarts.init(latencyChartRef.value)
  if (distributionChartRef.value) distributionChart = echarts.init(distributionChartRef.value)
}

onMounted(() => {
  nextTick(() => {
    initCharts()
    loadData()
  })
})

onBeforeUnmount(() => {
  failureChart?.dispose()
  latencyChart?.dispose()
  distributionChart?.dispose()
})
</script>

<style scoped>
.monitor-wrap {
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
  margin-bottom: 16px;
}
.metric-cards {
  margin-bottom: 16px;
}
.metric-card {
  text-align: center;
  margin-bottom: 12px;
}
.metric-name {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
}
.metric-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
}
.metric-label {
  font-size: 12px;
  color: #ccc;
}
.chart-row {
  margin-bottom: 16px;
}
.chart-box {
  height: 280px;
}
</style>