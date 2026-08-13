<template>
  <div class="crm-detail-page">
    <div class="page-header">
      <el-button @click="$router.back()" icon="ArrowLeft">返回我的待办工单列表</el-button>
      <h2>业务部门工单处理回复页</h2>
    </div>

    <!-- 只读：客服发起工单原始信息（业务部门仅查看，不可编辑） -->
    <el-card title="【客服发起工单原始信息】" class="info-card">
      <el-descriptions border :column="2">
        <el-descriptions-item label="发起客服ID">{{ orderInfo.service_id }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ orderInfo.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="客户手机号">{{ orderInfo.phone }}</el-descriptions-item>
        <el-descriptions-item label="问题分类">{{ getTypeName(orderInfo.problem_type) }}</el-descriptions-item>
        <el-descriptions-item label="转交本处理部门">{{ getDeptName(orderInfo.next_dept) }}</el-descriptions-item>
        <el-descriptions-item label="处理完成后回流部门">{{ getDeptName(orderInfo.return_dept) }}</el-descriptions-item>
        <el-descriptions-item label="指定处理人">{{ orderInfo.receive_user }}</el-descriptions-item>
        <el-descriptions-item label="工单优先级">{{ getPriorityText(orderInfo.priority) }}</el-descriptions-item>
        <el-descriptions-item label="客户原始问题描述" span="2">
          {{ orderInfo.detail_desc }}
        </el-descriptions-item>
        <el-descriptions-item label="工单状态" span="2">
          <el-tag :type="statusType(orderInfo.status)">{{ statusText(orderInfo.status) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 可编辑：业务部门填写回复、处理方案 -->
    <el-form
      ref="handleFormRef"
      :model="handleForm"
      label-width="140px"
      class="reply-form"
      :rules="handleRules"
    >
      <el-form-item label="业务部门处理回复" prop="handleRemark">
        <el-input
          v-model="handleForm.handleRemark"
          type="textarea"
          :rows="5"
          placeholder="填写本部门处理方案、对客户问题的回复（必填）"
        />
      </el-form-item>

      <el-form-item>
        <!-- 业务部门提交回复，办结回流 -->
        <el-button type="success" :loading="submitting" @click="completeAndReturn">
          提交处理回复，工单回流指定部门
        </el-button>
        <el-button @click="$router.back()">取消，返回列表</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElForm } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { getWorkOrderDetail, replyWorkOrder, type WorkOrderDetail } from '@/api/workorder'

const route = useRoute()
const router = useRouter()
const handleFormRef = ref<InstanceType<typeof ElForm>>()
const submitting = ref(false)

// 只读：客服创建的工单原始数据
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
  return_dept: '',
  receive_user: '',
  priority: '',
  detail_desc: '',
  handle_remark: ''
})

// 业务部门填写的回复内容
const handleForm = ref({
  handleRemark: ''
})

// 回复必填校验
const handleRules = ref({
  handleRemark: [{ required: true, message: '请填写本部门处理回复后再提交回流', trigger: 'blur' }]
})

// 页面加载：根据路由id读取客服创建的工单数据
const loadOrderData = async () => {
  const orderId = Number(route.query.id)
  if (!orderId) {
    ElMessage.error('缺少工单ID')
    return
  }
  try {
    const res = await getWorkOrderDetail(orderId)
    orderInfo.value = res
    handleForm.value.handleRemark = res.handle_remark || ''
  } catch {
    ElMessage.error('加载工单详情失败')
  }
}

// 业务部门提交回复，工单回流
const completeAndReturn = async () => {
  if (!handleFormRef.value) return
  await handleFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    submitting.value = true
    try {
      await replyWorkOrder(orderInfo.value.id, {
        handle_remark: handleForm.value.handleRemark,
        back_dept: orderInfo.value.return_dept
      })
      ElMessage.success('处理回复提交成功，工单已自动回流至预设部门')
      router.push('/crm/list')
    } catch {
      ElMessage.error('提交处理回复失败')
    } finally {
      submitting.value = false
    }
  })
}

// 文字转换工具
const getTypeName = (val: string) => {
  const map: Record<string, string> = {
    consult: '产品咨询',
    refund: '售后退换',
    fault: '系统故障',
    complaint: '投诉建议'
  }
  return map[val] || val
}

const getDeptName = (val: string) => {
  const map: Record<string, string> = {
    service: '客服接待部',
    aftersale: '售后处理部',
    ops: '技术运维部',
    finance: '财务部',
    market: '市场部',
    human: '人事部'
  }
  return map[val] || val
}

const getPriorityText = (val: string) => {
  const map: Record<string, string> = {
    low: '低',
    mid: '中等',
    high: '紧急'
  }
  return map[val] || val
}

const statusType = (s: string) => {
  const map: Record<string, string> = {
    submitted: 'info',
    answered: 'warning',
    processed: 'success'
  }
  return map[s] || ''
}

const statusText = (s: string) => {
  const map: Record<string, string> = {
    submitted: '已提交',
    answered: '已回复',
    processed: '已处理'
  }
  return map[s] || s
}

onMounted(() => {
  loadOrderData()
})
</script>

<style scoped>
/* 页面整体居中核心样式 */
.crm-detail-page {
  width: 94%;
  max-width: 1000px;
  margin: 40px auto 0;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 24px;
}
h2 {
  margin: 0;
  font-size: 19px;
}
.info-card {
  width: 100%;
}
.reply-form {
  width: 100%;
  margin-top: 24px;
}
</style>
