<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>业务配置管理</span>
          <el-button type="primary" size="small" @click="handleReload">刷新缓存</el-button>
        </div>
      </template>

      <el-table :data="configList" border stripe v-loading="loading">
        <el-table-column prop="key" label="配置项" width="240" />
        <el-table-column label="当前值" min-width="300">
          <template #default="{ row }">
            <span class="config-value">{{ formatValue(row.value) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="editConfig(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="editVisible" title="编辑配置" width="600px">
      <el-form label-width="100px">
        <el-form-item label="配置项">
          <el-input :value="editForm.key" disabled />
        </el-form-item>
        <el-form-item label="配置值">
          <el-input
            v-model="editForm.valueStr"
            type="textarea"
            :rows="8"
            placeholder="输入 JSON 格式的值"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, setConfig, reloadConfig } from '@/api/system'

interface ConfigRow {
  key: string
  value: any
}

const loading = ref(false)
const configList = ref<ConfigRow[]>([])
const editVisible = ref(false)
const editForm = ref({ key: '', valueStr: '' })

const CONFIG_KEYS = [
  'qa_statuses',
  'brand_keywords',
  'forbidden_new_kws',
  'enterprise_name'
]

const formatValue = (val: any) => {
  if (typeof val === 'string') return val
  return JSON.stringify(val, null, 2)
}

const loadConfigs = async () => {
  loading.value = true
  const items: ConfigRow[] = []
  for (const key of CONFIG_KEYS) {
    try {
      const res = await getConfig(key)
      items.push({ key: res.key, value: res.value })
    } catch {
      // 配置项可能不存在
    }
  }
  configList.value = items
  loading.value = false
}

const editConfig = (row: ConfigRow) => {
  editForm.value = {
    key: row.key,
    valueStr: formatValue(row.value)
  }
  editVisible.value = true
}

const saveConfig = async () => {
  try {
    const parsed = JSON.parse(editForm.value.valueStr)
    await setConfig(editForm.value.key, parsed)
    ElMessage.success('保存成功')
    editVisible.value = false
    loadConfigs()
  } catch {
    // 不是 JSON，尝试作为字符串保存
    try {
      await setConfig(editForm.value.key, editForm.value.valueStr)
      ElMessage.success('保存成功')
      editVisible.value = false
      loadConfigs()
    } catch {
      ElMessage.error('保存失败，请检查格式')
    }
  }
}

const handleReload = async () => {
  try {
    await reloadConfig()
    ElMessage.success('缓存已刷新')
  } catch {
    ElMessage.error('刷新失败')
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.config-page {
  padding: 20px;
  max-width: 900px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.config-value {
  font-family: monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
