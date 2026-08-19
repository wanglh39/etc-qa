<template>
  <div class="audit-pending-wrap">
    <!-- KPI 概览卡片 -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24"><Clock /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ total }}</div>
          <div class="kpi-label">待审核总数</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ currentPageList.length }}</div>
          <div class="kpi-label">当前页条数</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24"><Select /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ selectedRows.length }}</div>
          <div class="kpi-label">已选中</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24"><Files /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ categoryCount }}</div>
          <div class="kpi-label">涉及分类</div>
        </div>
      </div>
    </div>

    <el-card class="full-card">
      <div class="card-body-inner">
        <div class="toolbar">
          <h3>待审核新问题列表</h3>
          <div class="toolbar-right">
            <el-select v-model="filterCategory" placeholder="全部分类" clearable style="width: 180px" @change="onFilterChange">
              <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
            </el-select>
            <el-button type="primary" @click="batchApprove">批量入库</el-button>
            <el-button type="primary" @click="batchReject">批量驳回</el-button>
          </div>
        </div>
        <el-table border :data="currentPageList" @selection-change="handleSelectionChange" v-loading="loading">
          <el-table-column type="selection" width="55" />
          <el-table-column prop="id" label="知识ID" width="80" />
          <el-table-column prop="question" label="用户问题" min-width="260" />
          <el-table-column prop="category_l1" label="分类" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.category_l1 }}</el-tag>
              <span v-if="row.category_l2" style="color: #bfbfbf; margin-left: 4px">/ {{ row.category_l2 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="提交时间" width="170">
            <template #default="{ row }">
              <span style="color: #bfbfbf">{{ row.created_at || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button link type="primary" @click="goDetail(row.id)">查看详情</el-button>
              <el-button link type="primary" @click="handleApprove(row.id)">入库</el-button>
              <el-button link type="primary" @click="handleReject(row.id)">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Document, Select, Files } from '@element-plus/icons-vue'
import { getQAList, updateQAStatus, type QAListItem } from '@/api/knowledge'

const router = useRouter()

const page = ref(1)
const pageSize = ref(10)
const tableAllData = ref<QAListItem[]>([])
const total = ref(0)
const selectedRows = ref<QAListItem[]>([])
const loading = ref(false)
const filterCategory = ref('')

const currentPageList = computed(() => tableAllData.value)
const categoryCount = computed(() => {
  const set = new Set<string>()
  tableAllData.value.forEach((r) => { if (r.category_l1) set.add(r.category_l1) })
  return set.size
})
const categoryOptions = computed(() => {
  const set = new Set<string>()
  tableAllData.value.forEach((r) => { if (r.category_l1) set.add(r.category_l1) })
  return Array.from(set).sort()
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await getQAList({
      page: page.value,
      page_size: pageSize.value,
      status: 'deprecated',
      category_l1: filterCategory.value || undefined
    })
    tableAllData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载待审核列表失败')
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => {
  page.value = 1
  loadData()
}

const goDetail = (id: number) => {
  router.push({ name: 'PendingDetail', query: { id } })
}

const handleApprove = async (qaId: number) => {
  try {
    await updateQAStatus(qaId, 'active')
    ElMessage.success('已入库')
    loadData()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleReject = async (qaId: number) => {
  try {
    await updateQAStatus(qaId, 'archived')
    ElMessage.success('已驳回')
    loadData()
  } catch {
    ElMessage.error('操作失败')
  }
}

const batchApprove = async () => {
  await batchUpdate('active', '入库')
}

const batchReject = async () => {
  await batchUpdate('archived', '驳回')
}

const handleSelectionChange = (rows: QAListItem[]) => {
  selectedRows.value = rows
}

const batchUpdate = async (status: string, actionName: string) => {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) {
    ElMessage.warning(`请先勾选要${actionName}的问题`)
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认${actionName}选中的 ${ids.length} 条问题？`,
      `${actionName}确认`,
      { type: 'info', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    const results = await Promise.allSettled(ids.map((id) => updateQAStatus(id, status)))
    const ok = results.filter((r) => r.status === 'fulfilled').length
    const fail = results.length - ok
    ElMessage.success(`${actionName}完成：成功 ${ok} 条${fail ? `，失败 ${fail} 条` : ''}`)
    loadData()
  } catch {
    ElMessage.error('批量操作失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.audit-pending-wrap {
  width: 100%;
  padding: 20px;
  box-sizing: border-box;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  
  transition: transform 0.2s;
}
.kpi-card:hover {
  border-color: #CBD5E1;
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  background: #F1F5F9; color: #1677FF;
}
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #0F172A;
}
.kpi-label {
  font-size: 13px;
  color: #bfbfbf;
  margin-top: 2px;
}

.full-card {
  min-height: 400px;
}
.card-body-inner {
  display: flex;
  flex-direction: column;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.toolbar h3 {
  margin: 0;
  font-size: 16px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
