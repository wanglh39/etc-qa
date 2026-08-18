<template>
  <div class="dept-page">
    <!-- KPI概览卡片 -->
    <div class="kpi-row">
      <el-card class="kpi-card" shadow="hover" @click="filterByStatus('')">
        <div class="kpi-inner">
          <div class="kpi-icon total"><el-icon><Document /></el-icon></div>
          <div class="kpi-info">
            <div class="kpi-num">{{ stats.total || 0 }}</div>
            <div class="kpi-label">全部工单</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover" @click="filterByStatus('submitted')">
        <div class="kpi-inner">
          <div class="kpi-icon pending"><el-icon><Clock /></el-icon></div>
          <div class="kpi-info">
            <div class="kpi-num">{{ stats.submitted || 0 }}</div>
            <div class="kpi-label">待处理</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover" @click="filterByStatus('answered')">
        <div class="kpi-inner">
          <div class="kpi-icon answered"><el-icon><ChatDotRound /></el-icon></div>
          <div class="kpi-info">
            <div class="kpi-num">{{ stats.answered || 0 }}</div>
            <div class="kpi-label">已回复</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover" @click="filterByStatus('processed')">
        <div class="kpi-inner">
          <div class="kpi-icon done"><el-icon><CircleCheck /></el-icon></div>
          <div class="kpi-info">
            <div class="kpi-num">{{ stats.processed || 0 }}</div>
            <div class="kpi-label">已办结</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon today"><el-icon><Calendar /></el-icon></div>
          <div class="kpi-info">
            <div class="kpi-num">{{ stats.today || 0 }}</div>
            <div class="kpi-label">今日新增</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 主卡片 -->
    <el-card shadow="hover" class="main-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ currentDeptName }}工单处理</span>
          <div class="header-actions" v-if="selectedIds.length > 0">
            <el-tag type="info">已选 {{ selectedIds.length }} 条</el-tag>
            <el-button type="success" size="small" :loading="batchLoading" @click="batchFinish">
              批量办结
            </el-button>
          </div>
        </div>
      </template>

      <!-- Tab状态筛选 -->
      <el-tabs v-model="activeTab" class="status-tabs" @tab-change="onTabChange">
        <el-tab-pane label="全部" name="">
          <template #label>
            <span>全部 <el-badge :value="stats.total" :max="999" type="primary" /></span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="submitted">
          <template #label>
            <span>待处理 <el-badge :value="stats.submitted" :max="999" type="warning" /></span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="answered">
          <template #label>
            <span>已回复 <el-badge :value="stats.answered" :max="999" type="primary" /></span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="processed">
          <template #label>
            <span>已办结 <el-badge :value="stats.processed" :max="999" type="success" /></span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <!-- 搜索区域 -->
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="工单编号">
          <el-input v-model="searchForm.orderNo" placeholder="请输入工单编号" clearable style="width: 200px;" @keyup.enter="handleSearch"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格区域 -->
      <div class="table-wrapper">
        <el-table
          :data="displayList"
          border
          stripe
          style="width: 100%; height: 100%;"
          height="100%"
          v-loading="loading"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="45" align="center" :selectable="(row: WorkOrderListItem) => row.status !== 'processed'" />
          <el-table-column label="工单ID" prop="id" width="80" align="center"></el-table-column>
          <el-table-column label="工单编号" prop="external_id" min-width="180"></el-table-column>
          <el-table-column label="问题类型" min-width="120" align="center">
            <template #default="scope">
              <el-tag v-if="parseRaw(scope.row).problem_type" size="small" effect="plain">
                {{ parseRaw(scope.row).problem_type }}
              </el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="优先级" width="100" align="center">
            <template #default="scope">
              <el-tag
                v-if="parseRaw(scope.row).priority"
                :type="priorityType(parseRaw(scope.row).priority)"
                size="small"
              >
                {{ parseRaw(scope.row).priority }}
              </el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" prop="created_at" min-width="160" align="center"></el-table-column>
          <el-table-column label="工单状态" prop="status" width="100" align="center">
            <template #default="scope">
              <el-tag v-if="scope.row.status === 'submitted'" type="warning" effect="light">待处理</el-tag>
              <el-tag v-else-if="scope.row.status === 'answered'" type="primary" effect="light">已回复</el-tag>
              <el-tag v-else-if="scope.row.status === 'processed'" type="success" effect="light">已办结</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="scope">
              <el-button link type="primary" size="small" @click="openDetail(scope.row)">查看详情</el-button>
              <el-button
                link
                type="success"
                size="small"
                :disabled="scope.row.status === 'processed'"
                @click="handleFinish(scope.row)"
              >办结</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 分页区域 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="page.pageNum"
          v-model:page-size="page.pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="page.total"
          background
          @size-change="getTableList"
          @current-change="getTableList"
        ></el-pagination>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Clock, ChatDotRound, CircleCheck, Calendar } from '@element-plus/icons-vue'
import { getWorkOrders, getWorkOrderStats, type WorkOrderListItem, type WorkOrderStats } from '@/api/audit'
import { replyWorkOrder } from '@/api/workorder'

