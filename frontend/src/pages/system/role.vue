<template>
  <div class="role-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <h3>角色管理</h3>

        <div class="filter-bar">
          <el-button type="success" @click="openAddDialog">新增角色</el-button>
        </div>

        <el-table border :max-height="'calc(100vh - 280px)'" :data="tableData">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="role_key" label="角色标识" width="160" />
          <el-table-column prop="role_name" label="角色名称" width="180" />
          <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="170" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog
      v-model="formVisible"
      :title="formMode === 'add' ? '新增角色' : '编辑角色'"
      width="480px"
      @closed="resetForm"
    >
      <el-form :model="formData" label-width="90px">
        <el-form-item label="角色标识" required>
          <el-input
            v-model="formData.role_key"
            placeholder="如：admin / service / dept"
            :disabled="formMode === 'edit'"
          />
        </el-form-item>
        <el-form-item label="角色名称" required>
          <el-input v-model="formData.role_name" placeholder="如：管理员" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getRoleList,
  createRole,
  updateRole,
  deleteRole,
  type RoleItem
} from '@/api/system'

const tableData = ref<RoleItem[]>([])

const formVisible = ref(false)
const formMode = ref<'add' | 'edit'>('add')
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formData = ref({
  role_key: '',
  role_name: '',
  description: ''
})

const loadData = async () => {
  try {
    tableData.value = await getRoleList()
  } catch {
    ElMessage.error('加载角色列表失败')
  }
}

const resetForm = () => {
  formData.value = { role_key: '', role_name: '', description: '' }
  editingId.value = null
}

const openAddDialog = () => {
  formMode.value = 'add'
  resetForm()
  formVisible.value = true
}

const openEditDialog = (row: RoleItem) => {
  formMode.value = 'edit'
  editingId.value = row.id
  formData.value = {
    role_key: row.role_key,
    role_name: row.role_name,
    description: row.description || ''
  }
  formVisible.value = true
}

const handleSubmit = async () => {
  if (!formData.value.role_key.trim() || !formData.value.role_name.trim()) {
    ElMessage.warning('角色标识和名称不能为空')
    return
  }
  submitting.value = true
  try {
    if (formMode.value === 'add') {
      await createRole({
        role_key: formData.value.role_key.trim(),
        role_name: formData.value.role_name.trim(),
        description: formData.value.description || undefined
      })
      ElMessage.success('角色创建成功')
    } else {
      await updateRole(editingId.value!, {
        role_name: formData.value.role_name.trim(),
        description: formData.value.description
      })
      ElMessage.success('角色已更新')
    }
    formVisible.value = false
    loadData()
  } catch {
    ElMessage.error(formMode.value === 'add' ? '创建失败，标识可能已存在' : '更新失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: RoleItem) => {
  try {
    await ElMessageBox.confirm(`确认删除角色 "${row.role_name}"？删除后不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deleteRole(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch {
    ElMessage.error('删除失败，该角色可能仍有用户关联')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.role-wrap {
  width: 100%;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}
.full-card {
  height: 100%;
}
:deep(.el-card__body) {
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-body-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.filter-bar {
  margin: 12px 0;
}
.el-table {
  width: 100%;
}
</style>
