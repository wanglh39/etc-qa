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
            <el-option label="待处理" value="pending"></el-option>
            <el-option label="处理中" value="handling"></el-option>
            <el-option label="已完成" value="finish"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="getTableList">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格区域：flex:1 让它自动占据中间所有剩余空间 -->
      <div class="table-wrapper">
        <el-table
          :data="tableData"
          border
          stripe
          style="width: 100%; height: 100%;"
          height="100%"
        >
          <el-table-column label="工单ID" prop="id" width="100" align="center"></el-table-column>
          <el-table-column label="工单编号" prop="orderNo" min-width="180"></el-table-column>
          <el-table-column label="提交时间" prop="createTime" min-width="180" align="center"></el-table-column>
          <el-table-column label="工单状态" prop="status" width="120" align="center">
            <template #default="scope">
              <el-tag v-if="scope.row.status === 'pending'" type="warning" effect="light">待处理</el-tag>
              <el-tag v-else-if="scope.row.status === 'handling'" type="primary" effect="light">处理中</el-tag>
              <el-tag v-else-if="scope.row.status === 'finish'" type="success" effect="light">已完成</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template #default="scope">
              <el-button link type="primary" size="small" @click="openDetail(scope.row)">查看详情</el-button>
              <el-button link type="success" size="small" @click="handleFinish(scope.row)">办结</el-button>
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
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

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
const tableData = ref<any[]>([])

// 查询工单列表（按部门返回不同模拟数据）
const getTableList = async () => {
  console.log('当前部门编码：', deptCode.value, '查询参数：', searchForm.value, page.value)
  // 根据部门编码区分工单数据
  const code = deptCode.value
  if (code === 'aftersale') {
    // 售后工单数据
    tableData.value = [
      { id: 1, orderNo: 'SA20260717001', createTime: '2026-07-17 10:20:00', status: 'pending' },
      { id: 2, orderNo: 'SA20260717002', createTime: '2026-07-17 11:05:00', status: 'handling' }
    ]
  } else if (code === 'ops') {
    // 运维工单数据
    tableData.value = [
      { id: 1, orderNo: 'OPS20260724001', createTime: '2026-07-23 08:30:00', status: 'pending' }
    ]
  } else if (code === 'finance') {
    // 财务工单数据
    tableData.value = [
      { id: 1, orderNo: 'FIN20260722001', createTime: '2026-07-22 09:10:00', status: 'pending' },
      { id: 2, orderNo: 'FIN20260722002', createTime: '2026-07-22 14:20:00', status: 'handling' }
    ]
  } else if (code === 'market') {
    // 市场工单
    tableData.value = [
      { id: 1, orderNo: 'MKT20260720001', createTime: '2026-07-20 16:00:00', status: 'finish' }
    ]
  } else if (code === 'human') {
    // 人事工单
    tableData.value = [
      { id: 1, orderNo: 'HR20260721001', createTime: '2026-07-21 11:20:00', status: 'pending' }
    ]
  } else {
    // 默认兜底数据
    tableData.value = []
  }
  page.value.total = tableData.value.length
}

// 重置搜索条件
const resetSearch = () => {
  searchForm.value = { orderNo: '', status: '' }
  page.value.pageNum = 1
  getTableList()
}

// 打开工单详情页面，携带部门编码与工单ID
const openDetail = (row: any) => {
  router.push({
    path: `/dept/handle/${deptCode.value}/detail/${row.id}`
  })
}

// 办结工单操作
const handleFinish = (row: any) => {
  ElMessage.success(`工单${row.orderNo}已办结`)
  getTableList()
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