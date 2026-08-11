<template>
  <div style="padding:16px">
    <el-card title="角色权限管理">
      <el-button type="primary" @click="userStore.switchRole(userStore.role === 'admin' ? 'operator' : 'admin')">
        切换当前角色（当前：{{ userStore.role }}）
      </el-button>
      <div class="mt-4">
        <BatchTable
          :table-data="tableData"
          :total="total"
          v-model:page-num="pageNum"
          v-model:page-size="pageSize"
        >
          <el-table-column label="账号ID" prop="id" width="100" />
          <el-table-column label="用户名" prop="name" />
          <el-table-column label="角色" prop="role" width="120" />
          <el-table-column label="操作" width="200" v-if="userStore.hasPerm('system')">
            <template #default="{ row }">
              <el-button text type="primary">编辑权限</el-button>
            </template>
          </el-table-column>
        </BatchTable>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BatchTable from '@/components/BatchTable.vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const tableData = ref([
  { id: 'U001', name: '超级管理员', role: 'admin' },
  { id: 'U002', name: '客服操作员', role: 'operator' }
])
const total = ref(2)
const pageNum = ref(1)
const pageSize = ref(10)

onMounted(() => {})
</script>
