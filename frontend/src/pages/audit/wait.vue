<template>
  <div style="padding: 16px;">
    <el-card title="待审核知识库">
      <BatchTable
        :table-data="tableData"
        :total="total"
        v-model:page-num="pageNum"
        v-model:page-size="pageSize"
        show-batch
        batch-text="批量入库"
        @batch="batchPass"
        @page-change="loadData"
      >
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="问题" prop="question" />
        <el-table-column label="草稿答案" prop="draftAnswer" />
        <el-table-column label="分类" prop="categoryName" width="120" />
        <el-table-column label="置信度" prop="confidence" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.confidence < 70 ? 'red' : '#333' }">
              {{ row.confidence }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="createTime" width="160" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button text type="success" @click="singlePass(row)">通过入库</el-button>
            <el-button text type="danger" @click="singleReject(row)">驳回</el-button>
          </template>
        </el-table-column>
      </BatchTable>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import BatchTable from '@/components/BatchTable.vue'
import { waitAuditList, AuditRow } from '@/mock/audit'

const tableData = ref<AuditRow[]>([])
const total = ref(0)
const pageNum = ref(1)
const pageSize = ref(10)

const loadData = () => {
  tableData.value = JSON.parse(JSON.stringify(waitAuditList))
  total.value = tableData.value.length
}

// 单条通过
const singlePass = (row: AuditRow) => {
  ElMessage.success(`【${row.question}】审核通过入库`)
  loadData()
}
// 单条驳回
const singleReject = (row: AuditRow) => {
  ElMessage.warning(`【${row.question}】已驳回`)
  loadData()
}
// 批量入库
const batchPass = (list: AuditRow[]) => {
  ElMessage.success(`批量审核通过${list.length}条`)
  loadData()
}

onMounted(loadData)
</script>
