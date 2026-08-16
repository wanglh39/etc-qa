<template>
  <div class="login-container">
    <el-card class="login-card" shadow="hover">
      <h2 class="title">客服话术系统</h2>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        label-width="70px"
        size="large"
        :rules="loginRules"
        class="login-form"
      >
        <el-form-item label="账号" prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入账号" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item class="login-btn-wrapper">
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { login as loginApi } from '@/api/auth'

const router = useRouter()
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

    sessionStorage.setItem('token', res.access_token)
    sessionStorage.setItem('userRole', res.role)
    sessionStorage.setItem('userDept', res.dept)

    ElMessage.success('登录成功')

    setTimeout(() => {
      if (res.role === 'superadmin') {
        router.push('/workbench/admin/dashboard')
      } else if (res.role === 'admin') {
        router.push('/workbench/admin/auditList')
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
  align-items: center;
  justify-content: center;
  background-color: #f5f7fa;
}

.login-card {
  width: 480px;
  max-width: 90%;
  padding: 36px 40px 24px;
  box-sizing: border-box;
}

.title {
  text-align: center;
  margin: 0 0 32px;
  color: #303133;
  font-size: 22px;
  font-weight: 600;
}

.login-btn-wrapper {
  margin-top: 14px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}
</style>