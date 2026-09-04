<template>
  <PageLayout page-title="分类管理">
    <!-- 右上角按钮 -->
    <template #actions>
      <el-button type="primary" @click="resetForm"> 新增分类 </el-button>
    </template>

    <el-row :gutter="20" align="stretch">
      <el-col :span="8">
        <el-card class="full-height-card">
          <template #header> 分类树 </template>
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
          <template #header> 分类详情 </template>
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
              <el-button type="primary" @click="save"> 保存 </el-button>
              <el-button @click="resetForm"> 重置 </el-button>
              <el-button type="info" :disabled="!form.id" @click="remove"> 删除 </el-button>
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

// 点击树节点回填表单
const fillForm = (node: any) => {
  form.value.id = node.id
  form.value.label = node.label
  form.value.parentId = node.parentId || ''
  form.value.desc = node.description || ''
}
// 重置表单（新增）
const resetForm = () => {
  form.value = { id: '', label: '', parentId: '', desc: '' }
}
// 保存分类（新增或更新）
const save = async () => {
  if (!form.value.label) return ElMessage.warning('请填写分类名称')
  const payload = {
    label: form.value.label,
    parent_id: form.value.parentId || null,
    description: form.value.desc,
  }
  try {
    if (form.value.id) {
      await updateCategory(form.value.id, payload)
      ElMessage.success('分类已更新')
    } else {
      await createCategory(payload)
      ElMessage.success('分类已创建')
    }
    resetForm()
    loadTree()
  } catch {
    ElMessage.error('保存分类失败')
  }
}
// 删除分类
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
    resetForm()
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
