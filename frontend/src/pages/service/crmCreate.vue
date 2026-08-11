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
        <el-input v-model="formData.serviceId" placeholder="输入当前客服工号"></el-input>
      </el-form-item>

      <el-form-item label="客户名称" prop="customerName">
        <el-input v-model="formData.customerName" placeholder="填写客户称呼"></el-input>
      </el-form-item>

      <el-form-item label="客户联系电话" prop="phone">
        <el-input v-model="formData.phone" placeholder="输入客户手机号码"></el-input>
      </el-form-item>

      <el-form-item label="客户问题分类" prop="problemType">
        <el-select v-model="formData.problemType" placeholder="挑选问题分类" style="width:100%">
          <el-option label="产品咨询" value="consult"></el-option>
          <el-option label="售后退换" value="refund"></el-option>
          <el-option label="系统故障" value="fault"></el-option>
          <el-option label="投诉建议" value="complaint"></el-option>
        </el-select>
      </el-form-item>

      <!-- 客服指定：流转给哪个业务部门处理 -->
      <el-form-item label="转交处理部门" prop="nextDept">
        <el-select v-model="formData.nextDept" placeholder="选择需要处理的部门" style="width:100%">
          <el-option label="售前咨询部" value="pre_sale"></el-option>
          <el-option label="售后处理部" value="after_sale"></el-option>
          <el-option label="技术运维部" value="tech"></el-option>
          <el-option label="投诉专员部" value="complaint_dept"></el-option>
        </el-select>
      </el-form-item>

      <!-- 客服指定：业务处理完成后，工单回流到哪个部门 -->
      <el-form-item label="办结回流部门" prop="returnDept">
        <el-select v-model="formData.returnDept" placeholder="业务处理完毕退回部门" style="width:100%">
          <el-option label="客服接待部" value="service"></el-option>
          <el-option label="售前咨询部" value="pre_sale"></el-option>
          <el-option label="售后处理部" value="after_sale"></el-option>
          <el-option label="技术运维部" value="tech"></el-option>
          <el-option label="投诉专员部" value="complaint_dept"></el-option>
        </el-select>
      </el-form-item>

      <!-- 客服指定：对应部门处理人 -->
      <el-form-item label="指定处理人员" prop="receiveUser">
        <el-input v-model="formData.receiveUser" placeholder="填写对应部门处理员工号/姓名"></el-input>
      </el-form-item>

      <el-form-item label="工单优先级" prop="priority">
        <el-radio-group v-model="formData.priority">
          <el-radio value="low">低</el-radio>
          <el-radio value="mid">中等</el-radio>
          <el-radio value="high">紧急</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="客户原始问题描述" prop="detailDesc">
        <el-input v-model="formData.detailDesc" type="textarea" :rows="6" placeholder="完整记录客户诉求、沟通情况"></el-input>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="submitWorkOrder">提交工单，转交对应部门处理</el-button>
        <el-button @click="resetWorkForm">重置表单</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElForm } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const formRef = ref<InstanceType<typeof ElForm>>()

// 客服发起工单完整数据
const formData = ref({
  serviceId: '',
  customerName: '',
  phone: '',
  problemType: '',
  nextDept: '',      // 转交处理部门（业务部门）
  returnDept: '',    // 业务处理完成后回流部门
  receiveUser: '',   // 业务部门处理人
  priority: 'mid',
  detailDesc: ''     // 客户原始问题
})

const formRules = ref({
  serviceId: [{ required: true, message: '请填写发起客服ID', trigger: 'blur' }],
  customerName: [{ required: true, message: '客户名称不能为空', trigger: 'blur' }],
  phone: [
    { required: true, message: '手机号必填', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式有误', trigger: 'blur' }
  ],
  problemType: [{ required: true, message: '需要选择问题分类', trigger: 'change' }],
  nextDept: [{ required: true, message: '请选择转交处理部门', trigger: 'change' }],
  returnDept: [{ required: true, message: '请选择办结回流部门', trigger: 'change' }],
  receiveUser: [{ required: true, message: '请填写处理人员', trigger: 'blur' }],
  detailDesc: [{ required: true, message: '填写客户问题详情', trigger: 'blur' }]
})

// 客服提交工单：提交后跳转工单详情（给业务部门处理的页面）
const submitWorkOrder = async () => {
  if (!formRef.value) return
  await formRef.value.validate((isPass: boolean) => {
    if (isPass) {
      console.log('客服发起工单数据', formData.value)
      ElMessage.success('工单已提交，转交对应业务部门处理，即将跳转工单详情')
      setTimeout(() => {
        // 真实项目替换为后端接口返回的工单id，这里模拟id=1
        const workOrderId = 1
        // 修复：使用路由name跳转，自动匹配 /crm/detail
        router.push({
          name: 'CrmDetail',
          query: { id: workOrderId }
        })
      }, 1100)
    } else {
      ElMessage.warning('请完善全部必填信息后再提交')
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