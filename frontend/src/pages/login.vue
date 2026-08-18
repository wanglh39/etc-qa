<template>
  <div class="login-container">
    <!-- 左侧品牌面板 -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="brand-logo">
          <el-icon :size="48" color="#fff"><Headset /></el-icon>
        </div>
        <h1 class="brand-title">智能客服话术系统</h1>
        <p class="brand-tagline">AI驱动的企业级客服辅助平台</p>

        <div class="feature-list">
          <div class="feature-item">
            <el-icon :size="22"><Microphone /></el-icon>
            <div>
              <span class="feature-name">实时语音识别</span>
              <span class="feature-desc">流式ASR + 热词纠错，识别率提升30%</span>
            </div>
          </div>
          <div class="feature-item">
            <el-icon :size="22"><Search /></el-icon>
            <div>
              <span class="feature-name">智能知识检索</span>
              <span class="feature-desc">双路召回 + Reranker精排，秒级响应</span>
            </div>
          </div>
          <div class="feature-item">
            <el-icon :size="22"><DataLine /></el-icon>
            <div>
              <span class="feature-name">全链路可观测</span>
              <span class="feature-desc">LangSmith追踪 + 告警监控 + 审计日志</span>
            </div>
          </div>
          <div class="feature-item">
            <el-icon :size="22"><UserFilled /></el-icon>
            <div>
              <span class="feature-name">五角色权限体系</span>
              <span class="feature-desc">超管/运维/业务/客服/部门，RBAC细粒度管控</span>
            </div>
          </div>
        </div>
      </div>
      <div class="brand-footer">
        <span>ETC客服系统 v2.0 · 2026 挑战杯参赛作品</span>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="form-panel">
      <div class="form-wrapper">
        <h2 class="form-title">欢迎登录</h2>
        <p class="form-subtitle">请输入您的账号信息</p>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          label-width="0"
          size="large"
          :rules="loginRules"
          class="login-form"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="账号"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
              clearable
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
              登 录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="quick-login">
          <span class="quick-label">快速登录（演示）：</span>
          <div class="quick-tags">
            <el-tag
              v-for="role in quickRoles"
              :key="role.user"
              class="quick-tag"
              @click="quickFill(role)"
            >
              {{ role.label }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Microphone, Search, DataLine, UserFilled, Headset } from '@element-plus/icons-vue'
import { login as loginApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const quickRoles = [
  { user: 'superadmin', label: '超管', pass: '123456' },
  { user: 'admin', label: '业务管理', pass: '123456' },
  { user: 'ops', label: '运维', pass: '123456' },
  { user: 'service', label: '客服', pass: '123456' },
  { user: 'dept', label: '部门', pass: '123456' },
]

const quickFill = (role: { user: string; pass: string }) => {
  loginForm.username = role.user
  loginForm.password = role.pass
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }

  loading.value = true

  try {
    const res = await loginApi({
      username: loginForm.username,
      password: loginForm.password
    })

    authStore.setAuth(res.access_token, res.role, res.dept, loginForm.username)

    ElMessage.success('登录成功')

    setTimeout(() => {
      if (res.role === 'superadmin') {
        router.push('/workbench/admin/account')
      } else if (res.role === 'ops') {
        router.push('/workbench/admin/status')
      } else if (res.role === 'admin') {
        router.push('/workbench/admin/dashboard')
      } else if (res.role === 'service') {
        router.push('/service')
      } else {
        router.push(`/dept/handle/${res.dept}`)
      }
      loading.value = false
    }, 300)
  } catch (err: any) {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  overflow: hidden;
}

/* 左侧品牌面板 */
.brand-panel {
  flex: 1.2;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.brand-panel::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.15) 0%, transparent 70%);
  border-radius: 50%;
}
.brand-panel::after {
  content: '';
  position: absolute;
  bottom: -30%;
  left: -10%;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(103, 194, 58, 0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.brand-content {
  position: relative;
  z-index: 1;
  padding: 60px 80px;
  max-width: 600px;
}

.brand-logo {
  width: 72px;
  height: 72px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 12px;
  letter-spacing: 1px;
}

.brand-tagline {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 48px;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  color: rgba(255, 255, 255, 0.85);
}
.feature-item .el-icon {
  margin-top: 2px;
  color: #409eff;
  flex-shrink: 0;
}
.feature-item > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.feature-name {
  font-size: 15px;
  font-weight: 600;
}
.feature-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.brand-footer {
  position: absolute;
  bottom: 32px;
  left: 80px;
  z-index: 1;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
}

/* 右侧表单面板 */
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.form-wrapper {
  width: 380px;
  max-width: 90%;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.form-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.form-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 0 0 32px;
}

.login-form {
  margin-bottom: 24px;
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
}

.quick-login {
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}
.quick-label {
  font-size: 13px;
  color: #909399;
  display: block;
  margin-bottom: 10px;
}
.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.quick-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

@media (max-width: 768px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    flex: 1;
  }
}
</style>
