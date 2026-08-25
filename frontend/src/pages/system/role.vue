<template>
  <div class="role-wrap">
    <div class="header-bar">
      <h3>角色管理</h3>
      <el-button type="primary" @click="openAddDialog">
        <el-icon><Plus /></el-icon> 新增角色
      </el-button>
    </div>

    <!-- 角色卡片 -->
    <div class="role-cards">
      <el-card v-for="role in tableData" :key="role.id" class="role-card" shadow="hover">
        <div class="role-card-header">
          <div class="role-icon-box" :style="{ background: roleColor(role.role_key) }">
            <el-icon :size="24">
              <UserFilled v-if="role.role_key === 'superadmin'" />
              <Setting v-else-if="role.role_key === 'admin'" />
              <Monitor v-else-if="role.role_key === 'ops'" />
              <Service v-else-if="role.role_key === 'service'" />
              <Ticket v-else-if="role.role_key === 'dept'" />
              <User v-else />
            </el-icon>
          </div>
          <div class="role-meta">
            <div class="role-name">
              {{ role.role_name }}
            </div>
            <div class="role-key">
              {{ role.role_key }}
            </div>
          </div>
          <el-tag :color="roleColor(role.role_key)" effect="dark" style="border: none">
            {{ userCountByRole(role.role_key) }}人
          </el-tag>
        </div>

        <div class="role-desc">
          {{ role.description || '暂无描述' }}
        </div>

        <!-- 权限矩阵 -->
        <div class="perm-section">
          <div class="perm-title">可访问页面</div>
          <div class="perm-tags">
            <el-tag
              v-for="perm in getPermissions(role)"
              :key="perm"
              size="small"
              effect="plain"
              style="margin: 2px"
            >
              {{ perm }}
            </el-tag>
          </div>
        </div>

        <div class="role-actions">
          <el-button link type="primary" @click="openEditDialog(role)"> 编辑 </el-button>
          <el-button link type="info" @click="handleDelete(role)"> 删除 </el-button>
        </div>
      </el-card>
    </div>

    <el-dialog
      v-model="formVisible"
      :title="formMode === 'add' ? '新增角色' : '编辑角色'"
      width="600px"
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
        <el-form-item label="可访问页面">
          <el-checkbox-group v-model="formData.permissions">
            <div v-for="page in ALL_PAGES" :key="page.path" style="margin-bottom: 4px">
              <el-checkbox :value="page.path">
                {{ page.label }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false"> 取消 </el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit"> 确认 </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled, Setting, Monitor, Service, Ticket, User, Plus } from '@element-plus/icons-vue'
import {
  getRoleList,
  createRole,
  updateRole,
  deleteRole,
  getUserList,
  type RoleItem,
  type UserListItem,
} from '@/api/system'
import { roleColor, roleSortKey } from '@/utils/roleColor'
import { ALL_PAGES, getPageLabel } from '@/config/pages'

const tableData = ref<RoleItem[]>([])
const allUsers = ref<UserListItem[]>([])

const formVisible = ref(false)
const formMode = ref<'add' | 'edit'>('add')
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formData = ref({ role_key: '', role_name: '', description: '', permissions: [] as string[] })

const getPermissions = (role: RoleItem) => (role.permissions || []).map((p) => getPageLabel(p))

const userCountByRole = (roleKey: string) => allUsers.value.filter((u) => u.role === roleKey).length

const loadData = async () => {
  try {
    const roles = await getRoleList()
    tableData.value = roles.sort((a, b) => roleSortKey(a.role_key) - roleSortKey(b.role_key))
    const res = await getUserList({ page: 1, page_size: 999 })
    allUsers.value = res.items
  } catch {
    ElMessage.error('加载角色列表失败')
  }
}

const resetForm = () => {
  formData.value = { role_key: '', role_name: '', description: '', permissions: [] }
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
    description: row.description || '',
    permissions: row.permissions || [],
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
        description: formData.value.description || undefined,
        permissions: formData.value.permissions,
      })
      ElMessage.success('角色创建成功')
    } else {
      await updateRole(editingId.value!, {
        role_name: formData.value.role_name.trim(),
        description: formData.value.description,
        permissions: formData.value.permissions,
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
      type: 'info',
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
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #f8fafc;
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.role-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.role-card {
  transition: border-color 0.2s;
}
.role-card:hover {
  border-color: #cbd5e1 !important;
}

.role-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.role-icon-box {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.role-meta {
  flex: 1;
}
.role-name {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}
.role-key {
  font-size: 12px;
  color: #bfbfbf;
  margin-top: 2px;
}

.role-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
  margin-bottom: 16px;
  min-height: 40px;
}

.perm-section {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.perm-title {
  font-size: 12px;
  color: #bfbfbf;
  margin-bottom: 8px;
}
.perm-tags {
  display: flex;
  flex-wrap: wrap;
}

.role-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
