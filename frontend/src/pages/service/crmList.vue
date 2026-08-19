<template>
  <div class="crm-list-page">
    <div class="page-header">
      <h2>CRM工单列表</h2>
      <el-button type="primary" @click="$router.push('/crm/create')">新建工单</el-button>
    </div>

    <!-- 搜索区域 -->
    <el-card class="search-card">
      <el-form inline :model="searchForm">
        <el-form-item label="工单状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable>
            <el-option label="已提交" value="submitted"></el-option>
            <el-option label="已处理" value="processed"></el-option>
            <el-option label="已回复" value="answered"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="getTableData">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工单表格 -->
    <el-table border :data="tableData" style="width:100%;">
      <el-table-column label="工单ID" prop="id" width="80"></el-table-column>
      <el-table-column label="外部ID" prop="external_id" min-width="140">
        <template #default="{ row }">
          {{ row.external_id || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="工单内容" min-width="280">
        <template #default="{ row }">
          {{ parseRawText(row.raw_data) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" prop="created_at" width="170"></el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pageInfo.pageNum"
      v-model:page-size="pageInfo.pageSize"
      :total="pageInfo.total"
      layout="total, sizes, prev, pager, next, jumper"
      class="pagination-box"
      @change="getTableData"
    ></el-pagination>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getWorkOrders, type WorkOrderListItem } from '@/api/audit'

const searchForm = ref({
  status: ''
})

const pageInfo = ref({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<WorkOrderListItem[]>([])

const getTableData = async () => {
  try {
    const res = await getWorkOrders({
      page: pageInfo.value.pageNum,
      page_size: pageInfo.value.pageSize,
      status: searchForm.value.status || undefined
    })
    tableData.value = res.items
    pageInfo.value.total = res.total
  } catch {
    ElMessage.error('加载工单列表失败')
  }
}

const resetSearch = () => {
  searchForm.value.status = ''
  pageInfo.value.pageNum = 1
  getTableData()
  ElMessage.info('搜索条件已重置')
}

const parseRawText = (raw: string) => {
  if (!raw) return '-'
  try {
    const obj = JSON.parse(raw)
    return obj.detail_desc || obj.question || obj.title || obj.content || raw.substring(0, 100)
  } catch {
    return raw.length > 100 ? raw.substring(0, 100) + '...' : raw
  }
}

const statusType = (s: string) => {
  const map: Record<string, string> = {
    submitted: 'info',
    answered: 'info',
    processed: 'primary'
  }
  return map[s] || ''
}

const statusText = (s: string) => {
  const map: Record<string, string> = {
    submitted: '已提交',
    answered: '已回复',
    processed: '已处理'
  }
  return map[s] || s
}

onMounted(() => {
  getTableData()
})
</script>

<style scoped>
/* 统一居中样式，和create、detail页面一致 */
.crm-list-page {
  width: 94%;
  max-width: 1200px;
  margin: 40px auto 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 19px;
}
.search-card {
  margin-bottom: 20px;
}
.pagination-box {
  margin-top: 16px;
  text-align: right;
}
</style>
