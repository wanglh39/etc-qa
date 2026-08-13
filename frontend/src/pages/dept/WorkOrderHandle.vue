<template>
  <!-- 外层容器：设置最小高度为视口高度，背景色加深以突出卡片 -->
  <div class="dept-page">
    <!-- 卡片主体：使用 flex 布局撑开高度 -->
    <el-card shadow="hover" class="main-card">
      <template #header>
        <div class="card-title">{{ currentDeptName }}工单处理</div>
      </template>

      <!-- 搜索区域：增加底部间距 -->
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="工单编号">
          <el-input v-model="searchForm.orderNo" placeholder="请输入工单编号" clearable style="width: 200px;"></el-input>
        </el-form-item>
        <el-form-item label="工单状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 150px;">
            <el-option label="待处理" value="submitted"></el-option>
            <el-option label="已回复" value="answered"></el-option>
            <el-option label="已办结" value="processed"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格区域：flex:1 让它自动占据中间所有剩余空间 -->
      <div class="table-wrapper">
        <el-table
          :data="displayList"
          border
          stripe
          style="width: 100%; height: 100%;"
          height="100%"
          v-loading="loading"
        >
          <el-table-column label="工单ID" prop="id" width="100" align="center"></el-table-column>
          <el-table-column label="工单编号" prop="external_id" min-width="180"></el-table-column>
          <el-table-column label="提交时间" prop="created_at" min-width="180" align="center"></el-table-column>
          <el-table-column label="工单状态" prop="status" width="120" align="center">
            <template #default="scope">
              <el-tag v-if="scope.row.status === 'submitted'" type="warning" effect="light">待处理</el-tag>
              <el-tag v-else-if="scope.row.status === 'answered'" type="primary" effect="light">已回复</el-tag>
              <el-tag v-else-if="scope.row.status === 'processed'" type="success" effect="light">已办结</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
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

      <!-- 分页区域：靠右对齐，保持固定间距 -->
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
import { ElMessage } from 'element-plus'
import { getWorkOrders, type WorkOrderListItem } from '@/api/audit'
import { replyWorkOrder } from '@/api/workorder'

// 路由实例，获取当前部门编码
const route = useRoute()
const router = useRouter()

// ===================== 部门名称映射配置 =====================
const deptNameMap: Record<string, string> = {
  aftersale: '售后处理部',
  ops: '技术运维部',
  finance: '财务部',
  market: '市场部',
  human: '人事部'
}
// 获取路由上的deptCode参数
const deptCode = computed(() => route.params.deptCode as string)
// 动态页面标题，匹配对应部门
const currentDeptName = computed(() => deptNameMap[deptCode.value] || '通用部门')
// ======================================================================

// 搜索表单数据
const searchForm = ref({
  orderNo: '',
  status: ''
})

// 分页参数
const page = ref({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

// 表格工单数据
const tableData = ref<WorkOrderListItem[]>([])
const loading = ref(false)

// 工单编号本地过滤（仅作用于当前页）
const displayList = computed(() => {
  const kw = searchForm.value.orderNo.trim()
  if (!kw) return tableData.value
  return tableData.value.filter((item) => (item.external_id || '').includes(kw))
})

// 查询工单列表（按部门 + 状态）
const getTableList = async () => {
  loading.value = true
  try {
    const res = await getWorkOrders({
      page: page.value.pageNum,
      page_size: page.value.pageSize,
      dept: deptCode.value,
      status: searchForm.value.status || undefined
    })
    tableData.value = res.items
    page.value.total = res.total
  } catch {
    ElMessage.error('加载工单列表失败')
  } finally {
    loading.value = false
  }
}

// 查询按钮：重置到第一页再加载
const handleSearch = () => {
  page.value.pageNum = 1
  getTableList()
}

// 重置搜索条件
const resetSearch = () => {
  searchForm.value = { orderNo: '', status: '' }
  page.value.pageNum = 1
  getTableList()
}

// 打开工单详情页面，携带部门编码与工单ID
const openDetail = (row: WorkOrderListItem) => {
  router.push({
    path: `/dept/handle/${deptCode.value}/detail/${row.id}`
  })
}

// 办结工单操作
const handleFinish = async (row: WorkOrderListItem) => {
  try {
    await replyWorkOrder(row.id, { handle_remark: '快速办结', back_dept: '' })
    ElMessage.success(`工单${row.external_id}已办结`)
    getTableList()
  } catch {
    ElMessage.error('办结失败')
  }
}

// 页面初始化加载数据
onMounted(() => {
  getTableList()
})

// 切换左侧菜单（切换部门）自动重置第一页并刷新数据
watch(deptCode, () => {
  page.value.pageNum = 1
  getTableList()
})
</script>

<style scoped>
/* 1. 页面整体布局：灰色背景，撑满全屏 */
.dept-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f0f2f5; /* 浅灰背景 */
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  justify-content: center;
}

/* 2. 卡片样式：限制最大宽度，内部使用 Flex 纵向布局 */
.main-card {
  width: 100%;
  max-width: 1400px; /* 防止在大屏上太宽 */
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px); /* 关键：减去上下 padding，确保不出现滚动条 */
}

/* 3. 标题样式优化 */
.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

/* 4. 搜索表单：增加底部间距，添加分割线 */
.search-form {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

/* 5. 表格容器：关键！使用 flex:1 自动填满中间剩余空间 */
.table-wrapper {
  flex: 1;
  margin-bottom: 20px; /* 与分页保持间距 */
  overflow: hidden; /* 防止内容溢出 */
}

/* 6. 分页容器：靠右对齐 */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
}

/* 深度选择器：调整卡片内部 Padding，使其更紧凑一致 */
:deep(.el-card__header) {
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
}
:deep(.el-card__body) {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
