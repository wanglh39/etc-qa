<template>
  <div class="impersonate-page">
    <el-alert
      title="模拟登录说明"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 20px"
    >
      选择目标角色后，系统将以该角色身份登录。顶部会显示橙色提示栏，可随时退出模拟返回超管身份。所有模拟操作会记录到操作日志。
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
            <div class="card-title">{{ target.label }}</div>
            <div class="card-sub">{{ target.desc }}</div>
          </div>
        </div>

        <div class="card-body">
          <div class="perm-preview">
            <div class="perm-label">可访问页面：</div>
            <div class="perm-list">
              <el-tag v-for="perm in target.permissions" :key="perm" size="small" effect="plain" style="margin: 2px">
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Monitor, Service, Ticket, Location } from '@element-plus/icons-vue'
import { impersonate } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref('')

const targets = [
  {
    role: 'admin', label: '业务管理员', desc: '审核+知识库+分类+配置',
    home: '/workbench/admin/dashboard', icon: Setting,
    gradient: 'linear-gradient(135deg, #409eff, #337ecc)',
    permissions: ['数据看板', '待审核', '审核历史', '知识库', '分类管理', '配置']
  },
  {
    role: 'ops', label: '运维工程师', desc: '看板+状态+监控+告警',
    home: '/workbench/admin/status', icon: Monitor,
    gradient: 'linear-gradient(135deg, #67c23a, #5daf34)',
    permissions: ['数据看板', '系统状态', '性能监控', '定时任务', '异常告警']
  },
  {
    role: 'service', label: '客服', desc: '客服工作台',
    home: '/service', icon: Service,
    gradient: 'linear-gradient(135deg, #e6a23c, #d48806)',
    permissions: ['客服工作台', '工单创建', '工单列表']
  },
  {
    role: 'dept', label: '部门处理员', desc: '工单处理',
    home: '/dept/handle/aftersale', icon: Ticket,
    gradient: 'linear-gradient(135deg, #909399, #7e8c9a)',
    permissions: ['工单处理', '工单详情']
  },
]

const doImpersonate = async (targetRole: string) => {
  loading.value = targetRole
  try {
    const res = await impersonate(targetRole)
    authStore.startImpersonation(res.access_token, res.role, res.dept, res.username)
    ElMessage.success(`已切换为${targets.find(t => t.role === targetRole)?.label}身份`)
    router.replace(targets.find(t => t.role === targetRole)?.home ?? '/')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail ?? '模拟登录失败')
  } finally {
    loading.value = ''
  }
}
</script>

<style scoped>
.impersonate-page {
  padding: 20px;
  min-height: 100vh;
  background-color: #f0f2f5;
  box-sizing: border-box;
}

.role-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.role-card {
  overflow: hidden;
  transition: transform 0.2s;
}
.role-card:hover {
  transform: translateY(-4px);
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
  border-radius: 12px;
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
  color: #909399;
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
  border-top: 1px solid #ebeef5;
}
.home-info {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
