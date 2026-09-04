<template>
  <div class="login-wrap">
    <div class="brand-area">
      <div class="brand-logo">
        <img src="/huawei-logo.svg" alt="华为" />
      </div>
      <div class="brand-text">
        <h1 class="brand-title">挑战杯揭榜挂帅华为赛题</h1>
        <p class="brand-subtitle">客服工单流转系统优化</p>
      </div>
    </div>

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
          <el-input v-model="loginForm.username" placeholder="账号" :prefix-icon="User" clearable />
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

    <div class="footer-text">© 2026 客服工单流转系统优化 · 挑战杯揭榜挂帅华为赛题</div>
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
    const detail = err?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '登录失败，请检查账号密码')
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
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
}

.brand-area {
  position: absolute;
  top: 48px;
  left: 64px;
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 2;
}

.brand-logo img {
  width: 60px;
  height: auto;
  display: block;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.brand-title {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  letter-spacing: 0.02em;
  line-height: 1.3;
}

.brand-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0;
  letter-spacing: 0.04em;
}

.login-form-box {
  width: 400px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 12px;
  padding: 48px 40px;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.3),
    0 4px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 1;
}

.form-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
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

.login-btn:hover,
.login-btn:focus {
  opacity: 0.9;
}

.footer-text {
  position: absolute;
  bottom: 32px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  z-index: 2;
}
</style>
