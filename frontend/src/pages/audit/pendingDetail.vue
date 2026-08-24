<template>
  <div class="audit-detail-wrap">
    <el-card shadow="hover">
      <!-- 头部区域 -->
      <div class="header-bar">
        <h3>工单审核详情</h3>
      </div>

      <!-- 详情展示区域 -->
      <el-descriptions border :column="2" style="margin: 20px 0">
        <el-descriptions-item label="知识ID">{{ detailInfo.id }}</el-descriptions-item>

        <el-descriptions-item label="分类">
          {{ detailInfo.category_l1
          }}{{ detailInfo.category_l2 ? ' / ' + detailInfo.category_l2 : '' }}
        </el-descriptions-item>

        <el-descriptions-item label="提交时间">{{
          detailInfo.created_at || '-'
        }}</el-descriptions-item>

        <el-descriptions-item label="状态">
          <el-tag type="info" size="small">待审核</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="用户问题" :span="2">
          <div style="white-space: pre-wrap">{{ detailInfo.question }}</div>
        </el-descriptions-item>

        <el-descriptions-item label="标准答案" :span="2">
          <div v-if="detailInfo.answer" style="white-space: pre-wrap; color: #475569">
            {{ detailInfo.answer }}
          </div>
          <span v-else style="color: #bfbfbf">暂无标准答案，请在下方备注填写</span>
        </el-descriptions-item>

        <el-descriptions-item label="内部流程" :span="2">
          {{ detailInfo.internal_process || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="反馈部门" :span="2">
          {{ detailInfo.feedback_dept || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="处理备注" :span="2">
          <el-input
            v-model="remark"
            type="textarea"
            :rows="4"
            placeholder="请填写入库或驳回的详细备注..."
          />
        </el-descriptions-item>
      </el-descriptions>

      <!-- 底部操作按钮 -->
      <div class="btn-group">
        <el-button type="primary" :loading="loading" @click="handleAudit('pass')">
          确认入库
        </el-button>
        <el-button type="primary" :loading="loading" @click="handleAudit('reject')">
          驳回工单
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getQADetail, updateQAStatus, type QADetailResponse } from '@/api/knowledge'

const route = useRoute()
const router = useRouter()
const remark = ref('')
const loading = ref(false)

const detailInfo = ref<QADetailResponse>({
  id: 0,
  question: '',
  answer: '',
  category_l1: '',
  category_l2: '',
  internal_process: '',
  feedback_dept: '',
  status: '',
  created_at: '',
})

onMounted(async () => {
  const id = Number(route.query.id)
  if (!id) {
    ElMessage.error('缺少工单ID')
    return
  }
  try {
    const res = await getQADetail(id)
    detailInfo.value = res
  } catch {
    ElMessage.error('加载详情失败')
  }
})

const handleAudit = async (action: 'pass' | 'reject') => {
  if (!remark.value.trim()) {
    ElMessage.warning('请先填写处理备注')
    return
  }
  loading.value = true
  try {
    const newStatus = action === 'pass' ? 'active' : 'archived'
    await updateQAStatus(detailInfo.value.id, newStatus)
    ElMessage.success(action === 'pass' ? '入库成功' : '已驳回')
    setTimeout(() => router.back(), 500)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.audit-detail-wrap {
  width: 94%;
  max-width: 1000px;
  margin: 40px auto 0;
}

.header-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}

.header-bar h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.btn-group {
  margin-top: 30px;
  text-align: right;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}
</style>