const route = useRoute()
const router = useRouter()

const deptNameMap: Record<string, string> = {
  aftersale: '售后处理部',
  ops: '技术运维部',
  finance: '财务部',
  market: '市场部',
  human: '人事部'
}
const deptCode = computed(() => route.params.deptCode as string)
const currentDeptName = computed(() => deptNameMap[deptCode.value] || '通用部门')

const activeTab = ref('')
const searchForm = ref({ orderNo: '' })
const page = ref({ pageNum: 1, pageSize: 10, total: 0 })
const tableData = ref<WorkOrderListItem[]>([])
const loading = ref(false)
const stats = ref<WorkOrderStats>({ total: 0, submitted: 0, answered: 0, processed: 0, today: 0 })
const selectedIds = ref<number[]>([])
const batchLoading = ref(false)

const parseRaw = (row: WorkOrderListItem): Record<string, any> => {
  try { return JSON.parse(row.raw_data || '{}') } catch { return {} }
}

const priorityType = (p: string): 'danger' | 'warning' | 'info' => {
  if (p === '高' || p === 'urgent') return 'danger'
  if (p === '中' || p === 'normal') return 'warning'
  return 'info'
}

const displayList = computed(() => {
  const kw = searchForm.value.orderNo.trim()
  if (!kw) return tableData.value
  return tableData.value.filter((item) => (item.external_id || '').includes(kw))
})

const getTableList = async () => {
  loading.value = true
  try {
    const res = await getWorkOrders({
      page: page.value.pageNum,
      page_size: page.value.pageSize,
      dept: deptCode.value,
      status: activeTab.value || undefined
    })
    tableData.value = res.items
    page.value.total = res.total
  } catch {
    ElMessage.error('加载工单列表失败')
  } finally {
    loading.value = false
  }
}

const getStats = async () => {
  try {
    stats.value = await getWorkOrderStats()
  } catch {
    stats.value = { total: 0, submitted: 0, answered: 0, processed: 0, today: 0 }
  }
}

const onTabChange = () => {
  page.value.pageNum = 1
  getTableList()
}

const filterByStatus = (status: string) => {
  activeTab.value = status
  page.value.pageNum = 1
  getTableList()
}

const handleSearch = () => {
  page.value.pageNum = 1
  getTableList()
}

const resetSearch = () => {
  searchForm.value = { orderNo: '' }
  activeTab.value = ''
  page.value.pageNum = 1
  getTableList()
}

const onSelectionChange = (rows: WorkOrderListItem[]) => {
  selectedIds.value = rows.map((r) => r.id)
}

const openDetail = (row: WorkOrderListItem) => {
  router.push({ path: `/dept/handle/${deptCode.value}/detail/${row.id}` })
}

const handleFinish = async (row: WorkOrderListItem) => {
  try {
    await ElMessageBox.confirm(`确认办结工单 ${row.external_id}？`, '提示', { type: 'warning' })
    await replyWorkOrder(row.id, { handle_remark: '快速办结' })
    ElMessage.success(`工单${row.external_id}已办结`)
    getTableList()
    getStats()
  } catch {
    ElMessage.error('办结失败')
  }
}

const batchFinish = async () => {
  try {
    await ElMessageBox.confirm(`确认批量办结 ${selectedIds.value.length} 条工单？`, '批量办结', { type: 'warning' })
    batchLoading.value = true
    let ok = 0
    for (const id of selectedIds.value) {
      try {
        await replyWorkOrder(id, { handle_remark: '批量办结' })
        ok++
      } catch { /* skip */ }
    }
    ElMessage.success(`成功办结 ${ok}/${selectedIds.value.length} 条`)
    selectedIds.value = []
    getTableList()
    getStats()
  } catch {
    ElMessage.error('批量办结失败')
  } finally {
    batchLoading.value = false
  }
}

onMounted(() => {
  getTableList()
  getStats()
})

watch(deptCode, () => {
  page.value.pageNum = 1
  getTableList()
  getStats()
})
</script>

<style scoped>
.dept-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f0f2f5;
  padding: 20px;
  box-sizing: border-box;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.kpi-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
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
  font-size: 24px;
  color: #fff;
}
.kpi-icon.total { background: linear-gradient(135deg, #409eff, #337ecc); }
.kpi-icon.pending { background: linear-gradient(135deg, #e6a23c, #d48806); }
.kpi-icon.answered { background: linear-gradient(135deg, #409eff, #66b1ff); }
.kpi-icon.done { background: linear-gradient(135deg, #67c23a, #5daf34); }
.kpi-icon.today { background: linear-gradient(135deg, #909399, #7e8c9a); }

.kpi-num {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}
.kpi-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.main-card {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tabs {
  margin-bottom: 8px;
}

.search-form {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.table-wrapper {
  flex: 1;
  margin-bottom: 16px;
  overflow: hidden;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

:deep(.el-card__header) {
  padding: 16px 20px;
}
:deep(.el-card__body) {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
