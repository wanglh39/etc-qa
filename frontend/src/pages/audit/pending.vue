<template>
  <div class="audit-pending-wrap">
    <el-card class="full-card">
      <!-- 利用 el-card 默认的 body 容器，直接在其上写 flex 布局 -->
      <div class="card-body-inner">
        <h3>待审核新问题列表</h3>
        <div class="btn-group">
          <el-button type="primary" @click="batchApprove">批量入库</el-button>
          <el-button type="danger" @click="batchReject">批量驳回</el-button>
        </div>
        <!-- 表格不设置固定高度，高度随内容自适应，无滚动条 -->
        <el-table border :data="currentPageList" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column prop="id" label="知识ID" width="80" />
          <el-table-column prop="question" label="用户问题" min-width="260" />
          <el-table-column prop="category_l1" label="分类" width="120">
            <template #default="{ row }">
              {{ row.category_l1 }}{{ row.category_l2 ? ' / ' + row.category_l2 : '' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="提交时间" width="170" />
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button link type="primary" @click="goDetail(row.id)">查看详情</el-button>
              <el-button link type="success" @click="handleApprove(row.id)">入库</el-button>
              <el-button link type="danger" @click="handleReject(row.id)">驳回</el-button>
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
import { getQAList, updateQAStatus, type QAListItem } from '@/api/knowledge'

const router = useRouter()

const page = ref(1)
const pageSize = ref(10)
const tableAllData = ref<QAListItem[]>([])
const total = ref(0)
const selectedRows = ref<QAListItem[]>([])

const currentPageList = computed(() => tableAllData.value)

const loadData = async () => {
  try {
    const res = await getQAList({
      page: page.value,
      page_size: pageSize.value,
      status: 'deprecated'
    })
    tableAllData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载待审核列表失败')
  }
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
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
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
/* 外层容器：撑满屏幕可视区域，隐藏自身滚动条 */
.audit-pending-wrap {
  width: 100%;
  height: 100vh; /* 占满整个视口高度 */
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden; /* 关键：隐藏外层容器的滚动条 */
}

/* Card 填满父容器 */
.full-card {
  height: 100%;
}

/* 深度修改 el-card 的 body 容器：用 Flex 布局管理子元素，无溢出 */
:deep(.el-card__body) {
  height: 100%;
  padding: 20px;
  box-sizing: border-box; /* 关键：padding 纳入高度计算，避免总高度超出 */
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 禁止内部内容溢出产生滚动条 */
}

/* 内部内容区：Flex 纵向布局，自动填充剩余空间 */
.card-body-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 按钮组：上下间距 */
.btn-group {
  margin: 16px 0;
}

/* 表格：无固定高度，随内容自适应（每页 2 条数据时，仅渲染 2 行） */
.el-table {
  flex: 1; /* 自动填充剩余空间，但内容少时不会强制拉伸 */
  overflow: visible; /* 允许内容自然显示，无内部滚动条 */
}
</style>