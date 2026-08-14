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
        <el-descriptions-item label="工单编号">{{ orderInfo.external_id }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ orderInfo.created_at }}</el-descriptions-item>
        <el-descriptions-item label="工单状态">
          <el-tag v-if="orderInfo.status === 'submitted'" type="warning">待处理</el-tag>
          <el-tag v-else-if="orderInfo.status === 'answered'" type="primary">已回复</el-tag>
          <el-tag v-else-if="orderInfo.status === 'processed'" type="success">已办结</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ orderInfo.customer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户手机号">{{ orderInfo.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="用户问题描述" :span="2">
          {{ orderInfo.detail_desc || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 处理备注区域 -->
      <div class="remark-area">
        <h4 style="margin:0 0 8px 0;">处理备注</h4>
        <el-input
          v-model="remarkText"
          type="textarea"
          :rows="5"
          placeholder="请填写工单处理过程、解决方案"
        />
      </div>

      <!-- 底部操作按钮 -->
      <div class="btn-box">
        <el-button type="success" :loading="submitting" @click="handleFinish">办结工单</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getWorkOrderDetail, replyWorkOrder, type WorkOrderDetail } from '@/api/workorder'

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
const orderInfo = ref<WorkOrderDetail>({
  id: 0,
  external_id: '',
  status: '',
  dept: '',
  service_id: '',
  customer_name: '',
  phone: '',
  problem_type: '',
  next_dept: '',
  priority: '',
  detail_desc: '',
  handle_remark: ''
})
// 备注文本
const remarkText = ref('')
const submitting = ref(false)

// 请求工单详情
const getOrderDetail = async () => {
  const id = Number(orderId.value)
  if (!id) {
    ElMessage.error('缺少工单ID')
    return
  }
  try {
    const res = await getWorkOrderDetail(id)
    orderInfo.value = res
    remarkText.value = res.handle_remark || ''
  } catch {
    ElMessage.error('加载工单详情失败')
  }
}

// 办结工单并返回列表
const handleFinish = async () => {
  if (!remarkText.value.trim()) {
    ElMessage.warning('办结前请先填写处理备注')
    return
  }
  submitting.value = true
  try {
    await replyWorkOrder(orderInfo.value.id, {
      handle_remark: remarkText.value
    })
    ElMessage.success('工单办结完成')
    router.back()
  } catch {
    ElMessage.error('办结失败')
  } finally {
    submitting.value = false
  }
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
