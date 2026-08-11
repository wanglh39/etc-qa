<template>
  <div style="padding:16px">
    <el-row :gutter="16" class="mb-4">
      <el-col :span="6">
        <StatisticCard
          title="知识库总数"
          :value="stats.qa_total"
          desc="已激活"
          :icon="Message"
          icon-color="#409EFF"
        />
      </el-col>
      <el-col :span="6">
        <StatisticCard
          title="已激活知识"
          :value="stats.qa_active"
          desc="可用知识条目"
          :icon="Tickets"
          icon-color="#67C23A"
        />
      </el-col>
      <el-col :span="6">
        <StatisticCard
          title="待审核知识"
          :value="stats.qa_deprecated"
          desc="需及时处理"
          :icon="User"
          icon-color="#E6A23C"
        />
      </el-col>
      <el-col :span="6">
        <StatisticCard
          title="工单总数"
          :value="stats.work_order_total"
          desc="已处理"
          :icon="Document"
          icon-color="#F56C6C"
        />
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card title="每日咨询趋势">
          <div ref="lineRef" style="height:300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card title="问题分类占比">
          <div ref="pieRef" style="height:300px"></div>
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
import { getStats, type StatsResponse } from '@/api/dashboard'

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

let lineChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
const lineRef = ref<HTMLDivElement>()
const pieRef = ref<HTMLDivElement>()

const renderLine = () => {
  lineChart = echarts.init(lineRef.value!)
  // TODO: 后端暂无时间维度统计，暂时保留 mock 趋势数据
  lineChart.setOption({
    xAxis: { type: 'category', data: ['07-05', '07-06', '07-07', '07-08', '07-09', '07-10', '07-11'] },
    yAxis: { type: 'value' },
    series: [{ type: 'line', data: [120, 145, 168, 190, 205, 198, 216], smooth: true }]
  })
}

const renderPie = () => {
  pieChart = echarts.init(pieRef.value!)
  const pieData = Object.entries(stats.value.category_stats).map(([name, value]) => ({ name, value }))
  pieChart.setOption({
    series: [{
      type: 'pie',
      radius: '60%',
      data: pieData.length > 0 ? pieData : [{ name: '暂无数据', value: 1 }]
    }]
  })
}

onMounted(async () => {
  renderLine()
  renderPie()
  try {
    const res = await getStats()
    stats.value = res
    renderPie()
  } catch {
    // 加载失败时保持默认空饼图
  }
})

onUnmounted(() => {
  lineChart?.dispose()
  pieChart?.dispose()
})
</script>
