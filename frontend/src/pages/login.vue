<template>
  <div class="login-wrap">
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="glow glow-3"></div>
    <div class="dot-grid"></div>

    <div class="login-panel">
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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login as loginApi } from '@/api/auth'
import { getMyPermissions } from '@/api/system'
import { useAuthStore } from '@/stores/auth'
import { getDefaultPath } from '@/router'

const router = useRouter()
const authStore = useAuthStore()
const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
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
      password: loginForm.password,
    })

    authStore.setAuth(res.access_token, res.role, res.dept, loginForm.username)

    try {
      const perms = await getMyPermissions()
      authStore.setPermissions(perms)
    } catch {}

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
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
}
.glow-1 {
  width: 500px;
  height: 500px;
  background: #1677ff;
  top: -150px;
  left: -100px;
  opacity: 0.4;
}
.glow-2 {
  width: 400px;
  height: 400px;
  background: #3b82f6;
  bottom: -100px;
  right: -80px;
  opacity: 0.3;
}
.glow-3 {
  width: 300px;
  height: 300px;
  background: #0958d9;
  top: 40%;
  left: 15%;
  opacity: 0.25;
}
.dot-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 28px 28px;
}

.login-panel {
  width: 820px;
  height: 100vh;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
  z-index: 1;
}
.login-form-box {
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 40px 36px;
  box-shadow:
    0 4px 24px rgba(15, 23, 42, 0.08),
    0 1px 2px rgba(15, 23, 42, 0.04);
}
.form-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 6px;
  letter-spacing: -0.02em;
}
.form-sub {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 32px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
}
</style>
