<template>
  <div class="alert-wrap">
    <!-- 概览卡片 -->
    <div class="kpi-row">
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677ff">
            <el-icon :size="24"><BellFilled /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ severityCounts.P0 || 0 }}</div>
            <div class="kpi-label">P0 紧急</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677ff">
            <el-icon :size="24"><WarningFilled /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ severityCounts.P1 || 0 }}</div>
            <div class="kpi-label">P1 严重</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" style="background: #1677ff">
            <el-icon :size="24"><InfoFilled /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ severityCounts.P2 || 0 }}</div>
            <div class="kpi-label">P2 提醒</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon" :style="{ background: unackedCount > 0 ? '#1677FF' : '#1677FF' }">
            <el-icon :size="24"
              ><CircleCheck v-if="unackedCount === 0" /><Warning v-else
            /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ unackedCount }}</div>
            <div class="kpi-label">未确认</div>
          </div>
        </div>
      </el-card>
    </div>

    <el-card class="full-card">
      <div class="card-body-inner">
        <div class="header-bar">
          <h3>异常告警</h3>
          <div class="header-actions">
            <el-button
              v-if="selectedIds.length > 0"
              type="primary"
              size="small"
              :loading="batchLoading"
              @click="batchAck"
            >
              批量确认 ({{ selectedIds.length }})
            </el-button>
            <el-button type="primary" plain @click="loadData" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>

        <div class="filter-bar">
          <el-select
            v-model="filterStatus"
            placeholder="状态筛选"
            clearable
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option label="未确认" value="open" />
            <el-option label="已确认" value="acked" />
          </el-select>
          <el-select
            v-model="filterSeverity"
            placeholder="级别筛选"
            clearable
            style="width: 140px; margin-left: 12px"
            @change="handleSearch"
          >
            <el-option label="P0 紧急" value="P0" />
            <el-option label="P1 严重" value="P1" />
            <el-option label="P2 提醒" value="P2" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="handleSearch">搜索</el-button>
          <el-button style="margin-left: 8px" @click="handleReset">重置</el-button>
        </div>

        <el-table
          border
          :max-height="'calc(100vh - 380px)'"
          :data="tableData"
          @selection-change="onSelectionChange"
        >
          <el-table-column
            type="selection"
            width="45"
            align="center"
            :selectable="(row: AlertEventItem) => row.status === 'open'"
          />
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="级别" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="severityTagType(row.severity)" effect="dark">{{
                row.severity
              }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rule_id" label="规则" width="180" show-overflow-tooltip />
          <el-table-column prop="message" label="告警内容" min-width="300" show-overflow-tooltip />
          <el-table-column label="当前值" width="100" align="center">
            <template #default="{ row }">
              {{ row.current_value != null ? Number(row.current_value).toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="阈值" width="100" align="center">
            <template #default="{ row }">
              {{ row.threshold_value != null ? Number(row.threshold_value).toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'open' ? 'primary' : 'info'" effect="dark">
                {{ row.status === 'open' ? '未确认' : '已确认' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="acked_by" label="确认人" width="100" />
          <el-table-column prop="created_at" label="触发时间" width="170" />
          <el-table-column label="操作" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'open'"
                type="primary"
                size="small"
                @click="handleAck(row.id)"
                >确认</el-button
              >
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          style="margin-top: 18px; justify-content: flex-end; display: flex"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  BellFilled,
  WarningFilled,
  InfoFilled,
  CircleCheck,
  Warning,
  Refresh,
} from '@element-plus/icons-vue'
import { getAlertList, ackAlert, type AlertEventItem } from '@/api/system'

const filterStatus = ref('')
const filterSeverity = ref('')
const page = ref(1)
const pageSize = ref(20)
const tableData = ref<AlertEventItem[]>([])
const total = ref(0)
const loading = ref(false)
const selectedIds = ref<number[]>([])
const batchLoading = ref(false)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const severityCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const item of tableData.value) {
    counts[item.severity] = (counts[item.severity] || 0) + 1
  }
  return counts
})

const unackedCount = computed(() => tableData.value.filter((r) => r.status === 'open').length)

const severityTagType = (s: string): 'primary' | 'info' => {
  if (s === 'P0') return 'primary'
  if (s === 'P1') return 'info'
  return 'info'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertList({
      page: page.value,
      page_size: pageSize.value,
      status: filterStatus.value || undefined,
      severity: filterSeverity.value || undefined,
    })
    tableData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载告警列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  loadData()
}

const handleReset = () => {
  filterStatus.value = ''
  filterSeverity.value = ''
  page.value = 1
  loadData()
}

const onSelectionChange = (rows: AlertEventItem[]) => {
  selectedIds.value = rows.map((r) => r.id)
}

const handleAck = async (alertId: number) => {
  try {
    await ackAlert(alertId)
    ElMessage.success('告警已确认')
    loadData()
  } catch {
    ElMessage.error('确认失败')
  }
}

const batchAck = async () => {
  batchLoading.value = true
  let ok = 0
  for (const id of selectedIds.value) {
    try {
      await ackAlert(id)
      ok++
    } catch {
      /* skip */
    }
  }
  batchLoading.value = false
  ElMessage.success(`成功确认 ${ok}/${selectedIds.value.length} 条`)
  selectedIds.value = []
  loadData()
}

onMounted(() => {
  loadData()
  refreshTimer = setInterval(loadData, 15000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.alert-wrap {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #f8fafc;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.kpi-card {
  transition: transform 0.2s;
  height: 100%;
}
.kpi-card:hover {
  border-color: #cbd5e1 !important;
}
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
  color: #0f172a;
  line-height: 1.2;
}
.kpi-label {
  font-size: 13px;
  color: #bfbfbf;
  margin-top: 4px;
}

.full-card {
  display: flex;
  flex-direction: column;
}
:deep(.el-card__body) {
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.card-body-inner {
  display: flex;
  flex-direction: column;
}
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.filter-bar {
  margin: 12px 0;
  display: flex;
  align-items: center;
}
</style>
