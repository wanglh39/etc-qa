<template>
  <PageLayout page-title="分类管理">
    <!-- 右上角按钮 -->
    <template #actions>
      <el-button type="primary" @click="handleAdd"> 新增分类 </el-button>
    </template>

    <el-row :gutter="20" align="stretch">
      <el-col :span="8">
        <el-card class="full-height-card">
          <template #header> 分类树（点击节点编辑） </template>
          <el-input
            v-model="searchKey"
            placeholder="搜索分类"
            clearable
            style="margin-bottom: 10px"
          />
          <el-tree
            :data="categoryTree"
            :props="{ label: 'label', children: 'children' }"
            node-key="id"
            @node-click="fillForm"
          />
        </el-card>
      </el-col>
      <!-- 右侧表单 -->
      <el-col :span="16">
        <el-card class="full-height-card">
          <template #header>
            <span v-if="formMode === 'add'"> 新增分类 </span>
            <span v-else> 编辑分类：{{ editingLabel }} </span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="分类名称">
              <el-input v-model="form.label" placeholder="请输入分类名称" />
            </el-form-item>
            <el-form-item label="上级分类">
              <el-tree-select
                v-model="form.parentId"
                :data="categoryTree"
                :props="{ label: 'label', value: 'id' }"
                placeholder="无则为一级分类"
                clearable
                check-strictly
                :render-after-expand="false"
              />
            </el-form-item>
            <el-form-item label="分类描述">
              <el-input
                v-model="form.desc"
                type="textarea"
                :rows="3"
                placeholder="请输入分类描述"
              />
            </el-form-item>
            <el-form-item>
              <el-button v-if="formMode === 'add'" type="primary" @click="save"> 创建 </el-button>
              <el-button v-else type="primary" @click="save"> 保存修改 </el-button>
              <el-button @click="handleAdd"> 新建 </el-button>
              <el-button type="info" :disabled="formMode !== 'edit'" @click="remove">
                删除
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PageLayout from '@/components/layout/PageLayout.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCategories, createCategory, updateCategory, deleteCategory } from '@/api/knowledge'

const searchKey = ref('')
const categoryTree = ref<any[]>([])

const formMode = ref<'add' | 'edit'>('add')
const editingLabel = ref('')
const form = ref<{ id: number | ''; label: string; parentId: number | ''; desc: string }>({
  id: '',
  label: '',
  parentId: '',
  desc: '',
})

const loadTree = async () => {
  try {
    const res = await getCategories()
    categoryTree.value = res.categories || []
  } catch {
    ElMessage.error('加载分类失败')
  }
}

onMounted(loadTree)

const isDerived = ref(false)

const fillForm = (node: any) => {
  form.value.id = node.id
  form.value.label = node.label
  form.value.parentId = node.parentId || ''
  form.value.desc = node.description || ''
  isDerived.value = !!node.derived
  formMode.value = 'edit'
  editingLabel.value = node.label
}

const handleAdd = () => {
  formMode.value = 'add'
  editingLabel.value = ''
  isDerived.value = false
  form.value = { id: '', label: '', parentId: '', desc: '' }
}

const save = async () => {
  if (!form.value.label) return ElMessage.warning('请填写分类名称')
  const payload = {
    label: form.value.label,
    parent_id: form.value.parentId || null,
    description: form.value.desc,
  }
  try {
    if (formMode.value === 'edit' && form.value.id && !isDerived.value) {
      await updateCategory(form.value.id, payload)
      ElMessage.success('分类已更新')
    } else {
      await createCategory(payload)
      ElMessage.success('分类已创建')
    }
    handleAdd()
    loadTree()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(detail || '保存分类失败')
  }
}

const remove = async () => {
  if (!form.value.id) return ElMessage.warning('请先选择一个分类')
  try {
    await ElMessageBox.confirm(
      `确定删除分类「${form.value.label}」吗？该操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deleteCategory(form.value.id)
    ElMessage.success('分类已删除')
    handleAdd()
    loadTree()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(detail || '删除分类失败')
  }
}
</script>

<style scoped>
.full-height-card {
  height: 100%;
}
</style>
