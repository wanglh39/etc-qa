<template>
  <div class="account-wrap">
    <!-- KPI概览卡片 -->
    <div class="kpi-row">
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24">
              <UserFilled />
            </el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">
              {{ total }}
            </div>
            <div class="kpi-label">总账号数</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24">
              <CircleCheck />
            </el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">
              {{ activeCount }}
            </div>
            <div class="kpi-label">启用</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24">
              <CircleClose />
            </el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">
              {{ disabledCount }}
            </div>
            <div class="kpi-label">禁用</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24">
              <Avatar />
            </el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">
              {{ superadminCount }}
            </div>
            <div class="kpi-label">超管数</div>
          </div>
        </div>
      </el-card>
    </div>

    <el-card class="full-card">
      <div class="card-body-inner">
        <div class="header-bar">
          <h3>账号管理</h3>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon> 新增账号
          </el-button>
        </div>

        <div class="filter-bar">
          <el-select
            v-model="filterRole"
            placeholder="角色筛选"
            clearable
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option
              v-for="r in roleOptions"
              :key="r.role_key"
              :label="r.role_name"
              :value="r.role_key"
            />
          </el-select>
          <el-select
            v-model="filterStatus"
            placeholder="状态筛选"
            clearable
            style="width: 140px; margin-left: 12px"
            @change="handleSearch"
          >
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="handleSearch">
            搜索
          </el-button>
          <el-button style="margin-left: 8px" @click="handleReset"> 重置 </el-button>
        </div>

        <el-table border :max-height="'calc(100vh - 380px)'" :data="tableData">
          <el-table-column label="用户" min-width="180">
            <template #default="{ row }">
              <div class="user-cell">
                <div class="user-avatar" :style="{ background: roleColor(row.role) }">
                  {{ row.username.charAt(0).toUpperCase() }}
                </div>
                <div class="user-info">
                  <div class="user-name">
                    {{ row.username }}
                  </div>
                  <div class="user-id">ID: {{ row.id }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="140" align="center">
            <template #default="{ row }">
              <el-tag :color="roleColor(row.role)" effect="dark" style="border: none">
                {{ roleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="dept" label="部门" width="140" align="center">
            <template #default="{ row }">
              <span v-if="row.dept">{{ deptOptions.find((d) => d.dept_key === row.dept)?.dept_name || row.dept }}</span>
              <span v-else style="color: #94a3b8">-</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'primary' : 'info'" effect="dark">
                {{ row.status === 'active' ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170" align="center" />
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEditDialog(row)"> 编辑 </el-button>
              <el-button link type="info" @click="openResetDialog(row)"> 重置密码 </el-button>
              <el-button
                v-if="row.status === 'active'"
                link
                type="info"
                @click="handleToggleStatus(row, 'disabled')"
              >
                禁用
              </el-button>
              <el-button v-else link type="primary" @click="handleToggleStatus(row, 'active')">
                启用
              </el-button>
              <el-button link type="info" @click="handleDelete(row)"> 删除 </el-button>
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

    <el-dialog
      v-model="formVisible"
      :title="formMode === 'add' ? '新增账号' : '编辑账号'"
      width="520px"
      @closed="resetForm"
    >
      <el-form :model="formData" label-width="90px">
        <el-form-item label="用户名" required>
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            :disabled="formMode === 'edit'"
          />
        </el-form-item>
        <el-form-item v-if="formMode === 'add'" label="密码" required>
          <el-input
            v-model="formData.password"
            type="password"
            show-password
            placeholder="请输入初始密码"
          />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="r in roleOptions"
              :key="r.role_key"
              :label="r.role_name"
              :value="r.role_key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="formData.dept" placeholder="可选" clearable style="width: 100%">
            <el-option
              v-for="d in deptOptions"
              :key="d.dept_key"
              :label="d.dept_name"
              :value="d.dept_key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="formData.status" style="width: 100%">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false"> 取消 </el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit"> 确认 </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetVisible" title="重置密码" width="440px" @closed="resetResetForm">
      <el-form :model="resetForm" label-width="90px">
        <el-form-item label="用户名">
          <el-input :value="resetPwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input
            v-model="resetPwdForm.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false"> 取消 </el-button>
        <el-button type="primary" :loading="resetting" @click="handleResetPassword">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled, CircleCheck, CircleClose, Avatar, Plus } from '@element-plus/icons-vue'
import {
  getUserList,
  createUser,
  updateUser,
  resetPassword,
  deleteUser,
  getRoleList,
  getDeptList,
  type UserListItem,
  type RoleItem,
  type DeptItem,
} from '@/api/system'
import { roleColor } from '@/utils/roleColor'

const filterRole = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = ref(10)
const tableData = ref<UserListItem[]>([])
const total = ref(0)
const roleOptions = ref<RoleItem[]>([])
const deptOptions = ref<DeptItem[]>([])

const formVisible = ref(false)
const formMode = ref<'add' | 'edit'>('add')
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formData = ref({ username: '', password: '', role: '', dept: '', status: 'active' })

const resetVisible = ref(false)
const resetting = ref(false)
const resetPwdForm = ref({ userId: 0, username: '', newPassword: '' })

const activeCount = computed(() => tableData.value.filter((r) => r.status === 'active').length)
const disabledCount = computed(() => tableData.value.filter((r) => r.status === 'disabled').length)
const superadminCount = computed(
  () => tableData.value.filter((r) => r.role === 'superadmin').length
)

const roleLabel = (key: string) => {
  const r = roleOptions.value.find((r) => r.role_key === key)
  return r ? r.role_name : key
}

const loadData = async () => {
  try {
    const res = await getUserList({
      page: page.value,
      page_size: pageSize.value,
      role: filterRole.value || undefined,
      status: filterStatus.value || undefined,
    })
    tableData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载账号列表失败')
  }
}

const loadRoles = async () => {
  try {
    roleOptions.value = await getRoleList()
  } catch {
    ElMessage.error('加载角色列表失败')
  }
}

const loadDepts = async () => {
  try {
    deptOptions.value = await getDeptList()
  } catch {
    // ignore
  }
}

const handleSearch = () => {
  page.value = 1
  loadData()
}
const handleReset = () => {
  filterRole.value = ''
  filterStatus.value = ''
  page.value = 1
  loadData()
}

const resetForm = () => {
  formData.value = { username: '', password: '', role: '', dept: '', status: 'active' }
  editingId.value = null
}
const openAddDialog = () => {
  formMode.value = 'add'
  resetForm()
  formVisible.value = true
}
const openEditDialog = (row: UserListItem) => {
  formMode.value = 'edit'
  editingId.value = row.id
  formData.value = {
    username: row.username,
    password: '',
    role: row.role,
    dept: row.dept || '',
    status: row.status,
  }
  formVisible.value = true
}

const handleSubmit = async () => {
  if (!formData.value.username.trim() || !formData.value.role) {
    ElMessage.warning('用户名和角色不能为空')
    return
  }
  if (formMode.value === 'add' && !formData.value.password.trim()) {
    ElMessage.warning('请输入初始密码')
    return
  }
  submitting.value = true
  try {
    if (formMode.value === 'add') {
      await createUser({
        username: formData.value.username.trim(),
        password: formData.value.password,
        role: formData.value.role,
        dept: formData.value.dept || undefined,
        status: formData.value.status,
      })
      ElMessage.success('账号创建成功')
    } else {
      await updateUser(editingId.value!, {
        role: formData.value.role,
        dept: formData.value.dept || undefined,
        status: formData.value.status,
      })
      ElMessage.success('账号已更新')
    }
    formVisible.value = false
    loadData()
  } catch {
    ElMessage.error(formMode.value === 'add' ? '创建失败，用户名可能已存在' : '更新失败')
  } finally {
    submitting.value = false
  }
}

const handleToggleStatus = async (row: UserListItem, newStatus: string) => {
  try {
    await updateUser(row.id, { status: newStatus })
    ElMessage.success(newStatus === 'active' ? '已启用' : '已禁用')
    loadData()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: UserListItem) => {
  try {
    await ElMessageBox.confirm(`确认删除账号 "${row.username}"？删除后不可恢复。`, '删除确认', {
      type: 'info',
    })
  } catch {
    return
  }
  try {
    await deleteUser(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

const resetResetForm = () => {
  resetPwdForm.value = { userId: 0, username: '', newPassword: '' }
}
const openResetDialog = (row: UserListItem) => {
  resetPwdForm.value = { userId: row.id, username: row.username, newPassword: '' }
  resetVisible.value = true
}

const handleResetPassword = async () => {
  if (!resetPwdForm.value.newPassword.trim()) {
    ElMessage.warning('请输入新密码')
    return
  }
  resetting.value = true
  try {
    await resetPassword(resetPwdForm.value.userId, resetPwdForm.value.newPassword)
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch {
    ElMessage.error('重置失败')
  } finally {
    resetting.value = false
  }
}

onMounted(() => {
  loadRoles()
  loadDepts()
  loadData()
})
</script>

<style scoped>
.account-wrap {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #f8fafc;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.kpi-card {
  transition: transform 0.2s;
  height: 100%;
}
.kpi-card:hover {
  border-color: #cbd5e1 !important;
}
.kpi-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #f1f5f9;
  color: #1677ff;
}
.kpi-num {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}
.kpi-label {
  font-size: 13px;
  color: #bfbfbf;
  margin-top: 4px;
}

.full-card {
  display: flex;
  flex-direction: column;
}
:deep(.el-card__body) {
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.card-body-inner {
  display: flex;
  flex-direction: column;
}
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.filter-bar {
  margin: 12px 0;
  display: flex;
  align-items: center;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}
.user-name {
  font-weight: 500;
  color: #0f172a;
}
.user-id {
  font-size: 12px;
  color: #bfbfbf;
}
</style>
