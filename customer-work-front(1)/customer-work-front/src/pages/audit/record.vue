<template>
  <div style="padding:16px">
    <el-card title="审核历史记录">
      <BatchTable
        :table-data="tableData"
        :total="total"
        v-model:page-num="pageNum"
        v-model:page-size="pageSize"
        @page-change="loadData"
      >
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="问题" prop="question" />
        <el-table-column label="审核结果" prop="result" width="100">
          <template #default="{ row }">
            <el-tag :type="row.result === 'pass' ? 'success' : 'danger'">
              {{ row.result === 'pass' ? '通过' : '驳回' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审核人" prop="auditor" width="100" />
        <el-table-column label="审核时间" prop="auditTime" width="160" />
      </BatchTable>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BatchTable from '@/components/BatchTable.vue'
import { auditRecordList, AuditRecord } from '@/mock/audit'

const tableData = ref<AuditRecord[]>([])
const total = ref(0)
const pageNum = ref(1)
const pageSize = ref(10)

const loadData = () => {
  tableData.value = JSON.parse(JSON.stringify(auditRecordList))
  total.value = tableData.value.length
}

onMounted(loadData)
</script>
