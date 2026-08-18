<template>
  <div class="login-cover">
    <div class="dot-grid"></div>
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>

    <div class="login-content">
      <div class="brand-area">
        <div class="brand-icon">
          <el-icon :size="36"><Headset /></el-icon>
        </div>
        <h1 class="brand-title">智能客服话术系统</h1>
        <p class="brand-sub">AI 驱动的企业级客服辅助平台</p>
      </div>

      <div class="glass-card">
        <h2 class="card-title">欢迎登录</h2>
        <p class="card-sub">请输入您的账号信息</p>

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
              class="dark-input"
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
              class="dark-input"
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
          <span class="quick-label">快速登录（演示）</span>
          <div class="quick-btns">
            <button
              v-for="role in quickRoles"
              :key="role.user"
              class="quick-btn"
              @click="quickFill(role)"
            >
              {{ role.label }}
            </button>
          </div>
        </div>
      </div>

      <div class="feature-row">
        <div class="feature-chip" v-for="f in features" :key="f.name">
          <el-icon :size="16"><component :is="f.icon" /></el-icon>
          <span>{{ f.name }}</span>
        </div>
      </div>

      <div class="footer-text">ETC 客服系统 v2.0 · 2026 挑战杯参赛作品</div>
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

const features = [
  { name: '实时语音识别', icon: Microphone },
  { name: '智能知识检索', icon: Search },
  { name: '全链路可观测', icon: DataLine },
  { name: '五角色权限体系', icon: UserFilled },
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
.login-cover {
  width: 100vw;
  height: 100vh;
  background: #0F172A;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.dot-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 28px 28px;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
}
.glow-1 {
  width: 500px;
  height: 500px;
  background: rgba(0, 82, 255, 0.15);
  top: -15%;
  right: -10%;
}
.glow-2 {
  width: 400px;
  height: 400px;
  background: rgba(77, 124, 255, 0.1);
  bottom: -15%;
  left: -10%;
}

.login-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
  max-width: 440px;
  width: 90%;
}

.brand-area {
  text-align: center;
}
.brand-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: rgba(0, 82, 255, 0.15);
  border: 1px solid rgba(0, 82, 255, 0.3);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4D7CFF;
}
.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 6px;
  letter-spacing: 0.5px;
}
.brand-sub {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.glass-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 32px 36px;
}
.card-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 4px;
}
.card-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0 0 24px;
}

:deep(.dark-input .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
  border-radius: 8px;
}
:deep(.dark-input .el-input__wrapper:hover) {
  border-color: rgba(0, 82, 255, 0.5);
}
:deep(.dark-input .el-input__wrapper.is-focus) {
  border-color: #0052FF;
  box-shadow: 0 0 0 3px rgba(0, 82, 255, 0.15);
}
:deep(.dark-input .el-input__inner) {
  color: #fff;
}
:deep(.dark-input .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.35);
}
:deep(.dark-input .el-input__prefix) {
  color: rgba(255, 255, 255, 0.4);
}
:deep(.dark-input .el-input__suffix) {
  color: rgba(255, 255, 255, 0.4);
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
  border: none;
  background: #0052FF;
}
.login-btn:hover {
  background: #0040CC;
}

.quick-login {
  margin-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 20px;
}
.quick-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  display: block;
  margin-bottom: 10px;
}
.quick-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.quick-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.quick-btn:hover {
  background: rgba(0, 82, 255, 0.15);
  border-color: rgba(0, 82, 255, 0.4);
  color: #fff;
}

.feature-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}
.feature-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.footer-text {
  color: rgba(255, 255, 255, 0.2);
  font-size: 12px;
}
</style>
