<template>
  <div class="crm-create-page">
    <!-- 仅保留标题，移除了返回按钮 -->
    <div class="page-header">
      <h2>客服发起CRM工单</h2>
    </div>

    <el-form
      ref="formRef"
      :model="formData"
      label-width="140px"
      :rules="formRules"
      class="center-form"
    >
      <!-- 当前操作人：客服ID（当前登录客服自动填充，可手动修改） -->
      <el-form-item label="发起客服ID" prop="serviceId">
        <el-input v-model="formData.serviceId" placeholder="输入当前客服工号" />
      </el-form-item>

      <el-form-item label="客户名称" prop="customerName">
        <el-input v-model="formData.customerName" placeholder="填写客户称呼" />
      </el-form-item>

      <el-form-item label="客户联系电话" prop="phone">
        <el-input v-model="formData.phone" placeholder="输入客户手机号码" />
      </el-form-item>

      <el-form-item label="客户问题分类" prop="problemType">
        <el-select v-model="formData.problemType" placeholder="挑选问题分类" style="width: 100%">
          <el-option label="产品咨询" value="consult" />
          <el-option label="售后退换" value="refund" />
          <el-option label="系统故障" value="fault" />
          <el-option label="投诉建议" value="complaint" />
        </el-select>
      </el-form-item>

      <!-- 客服指定：流转给哪个业务部门处理 -->
      <el-form-item label="转交处理部门" prop="nextDept">
        <el-select v-model="formData.nextDept" placeholder="选择需要处理的部门" style="width: 100%">
          <el-option label="售后处理部" value="aftersale" />
          <el-option label="技术运维部" value="ops" />
          <el-option label="财务部" value="finance" />
          <el-option label="市场部" value="market" />
          <el-option label="人事部" value="human" />
        </el-select>
      </el-form-item>

      <el-form-item label="工单优先级" prop="priority">
        <el-radio-group v-model="formData.priority">
          <el-radio value="low"> 低 </el-radio>
          <el-radio value="mid"> 中等 </el-radio>
          <el-radio value="high"> 紧急 </el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="客户原始问题描述" prop="detailDesc">
        <el-input
          v-model="formData.detailDesc"
          type="textarea"
          :rows="6"
          placeholder="完整记录客户诉求、沟通情况"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submitWorkOrder">
          提交工单，转交对应部门处理
        </el-button>
        <el-button @click="resetWorkForm"> 重置表单 </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElForm } from 'element-plus'
import { useRouter } from 'vue-router'
import { createWorkOrder } from '@/api/workorder'

const router = useRouter()
const formRef = ref<InstanceType<typeof ElForm>>()
const submitting = ref(false)

// 客服发起工单完整数据
const formData = ref({
  serviceId: '',
  customerName: '',
  phone: '',
  problemType: '',
  nextDept: '', // 转交处理部门（业务部门）
  priority: 'mid',
  detailDesc: '', // 客户原始问题
})

const formRules = ref({
  serviceId: [{ required: true, message: '请填写发起客服ID', trigger: 'blur' }],
  customerName: [{ required: true, message: '客户名称不能为空', trigger: 'blur' }],
  phone: [
    { required: true, message: '手机号必填', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式有误', trigger: 'blur' },
  ],
  problemType: [{ required: true, message: '需要选择问题分类', trigger: 'change' }],
  nextDept: [{ required: true, message: '请选择转交处理部门', trigger: 'change' }],
  detailDesc: [{ required: true, message: '填写客户问题详情', trigger: 'blur' }],
})

// 客服提交工单：提交后跳转工单详情（给业务部门处理的页面）
const submitWorkOrder = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (isPass: boolean) => {
    if (!isPass) {
      ElMessage.warning('请完善全部必填信息后再提交')
      return
    }
    submitting.value = true
    try {
      const res = await createWorkOrder({
        service_id: formData.value.serviceId,
        customer_name: formData.value.customerName,
        phone: formData.value.phone,
        problem_type: formData.value.problemType,
        next_dept: formData.value.nextDept,
        priority: formData.value.priority,
        detail_desc: formData.value.detailDesc,
      })
      ElMessage.success('工单已提交，转交对应业务部门处理')
      router.push({ name: 'CrmDetail', query: { id: res.id } })
    } catch {
      ElMessage.error('工单提交失败')
    } finally {
      submitting.value = false
    }
  })
}

const resetWorkForm = () => {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.crm-create-page {
  width: 94%;
  max-width: 900px;
  margin: 40px auto 0;
}
.page-header {
  /* 移除 flex 布局中的 gap，改为简单的底部间距 */
  margin-bottom: 24px;
}
h2 {
  margin: 0;
  font-size: 19px;
  /* 可选：如果你希望标题在去掉按钮后看起来更居中或靠左，可以在此调整 text-align */
}
.center-form {
  width: 100%;
}
</style>
