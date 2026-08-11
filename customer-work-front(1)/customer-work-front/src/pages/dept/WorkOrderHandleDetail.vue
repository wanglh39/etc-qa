<template>
  <div class="dept-detail-page">
    <el-card shadow="hover">
      <template #header>
        <div class="header-wrap">
          <!-- 返回按钮 -->
          <el-button text @click="$router.back()">
            &lt; 返回{{ deptName }}工单列表
          </el-button>
          <span class="page-title">{{ deptName }}工单详情</span>
        </div>
      </template>

      <!-- 工单基础信息 -->
      <el-descriptions border :column="2" style="margin-bottom:24px">
        <el-descriptions-item label="工单ID">{{ orderInfo.id }}</el-descriptions-item>
        <el-descriptions-item label="工单编号">{{ orderInfo.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ orderInfo.createTime }}</el-descriptions-item>
        <el-descriptions-item label="工单状态">
          <el-tag v-if="orderInfo.status === 'pending'" type="warning">待处理</el-tag>
          <el-tag v-else-if="orderInfo.status === 'handling'" type="primary">处理中</el-tag>
          <el-tag v-else-if="orderInfo.status === 'finish'" type="success">已完成</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="用户问题描述" :span="2">
          {{ orderInfo.question }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 处理备注区域 -->
      <div class="remark-area">
        <h4 style="margin:0 0 8px 0;">处理备注</h4>
        
        <!-- 【重点修复】这里使用了 :rows="5" 而不是 rows="5" -->
        <!-- 加上冒号后，Vue会将 "5" 解析为数字类型，从而消除控制台警告 -->
        <el-input
          v-model="remarkText"
          type="textarea"
          :rows="5"
          placeholder="请填写工单处理过程、解决方案"
        />
      </div>

      <!-- 底部操作按钮 -->
      <div class="btn-box">
        <el-button type="primary" @click="saveRemark">保存备注</el-button>
        <el-button type="success" @click="handleFinish">办结工单</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

// 和列表页完全统一的部门映射
const deptNameMap: Record<string, string> = {
  aftersale: '售后处理部',
  ops: '技术运维部',
  finance: '财务部',
  market: '市场部',
  human: '人事部'
}

// 路由参数
const deptCode = computed(() => route.params.deptCode as string)
const orderId = computed(() => route.params.orderId as string)
const deptName = computed(() => deptNameMap[deptCode.value] || '通用部门')

// 工单详情数据
const orderInfo = ref<any>({})
// 备注文本
const remarkText = ref('')

// 请求工单详情
const getOrderDetail = async () => {
  console.log('加载详情 部门编码:', deptCode.value, '工单ID:', orderId.value)
  
  // 模拟后端接口返回
  // 实际开发中请替换为 axios.get(...)
  orderInfo.value = {
    id: orderId.value,
    orderNo: `CR2026071700${orderId.value}`,
    createTime: '2026-07-17 10:20:00',
    status: 'handling',
    question: '用户反馈更换手机号后收不到验证码，尝试多次依然失败，请协助处理。',
    remark: '' // 假设初始没有备注
  }
  remarkText.value = orderInfo.value.remark
}

// 保存处理备注
const saveRemark = () => {
  if (!remarkText.value.trim()) {
    ElMessage.warning('请输入备注内容')
    return
  }
  // 模拟保存接口
  setTimeout(() => {
    ElMessage.success('处理备注保存成功')
  }, 300)
}

// 办结工单并返回列表
const handleFinish = () => {
  if (!remarkText.value.trim()) {
    ElMessage.warning('办结前请先填写处理备注')
    return
  }
  
  ElMessage.success('工单办结完成，自动返回列表页')
  // 模拟办结请求...
  setTimeout(() => {
    router.back()
  }, 500)
}

onMounted(() => {
  getOrderDetail()
})
</script>

<style scoped>
.dept-detail-page {
  width: 100%;
}
.header-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.page-title {
  font-size: 16px;
  font-weight: 500;
}
.remark-area {
  margin-bottom: 20px;
}
.btn-box {
  text-align: right;
  margin-top: 16px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>