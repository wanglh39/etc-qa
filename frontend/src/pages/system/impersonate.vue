<template>
  <div class="impersonate-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>模拟登录</span>
          <el-tag type="warning" size="small">仅超级管理员可用</el-tag>
        </div>
      </template>

      <el-alert
        title="模拟登录说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        选择目标角色后，系统将以该角色身份登录。顶部会显示橙色提示栏，可随时退出模拟返回超管身份。所有模拟操作会记录到操作日志。
      </el-alert>

      <el-row :gutter="16">
        <el-col :span="6" v-for="target in targets" :key="target.role">
          <el-card class="role-card" shadow="hover">
            <div class="role-icon">
              <el-icon :size="40" :color="target.color">
                <component :is="target.icon" />
              </el-icon>
            </div>
            <div class="role-name">{{ target.label }}</div>
            <div class="role-desc">{{ target.desc }}</div>
            <div class="role-home">首页: {{ target.home }}</div>
            <el-button
              type="primary"
              plain
              style="width: 100%; margin-top: 12px"
              :loading="loading === target.role"
              @click="doImpersonate(target.role)"
            >
              模拟登录
            </el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Monitor, Service, Ticket } from '@element-plus/icons-vue'
import { impersonate } from '@/api/auth'

const router = useRouter()
const loading = ref('')

const targets = [
  { role: 'admin', label: '业务管理员', desc: '审核+知识库+分类+配置', home: '/workbench/admin/dashboard', icon: Setting, color: '#409EFF' },
  { role: 'ops', label: '运维工程师', desc: '看板+状态+监控+告警', home: '/workbench/admin/status', icon: Monitor, color: '#67C23A' },
  { role: 'service', label: '客服', desc: '客服工作台', home: '/service', icon: Service, color: '#E6A23C' },
  { role: 'dept', label: '部门处理员', desc: '工单处理', home: '/dept/handle/aftersale', icon: Ticket, color: '#F56C6C' },
]

const doImpersonate = async (targetRole: string) => {
  loading.value = targetRole
  try {
    const res = await impersonate(targetRole)
    sessionStorage.setItem('impersonator_token', sessionStorage.getItem('token') ?? '')
    sessionStorage.setItem('impersonator_role', 'superadmin')
    sessionStorage.setItem('token', res.access_token)
    sessionStorage.setItem('userRole', res.role)
    sessionStorage.setItem('userName', res.username)
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
  padding: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.role-card {
  text-align: center;
  padding: 8px;
}
.role-icon {
  margin: 12px 0;
}
.role-name {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 4px;
}
.role-desc {
  font-size: 12px;
  color: #999;
  margin-bottom: 2px;
}
.role-home {
  font-size: 11px;
  color: #c0c4cc;
}
</style>