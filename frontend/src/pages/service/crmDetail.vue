<template>
  <div class="crm-detail-page">
    <div class="page-header">
      <el-button @click="$router.back()" icon="ArrowLeft">返回我的待办工单列表</el-button>
      <h2>业务部门工单处理回复页</h2>
    </div>

    <!-- 只读：客服发起工单原始信息（业务部门仅查看，不可编辑） -->
    <el-card title="【客服发起工单原始信息】" class="info-card">
      <el-descriptions border :column="2">
        <el-descriptions-item label="发起客服ID">{{ orderInfo.serviceId }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ orderInfo.customerName }}</el-descriptions-item>
        <el-descriptions-item label="客户手机号">{{ orderInfo.phone }}</el-descriptions-item>
        <el-descriptions-item label="问题分类">{{ getTypeName(orderInfo.problemType) }}</el-descriptions-item>
        <el-descriptions-item label="转交本处理部门">{{ getDeptName(orderInfo.nextDept) }}</el-descriptions-item>
        <el-descriptions-item label="处理完成后回流部门">{{ getDeptName(orderInfo.returnDept) }}</el-descriptions-item>
        <el-descriptions-item label="指定处理人">{{ orderInfo.receiveUser }}</el-descriptions-item>
        <el-descriptions-item label="工单优先级">{{ getPriorityText(orderInfo.priority) }}</el-descriptions-item>
        <el-descriptions-item label="客户原始问题描述" span="2">
          {{ orderInfo.detailDesc }}
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

      <el-form-item label="工单当前状态">
        <el-tag type="primary">待本部门处理回复</el-tag>
      </el-form-item>

      <el-form-item>
        <!-- 业务部门提交回复，办结回流 -->
        <el-button type="success" @click="completeAndReturn">提交处理回复，工单回流指定部门</el-button>
        <el-button @click="saveDraft">保存回复草稿</el-button>
        <el-button @click="$router.back()">取消，返回列表</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElForm } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const handleFormRef = ref<InstanceType<typeof ElForm>>()

// 只读：客服创建的工单原始数据
const orderInfo = ref({
  serviceId: '',
  customerName: '',
  phone: '',
  problemType: '',
  nextDept: '',
  returnDept: '',
  receiveUser: '',
  priority: '',
  detailDesc: ''
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
  const orderId = route.query.id
  console.log('当前工单ID：', orderId)
  // 后端接口：根据工单id获取客服提交的完整工单数据
  // const res = await api.getOrderDetail(orderId)
  // orderInfo.value = res.data

  // 模拟客服提交的数据，和crmCreate填写内容对应
  orderInfo.value = {
    serviceId: 'KF001',
    customerName: '张先生',
    phone: '13800138000',
    problemType: 'consult',
    nextDept: 'after_sale',
    returnDept: 'service',
    receiveUser: 'SH003',
    priority: 'mid',
    detailDesc: '客户咨询产品退换货流程，需要售后部门对接处理。'
  }
}

// 业务部门提交回复，工单回流
const completeAndReturn = async () => {
  if (!handleFormRef.value) return
  await handleFormRef.value.validate(async valid => {
    if (!valid) return

    const submitParams = {
      orderId: route.query.id,
      handleRemark: handleForm.value.handleRemark,
      backDept: orderInfo.value.returnDept,
      operateType: 'dept_reply_complete'
    }
    console.log('业务部门回复提交参数', submitParams)

    ElMessage.success('处理回复提交成功，工单已自动回流至预设部门')
    // 修复：把错误路径 /service/crmList 改为路由配置里正确的 /crm/list
    setTimeout(() => {
      router.push('/crm/list')
    }, 1200)
  })
}

// 保存回复草稿
const saveDraft = () => {
  console.log('保存部门回复草稿', handleForm.value.handleRemark)
  ElMessage.info('处理回复草稿已保存')
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
    pre_sale: '售前咨询部',
    after_sale: '售后处理部',
    tech: '技术运维部',
    complaint_dept: '投诉专员部'
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
