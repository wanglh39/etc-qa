<template>
  <div class="impersonate-page">
    <el-alert
      title="模拟登录说明"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 20px"
    >
      选择目标角色后，系统将以该角色身份登录。顶部会显示提示栏，可随时退出模拟返回超管身份。所有模拟操作会记录到操作日志。
    </el-alert>

    <div class="role-cards">
      <el-card v-for="target in targets" :key="target.role" class="role-card" shadow="hover">
        <div class="card-top" :style="{ background: target.gradient }">
          <div class="card-icon">
            <el-icon :size="32">
              <component :is="target.icon" />
            </el-icon>
          </div>
          <div class="card-title-area">
            <div class="card-title">
              {{ target.label }}
            </div>
            <div class="card-sub">
              {{ target.desc }}
            </div>
          </div>
        </div>

        <div class="card-body">
          <div class="perm-preview">
            <div class="perm-label">可访问页面：</div>
            <div class="perm-list">
              <el-tag
                v-for="perm in target.permissions"
                :key="perm"
                size="small"
                effect="plain"
                style="margin: 2px"
              >
                {{ perm }}
              </el-tag>
            </div>
          </div>

          <div class="card-footer">
            <div class="home-info">
              <el-icon><Location /></el-icon>
              <span>{{ target.home }}</span>
            </div>
            <el-button
              type="primary"
              :loading="loading === target.role"
              @click="doImpersonate(target.role)"
            >
              模拟登录
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Monitor, Service, Ticket, Location } from '@element-plus/icons-vue'
import { impersonate } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { roleColor } from '@/utils/roleColor'
import { getRoleList, type RoleItem } from '@/api/system'
import { getPageLabel } from '@/config/pages'
import { getDefaultPath } from '@/router'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref('')

const roleIcons: Record<string, any> = {
  admin: Setting,
  ops: Monitor,
  service: Service,
  dept: Ticket,
}
const roleDescs: Record<string, string> = {
  admin: '审核+知识库+分类+配置',
  ops: '状态+监控+告警+定时任务',
  service: '客服工作台',
  dept: '工单处理',
}

const targets = ref<
  {
    role: string
    label: string
    desc: string
    home: string
    icon: any
    gradient: string
    permissions: string[]
  }[]
>([])

const loadRoles = async () => {
  try {
    const roles = await getRoleList()
    targets.value = roles
      .filter((r) => r.role_key !== 'superadmin')
      .map((r) => ({
        role: r.role_key,
        label: r.role_name,
        desc: r.description || roleDescs[r.role_key] || '',
        home: (r.permissions || [])[0] || '/',
        icon: roleIcons[r.role_key] || Setting,
        gradient: roleColor(r.role_key),
        permissions: (r.permissions || []).map((p) => getPageLabel(p)),
      }))
  } catch {
    ElMessage.error('加载角色列表失败')
  }
}

const doImpersonate = async (targetRole: string) => {
  loading.value = targetRole
  try {
    const res = await impersonate(targetRole)
    authStore.startImpersonation(
      res.access_token,
      res.role,
      res.dept,
      res.username,
      res.permissions
    )
    const target = targets.value.find((t) => t.role === targetRole)
    ElMessage.success(`已切换为${target?.label}身份`)
    router.replace(getDefaultPath(res.role))
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? '模拟登录失败')
  } finally {
    loading.value = ''
  }
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.impersonate-page {
  padding: 20px;
  min-height: 100vh;
  background-color: #f8fafc;
  box-sizing: border-box;
}

.role-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.role-card {
  overflow: hidden;
  transition: border-color 0.2s;
}
.role-card:hover {
  border-color: #cbd5e1 !important;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  color: #fff;
  margin: -20px -20px 0 -20px;
}
.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-title {
  font-size: 18px;
  font-weight: 700;
}
.card-sub {
  font-size: 13px;
  opacity: 0.85;
  margin-top: 4px;
}

.card-body {
  padding: 16px 0 0 0;
}

.perm-preview {
  margin-bottom: 16px;
}
.perm-label {
  font-size: 13px;
  color: #bfbfbf;
  margin-bottom: 8px;
}
.perm-list {
  display: flex;
  flex-wrap: wrap;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}
.home-info {
  font-size: 12px;
  color: #bfbfbf;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
