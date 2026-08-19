<template>
  <div class="login-wrap">
    <div class="login-left">
      <div class="brand-logo">
        <el-icon :size="32"><Headset /></el-icon>
      </div>
      <h1 class="brand-title">智能客服话术系统</h1>
      <p class="brand-desc">AI 驱动的企业级客服辅助平台</p>
      <div class="brand-features">
        <div class="feature-item" v-for="f in features" :key="f.name">
          <el-icon :size="16"><component :is="f.icon" /></el-icon>
          <span>{{ f.name }}</span>
        </div>
      </div>
      <div class="brand-footer">ETC 客服系统 v2.0 · 2026 挑战杯参赛作品</div>
    </div>

    <div class="login-right">
      <div class="login-form-box">
        <h2 class="form-title">欢迎登录</h2>
        <p class="form-sub">请输入您的账号信息</p>

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
import { getDefaultPath } from '@/router'

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
      router.push(getDefaultPath(res.role))
      loading.value = false
    }, 300)
  } catch (err: any) {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  width: 100vw;
  height: 100vh;
  display: flex;
  background: #F8FAFC;
}

.login-left {
  width: 45%;
  background: #0F172A;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
}
.brand-logo {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 20px;
}
.brand-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 6px;
  letter-spacing: -0.02em;
}
.brand-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0 0 40px;
}
.brand-features {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 40px;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
}
.brand-footer {
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
  position: absolute;
  bottom: 24px;
}

.login-right {
  width: 55%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.login-form-box {
  width: 100%;
  max-width: 340px;
}
.form-title {
  font-size: 22px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 4px;
  letter-spacing: -0.02em;
}
.form-sub {
  font-size: 14px;
  color: #64748B;
  margin: 0 0 28px;
}

.login-btn {
  width: 100%;
  height: 42px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 6px;
}

.quick-login {
  margin-top: 20px;
  border-top: 1px solid #E2E8F0;
  padding-top: 16px;
}
.quick-label {
  font-size: 12px;
  color: #94A3B8;
  display: block;
  margin-bottom: 8px;
}
.quick-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.quick-btn {
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid #E2E8F0;
  background: #fff;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.quick-btn:hover {
  border-color: #CBD5E1;
  background: #F8FAFC;
  color: #0F172A;
}

@media (max-width: 768px) {
  .login-left {
    display: none;
  }
  .login-right {
    width: 100%;
  }
}
</style>
