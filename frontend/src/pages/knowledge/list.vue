<template>
  <div class="knowledge-list-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <h3>知识库管理</h3>

        <div class="filter-bar">
          <el-input
            v-model="keyword"
            placeholder="关键词检索问题/答案"
            clearable
            style="width: 260px"
            @keyup.enter="handleSearch"
          />
          <el-select
            v-model="filterCategory"
            placeholder="业务分类"
            clearable
            style="width: 160px; margin-left: 12px"
            @change="handleSearch"
          >
            <el-option
              v-for="c in categoryOptions"
              :key="c.label"
              :label="c.label"
              :value="c.label"
            />
          </el-select>
          <el-select
            v-model="filterStatus"
            placeholder="状态"
            clearable
            style="width: 140px; margin-left: 12px"
            @change="handleSearch"
          >
            <el-option label="已上架" value="active" />
            <el-option label="已下架" value="deprecated" />
            <el-option label="已归档" value="archived" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="handleSearch">搜索</el-button>
          <el-button style="margin-left: 8px" @click="handleReset">重置</el-button>
          <el-button type="success" style="margin-left: 24px" @click="openAddDialog">新增知识</el-button>
        </div>

        <div class="btn-group">
          <el-button type="success" @click="batchUpdateStatus('active', '上架')">批量上架</el-button>
          <el-button type="warning" @click="batchUpdateStatus('deprecated', '下架')">批量下架</el-button>
          <el-button type="danger" @click="batchDelete">批量删除</el-button>
        </div>

        <el-table
          border
          :max-height="'calc(100vh - 300px)'"
          :data="tableData"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="question" label="问题内容" min-width="300" show-overflow-tooltip />
          <el-table-column label="答案摘要" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              {{ truncate(row.answer, 40) }}
            </template>
          </el-table-column>
          <el-table-column label="分类" width="120">
            <template #default="{ row }">
              {{ row.category_l1 }}{{ row.category_l2 ? ' / ' + row.category_l2 : '' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="150" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetailDialog(row.id)">查看详情</el-button>
              <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
              <el-button
                v-if="row.status !== 'active'"
                link
                type="success"
                @click="handleToggleStatus(row.id, 'active', '上架')"
              >上架</el-button>
              <el-button
                v-else
                link
                type="warning"
                @click="handleToggleStatus(row.id, 'deprecated', '下架')"
              >下架</el-button>
              <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          style="margin-top: 18px; justify-content: flex-end; display: flex"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="知识详情" width="640px">
      <el-descriptions :column="1" border v-if="detailData">
        <el-descriptions-item label="知识ID">{{ detailData.id }}</el-descriptions-item>
        <el-descriptions-item label="问题内容">{{ detailData.question }}</el-descriptions-item>
        <el-descriptions-item label="标准答案">
          <div style="white-space: pre-wrap">{{ detailData.answer }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="一级分类">{{ detailData.category_l1 }}</el-descriptions-item>
        <el-descriptions-item label="二级分类">{{ detailData.category_l2 }}</el-descriptions-item>
        <el-descriptions-item label="内部流程">
          <div style="white-space: pre-wrap">{{ detailData.internal_process }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="反馈部门">{{ detailData.feedback_dept }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(detailData.status) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detailData.created_at }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ detailData.updated_at }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog
      v-model="formVisible"
      :title="formMode === 'add' ? '新增知识' : '编辑知识'"
      width="640px"
      @closed="resetForm"
    >
      <el-form :model="formData" label-width="90px">
        <el-form-item label="问题内容" required>
          <el-input v-model="formData.question" type="textarea" :rows="3" placeholder="请输入标准化问题" />
        </el-form-item>
        <el-form-item label="标准答案" required>
          <el-input v-model="formData.answer" type="textarea" :rows="5" placeholder="请输入标准解决方案" />
        </el-form-item>
        <el-form-item label="一级分类">
          <el-select v-model="formData.category_l1" placeholder="请选择" clearable style="width: 100%">
            <el-option
              v-for="c in categoryOptions"
              :key="c.label"
              :label="c.label"
              :value="c.label"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="二级分类">
          <el-select v-model="formData.category_l2" placeholder="请选择" clearable style="width: 100%">
            <el-option
              v-for="c in subCategoryOptions"
              :key="c.label"
              :label="c.label"
              :value="c.label"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="内部流程">
          <el-input v-model="formData.internal_process" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="反馈部门">
          <el-input v-model="formData.feedback_dept" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button v-if="formMode === 'add'" type="primary" :loading="submitting" @click="handleAdd">确认新增</el-button>
        <el-button v-else type="primary" @click="handleEditNotSupported">确认编辑</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getQAList,
  searchQA,
  getQADetail,
  addQA,
  updateQAStatus,
  deleteQA,
  getCategories,
  type QAListItem,
  type QADetailResponse,
  type CategoryNode
} from '@/api/knowledge'

const keyword = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = ref(10)
const tableData = ref<QAListItem[]>([])
const total = ref(0)
const selectedRows = ref<QAListItem[]>([])
const categoryTree = ref<CategoryNode[]>([])

const categoryOptions = computed(() => categoryTree.value)
const subCategoryOptions = computed(() => {
  const parent = categoryTree.value.find((c) => c.label === formData.value.category_l1)
  return parent?.children || []
})

const detailVisible = ref(false)
const detailData = ref<QADetailResponse | null>(null)

const formVisible = ref(false)
const formMode = ref<'add' | 'edit'>('add')
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formData = ref({
  question: '',
  answer: '',
  category_l1: '',
  category_l2: '',
  internal_process: '',
  feedback_dept: ''
})

const statusLabel = (s: string) => {
  const map: Record<string, string> = { active: '已上架', deprecated: '已下架', archived: '已归档' }
  return map[s] || s
}
const statusTagType = (s: string) => {
  const map: Record<string, string> = { active: 'success', deprecated: 'warning', archived: 'info' }
  return map[s] || 'info'
}
const truncate = (text: string, n: number) => {
  if (!text) return ''
  return text.length > n ? text.slice(0, n) + '...' : text
}

const loadData = async () => {
  try {
    const hasKeyword = keyword.value.trim().length > 0
    const res = hasKeyword
      ? await searchQA({
          keyword: keyword.value.trim(),
          category_l1: filterCategory.value || undefined,
          status: filterStatus.value || undefined,
          page: page.value,
          page_size: pageSize.value
        })
      : await getQAList({
          page: page.value,
          page_size: pageSize.value,
          category_l1: filterCategory.value || undefined,
          status: filterStatus.value || undefined
        })
    tableData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载知识列表失败')
  }
}

const loadCategories = async () => {
  try {
    const res = await getCategories()
    categoryTree.value = res.categories || []
  } catch {
    ElMessage.error('加载分类失败')
  }
}

const handleSearch = () => {
  page.value = 1
  loadData()
}
const handleReset = () => {
  keyword.value = ''
  filterCategory.value = ''
  filterStatus.value = ''
  page.value = 1
  loadData()
}

const handleSelectionChange = (rows: QAListItem[]) => {
  selectedRows.value = rows
}

const handleToggleStatus = async (qaId: number, status: string, actionName: string) => {
  try {
    await updateQAStatus(qaId, status)
    ElMessage.success(`${actionName}成功`)
    loadData()
  } catch {
    ElMessage.error(`${actionName}失败`)
  }
}

const handleDelete = async (qaId: number) => {
  try {
    await ElMessageBox.confirm('确认删除该知识条目？删除后不可恢复。', '删除确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deleteQA(qaId)
    ElMessage.success('已删除')
    loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

const batchUpdateStatus = async (status: string, actionName: string) => {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) {
    ElMessage.warning(`请先勾选要${actionName}的条目`)
    return
  }
  try {
    await ElMessageBox.confirm(`确认${actionName}选中的 ${ids.length} 条知识？`, `${actionName}确认`, {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    const results = await Promise.allSettled(ids.map((id) => updateQAStatus(id, status)))
    const ok = results.filter((r) => r.status === 'fulfilled').length
    const fail = results.length - ok
    ElMessage.success(`${actionName}完成：成功 ${ok} 条${fail ? `，失败 ${fail} 条` : ''}`)
    loadData()
  } catch {
    ElMessage.error('批量操作失败')
  }
}

const batchDelete = async () => {
  const ids = selectedRows.value.map((r) => r.id)
  if (!ids.length) {
    ElMessage.warning('请先勾选要删除的条目')
    return
  }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条知识？删除后不可恢复。`, '批量删除确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    const results = await Promise.allSettled(ids.map((id) => deleteQA(id)))
    const ok = results.filter((r) => r.status === 'fulfilled').length
    const fail = results.length - ok
    ElMessage.success(`删除完成：成功 ${ok} 条${fail ? `，失败 ${fail} 条` : ''}`)
    loadData()
  } catch {
    ElMessage.error('批量删除失败')
  }
}

const openDetailDialog = async (id: number) => {
  try {
    const res = await getQADetail(id)
    detailData.value = res
    detailVisible.value = true
  } catch {
    ElMessage.error('加载详情失败')
  }
}

const resetForm = () => {
  formData.value = {
    question: '',
    answer: '',
    category_l1: '',
    category_l2: '',
    internal_process: '',
    feedback_dept: ''
  }
  editingId.value = null
}

const openAddDialog = () => {
  formMode.value = 'add'
  resetForm()
  formVisible.value = true
}

const openEditDialog = (row: QAListItem) => {
  formMode.value = 'edit'
  editingId.value = row.id
  formData.value = {
    question: row.question,
    answer: row.answer,
    category_l1: row.category_l1,
    category_l2: row.category_l2,
    internal_process: '',
    feedback_dept: ''
  }
  formVisible.value = true
}

const handleEditNotSupported = () => {
  ElMessage.warning('编辑内容接口待后端支持（当前后端仅提供上下架/删除），暂不可用')
}

const handleAdd = async () => {
  if (!formData.value.question.trim() || !formData.value.answer.trim()) {
    ElMessage.warning('问题内容和标准答案不能为空')
    return
  }
  submitting.value = true
  try {
    await addQA({
      question: formData.value.question.trim(),
      answer: formData.value.answer.trim(),
      category_l1: formData.value.category_l1 || undefined,
      category_l2: formData.value.category_l2 || undefined,
      internal_process: formData.value.internal_process || undefined,
      feedback_dept: formData.value.feedback_dept || undefined
    })
    ElMessage.success('新增成功')
    formVisible.value = false
    loadData()
  } catch {
    ElMessage.error('新增失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadData()
})
</script>

<style scoped>
.knowledge-list-wrap {
  width: 100%;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}
.full-card {
  height: 100%;
}
:deep(.el-card__body) {
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-body-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.filter-bar {
  margin: 12px 0;
  display: flex;
  align-items: center;
}
.btn-group {
  margin: 8px 0 12px;
}
.el-table {
  width: 100%;
}
</style>