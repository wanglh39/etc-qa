<template>
  <div style="padding:16px">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-left">
        <h2 class="welcome-title">{{ greetingText }}，{{ authStore.username || roleText }}</h2>
        <p class="welcome-desc">欢迎使用智能客服话术系统数据看板</p>
      </div>
      <div class="welcome-right">
        <div class="clock-display">{{ currentTime }}</div>
        <div class="date-display">{{ currentDate }}</div>
      </div>
    </div>

    <!-- 时间范围选择器 + 刷新 -->
    <div class="dashboard-header">
      <el-radio-group v-model="days" @change="loadTrend">
        <el-radio-button :value="7">近7天</el-radio-button>
        <el-radio-button :value="30">近30天</el-radio-button>
        <el-radio-button :value="90">近90天</el-radio-button>
      </el-radio-group>
      <el-button type="primary" plain @click="loadAll">刷新</el-button>
    </div>

    <!-- KPI卡片 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="6">
        <StatisticCard
          title="知识库总数"
          :value="stats.qa_total"
          :desc="`本期新增 ${trendSummary.qaNew} 条`"
          :icon="Message"
          icon-color="#0052FF"
          :sparkline="trendData.qa_new_counts"
          :to="currentRole === 'admin' ? '/workbench/admin/knowledge' : undefined"
        />
      </el-col>
      <el-col :span="6">
        <StatisticCard
          title="已激活知识"
          :value="stats.qa_active"
          desc="可用知识条目"
          :icon="Tickets"
          icon-color="#10B981"
          :growth="growthRate(stats.qa_active, stats.qa_active - trendSummary.qaNew)"
          :progress="{ current: stats.qa_active, total: stats.qa_total }"
          :to="currentRole === 'admin' ? '/workbench/admin/knowledge' : undefined"
        />
      </el-col>
      <el-col :span="6">
        <StatisticCard
          title="待审核知识"
          :value="stats.qa_deprecated"
          :desc="stats.qa_deprecated > 10 ? '积压较多，请尽快处理' : '需及时处理'"
          :icon="User"
          icon-color="#F59E0B"
          :alert="stats.qa_deprecated > 10"
          :to="currentRole === 'admin' ? '/workbench/admin/auditList' : undefined"
        />
      </el-col>
      <el-col :span="6">
        <StatisticCard
          title="工单总数"
          :value="stats.work_order_total"
          :desc="`待处理 ${stats.work_order_submitted} 个`"
          :icon="Document"
          icon-color="#EF4444"
          :growth="growthRate(stats.work_order_total, stats.work_order_total - trendSummary.woNew)"
          :sparkline="trendData.work_order_counts"
          :progress="{ current: stats.work_order_processed, total: stats.work_order_total }"
        />
      </el-col>
    </el-row>

    <!-- 趋势图 + 分类占比 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="12">
        <el-card>
          <template #header>每日咨询趋势</template>
          <div ref="lineRef" style="height:300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>问题分类占比</template>
          <div ref="pieRef" style="height:300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分布图 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>工单状态分布</template>
          <div ref="woStatusRef" style="height:280px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>知识库状态分布</template>
          <div ref="qaStatusRef" style="height:280px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { Message, Tickets, User, Document } from '@element-plus/icons-vue'
import StatisticCard from '@/components/StatisticCard.vue'
import { getStats, getStatsTrend, type StatsResponse, type TrendResponse } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const currentRole = authStore.role
const roleText = authStore.roleText
const days = ref(7)

const currentTime = ref('')
const currentDate = ref('')
const greetingText = ref('')
let clockTimer: ReturnType<typeof setInterval> | null = null

const updateClock = () => {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${h}:${m}:${s}`
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  currentDate.value = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${weekdays[now.getDay()]}`
  const hour = now.getHours()
  if (hour < 6) greetingText.value = '凌晨好'
  else if (hour < 9) greetingText.value = '早上好'
  else if (hour < 12) greetingText.value = '上午好'
  else if (hour < 14) greetingText.value = '中午好'
  else if (hour < 18) greetingText.value = '下午好'
  else greetingText.value = '晚上好'
}

const stats = ref<StatsResponse>({
  qa_total: 0,
  qa_active: 0,
  qa_deprecated: 0,
  qa_archived: 0,
  work_order_total: 0,
  work_order_submitted: 0,
  work_order_processed: 0,
  category_stats: {}
})

const trendData = ref<TrendResponse>({ dates: [], work_order_counts: [], qa_new_counts: [] })
const trendSummary = ref({ qaNew: 0, woNew: 0 })

let lineChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
let woStatusChart: echarts.ECharts | null = null
let qaStatusChart: echarts.ECharts | null = null
const lineRef = ref<HTMLDivElement>()
const pieRef = ref<HTMLDivElement>()
const woStatusRef = ref<HTMLDivElement>()
const qaStatusRef = ref<HTMLDivElement>()

const growthRate = (current: number, previous: number): number | undefined => {
  if (previous === 0) return undefined
  return Math.round(((current - previous) / previous) * 100)
}

const renderLine = () => {
  if (!lineRef.value) return
  if (!lineChart) lineChart = echarts.init(lineRef.value)
  const empty = trendData.value.dates.length === 0
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['每日工单量', 'QA新增'] },
    xAxis: { type: 'category', data: trendData.value.dates },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        name: '每日工单量',
        data: trendData.value.work_order_counts,
        smooth: true,
        areaStyle: { opacity: 0.1 },
        itemStyle: { color: '#0052FF' }
      },
      {
        type: 'line',
        name: 'QA新增',
        data: trendData.value.qa_new_counts,
        smooth: true,
        itemStyle: { color: '#67C23A' }
      }
    ],
    noDataLoadingOption: { text: empty ? '暂无数据' : '' }
  })
}

const renderPie = () => {
  if (!pieRef.value) return
  if (!pieChart) pieChart = echarts.init(pieRef.value)
  const pieData = Object.entries(stats.value.category_stats).map(([name, value]) => ({ name, value }))
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll' },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      center: ['50%', '45%'],
      data: pieData.length > 0 ? pieData : [{ name: '暂无数据', value: 1, itemStyle: { color: '#ccc' } }],
      label: { formatter: '{b}\n{d}%' }
    }]
  })
}

const renderWoStatus = () => {
  if (!woStatusRef.value) return
  if (!woStatusChart) woStatusChart = echarts.init(woStatusRef.value)
  const s = stats.value
  const data = [
    { name: '待处理', value: s.work_order_submitted, itemStyle: { color: '#E6A23C' } },
    { name: '已处理', value: s.work_order_processed, itemStyle: { color: '#0052FF' } },
    { name: '其他', value: Math.max(0, s.work_order_total - s.work_order_submitted - s.work_order_processed), itemStyle: { color: '#909399' } }
  ].filter(d => d.value > 0)
  woStatusChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      center: ['50%', '45%'],
      data: data.length > 0 ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#ccc' } }],
      label: { formatter: '{b}\n{d}%' }
    }]
  })
}

const renderQaStatus = () => {
  if (!qaStatusRef.value) return
  if (!qaStatusChart) qaStatusChart = echarts.init(qaStatusRef.value)
  const s = stats.value
  const data = [
    { name: '已激活', value: s.qa_active, itemStyle: { color: '#67C23A' } },
    { name: '待审核', value: s.qa_deprecated, itemStyle: { color: '#E6A23C' } },
    { name: '已归档', value: s.qa_archived, itemStyle: { color: '#909399' } }
  ].filter(d => d.value > 0)
  qaStatusChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      center: ['50%', '45%'],
      data: data.length > 0 ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#ccc' } }],
      label: { formatter: '{b}\n{d}%' }
    }]
  })
}

const loadStats = async () => {
  try {
    const res = await getStats()
    stats.value = res
  } catch {
    // keep defaults
  }
  renderPie()
  renderWoStatus()
  renderQaStatus()
}

const loadTrend = async () => {
  try {
    const res = await getStatsTrend(days.value)
    trendData.value = res
    trendSummary.value = {
      qaNew: res.qa_new_counts.reduce((a, b) => a + b, 0),
      woNew: res.work_order_counts.reduce((a, b) => a + b, 0)
    }
  } catch {
    trendData.value = { dates: [], work_order_counts: [], qa_new_counts: [] }
    trendSummary.value = { qaNew: 0, woNew: 0 }
  }
  renderLine()
}

const loadAll = () => {
  loadStats()
  loadTrend()
}

onMounted(() => {
  loadAll()
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  lineChart?.dispose()
  pieChart?.dispose()
  woStatusChart?.dispose()
  qaStatusChart?.dispose()
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.welcome-banner {
  background: #0F172A;
  border-radius: 12px;
  padding: 28px 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
  border: 1px solid #1E293B;
}
.welcome-banner::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(0, 82, 255, 0.2) 0%, transparent 70%);
  border-radius: 50%;
}
.welcome-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
  z-index: 1;
}
.welcome-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
}
.welcome-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
}
.welcome-right {
  text-align: right;
  position: relative;
  z-index: 1;
}
.clock-display {
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 2px;
}
.date-display {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 4px;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.mb-4 {
  margin-bottom: 16px;
}
</style>
