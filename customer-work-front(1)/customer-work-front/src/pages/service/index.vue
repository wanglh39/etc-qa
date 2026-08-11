<template>
  <PageLayout page-title="客服接待工作台">
    <!-- 顶部操作按钮 -->
    <div class="top-btn-group">
      <el-button type="primary" size="small" @click="handleAdopt">一键采用AI回复</el-button>
      <el-button size="small" @click="editDialog = true">修改答复</el-button>
      <el-button type="warning" size="small" @click="markInvalid">标记无效回答</el-button>
      <el-button type="danger" size="small" @click="createCRMOrder">创建CRM工单</el-button>
    </div>

    <el-row :gutter="20" style="margin-top:16px" align="flex-start">
      <!-- 左侧用户列表 -->
      <el-col :span="4">
        <el-card shadow="never">
          <template #header>在线用户</template>
          <el-table :data="userList" highlight-current-row @row-click="handleRowClick">
            <el-table-column prop="userId" label="用户ID" />
          </el-table>
        </el-card>
      </el-col>
      
      <!-- 中间对话内容区 -->
      <el-col :span="20">
        <el-card shadow="never">
          <div v-if="!curUser" class="empty-placeholder">
            点击左侧用户查看咨询内容
          </div>
          <div v-else style="padding:16px">
            <h4>用户：{{ curUser.userId }}</h4>
            <p style="margin:8px 0;color:#666">用户原始问题：{{ curUser.question }}</p >
            <el-input v-model="aiReply" type="textarea" rows="8" placeholder="AI自动生成回复，可编辑修改"/>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 修改答复弹窗 -->
    <el-dialog v-model="editDialog" title="编辑回复内容" width="550px">
      <el-input v-model="aiReply" type="textarea" rows="10"/>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="editDialog = false">保存修改</el-button>
      </template>
    </el-dialog>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/layout/PageLayout.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 路由实例
const router = useRouter()

// 统一定义接口类型
interface UserItem {
  userId: string
  question: string
}

// 用户列表 mock，显式指定泛型类型
const userList = ref<UserItem[]>([
  { userId: 'C001', question: '质保时间多久？' },
  { userId: 'C002', question: '如何办理退货？' },
  { userId: 'C003', question: '发票怎么开具？' }
])

// 当前选中用户，使用 UserItem 类型
const curUser = ref<UserItem | null>(null)

const aiReply = ref('')
const editDialog = ref(false)

// 提取点击事件，显式声明 row 的类型为 UserItem
const handleRowClick = (row: UserItem) => {
  curUser.value = row
}

// 一键采纳回复
const handleAdopt = () => {
  if (!curUser.value) return ElMessage.warning('请先选择用户')
  ElMessage.success('已发送回复给用户')
}

// 标记无效
const markInvalid = async () => {
  if (!curUser.value) return ElMessage.warning('请先选择用户')
  await ElMessageBox.confirm('确认当前AI回复无效？')
  aiReply.value = ''
  ElMessage.success('已标记无效')
}

// 创建CRM工单：新增跳转至新建工单页面
const createCRMOrder = () => {
  if (!curUser.value) return ElMessage.warning('请先选择用户')
  ElMessage.success(`已为用户${curUser.value.userId}跳转至工单创建页面`)
  // 修复：使用路由name跳转，避免路径写错
  router.push({
    name: 'CrmCreate'
  })
}
</script>

<style scoped>
.top-btn-group {
  display: flex;
  gap: 12px;
  padding: 10px 14px;
  background: #f5f7fa;
  border-radius: 6px;
}

/* 空状态样式 */
.empty-placeholder {
  text-align: center;
  padding: 80px 0;
  color: #909399;
}

/* 表格行鼠标指针 */
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
