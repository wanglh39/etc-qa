<template>
  <div class="config-page">
    <!-- 顶部横幅 -->
    <div class="config-banner">
      <div class="banner-icon">
        <el-icon :size="28"><Setting /></el-icon>
      </div>
      <div class="banner-text">
        <h2>业务配置管理</h2>
        <p>管理系统运行参数，修改后点击刷新缓存生效</p>
      </div>
      <el-button type="primary" @click="handleReload" :loading="reloading">
        <el-icon><Refresh /></el-icon> 刷新缓存
      </el-button>
    </div>

    <!-- 配置项卡片网格 -->
    <div class="config-grid" v-loading="loading">
      <div v-for="item in configList" :key="item.key" class="config-card">
        <div class="cc-header">
          <div class="cc-icon" :style="{ background: getConfigColor(item.key) }">
            <el-icon :size="20"><component :is="getConfigIcon(item.key)" /></el-icon>
          </div>
          <div class="cc-title-area">
            <div class="cc-title">{{ getConfigLabel(item.key) }}</div>
            <div class="cc-key">{{ item.key }}</div>
          </div>
          <el-button link type="primary" @click="editConfig(item)">
            <el-icon><Edit /></el-icon> 编辑
          </el-button>
        </div>
        <div class="cc-desc">{{ getConfigDesc(item.key) }}</div>
        <div class="cc-value">
          <pre>{{ formatValue(item.value) }}</pre>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" title="编辑配置" width="600px">
      <el-form label-width="100px">
        <el-form-item label="配置项">
          <el-input :value="getConfigLabel(editForm.key)" disabled />
        </el-form-item>
        <el-form-item label="配置键">
          <el-input :value="editForm.key" disabled />
        </el-form-item>
        <el-form-item label="配置值">
          <el-input
            v-model="editForm.valueStr"
            type="textarea"
            :rows="10"
            placeholder="输入 JSON 格式的值"
            style="font-family: monospace;"
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
import { Setting, Refresh, Edit, Document, Key, Warning, Shop } from '@element-plus/icons-vue'
import { getConfig, setConfig, reloadConfig } from '@/api/system'

interface ConfigRow {
  key: string
  value: any
}

const loading = ref(false)
const reloading = ref(false)
const configList = ref<ConfigRow[]>([])
const editVisible = ref(false)
const editForm = ref({ key: '', valueStr: '' })

const CONFIG_KEYS = [
  'qa_statuses',
  'brand_keywords',
  'forbidden_new_kws',
  'enterprise_name'
]

const configMeta: Record<string, { label: string; desc: string; icon: any; color: string }> = {
  qa_statuses: {
    label: '工单状态列表',
    desc: '定义系统中工单的所有可用状态，用于状态流转控制',
    icon: Document,
    color: '#1677FF'
  },
  brand_keywords: {
    label: '品牌关键词',
    desc: '用于识别用户提问中是否包含品牌相关词汇，影响分类和检索',
    icon: Key,
    color: '#1677FF'
  },
  forbidden_new_kws: {
    label: '禁用关键词',
    desc: '新建知识条目时禁止使用的关键词，防止不规范内容入库',
    icon: Warning,
    color: '#1677FF'
  },
  enterprise_name: {
    label: '企业名称',
    desc: '系统展示的企业名称，用于界面标题和品牌标识',
    icon: Shop,
    color: '#1677FF'
  }
}

const getConfigLabel = (key: string) => configMeta[key]?.label || key
const getConfigDesc = (key: string) => configMeta[key]?.desc || '暂无描述'
const getConfigIcon = (key: string) => configMeta[key]?.icon || Setting
const getConfigColor = (key: string) => configMeta[key]?.color || '#94A3B8'

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
  reloading.value = true
  try {
    await reloadConfig()
    ElMessage.success('缓存已刷新')
  } catch {
    ElMessage.error('刷新失败')
  } finally {
    reloading.value = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.config-page {
  padding: 20px;
}

.config-banner {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  color: #0F172A;
}
.banner-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: #F1F5F9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #1677FF;
}
.banner-text {
  flex: 1;
}
.banner-text h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
}
.banner-text p {
  margin: 0;
  font-size: 13px;
  opacity: 0.85;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.config-card {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}
.config-card:hover {
  border-color: #CBD5E1;
}
.cc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.cc-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.cc-title-area {
  flex: 1;
}
.cc-title {
  font-size: 15px;
  font-weight: 600;
  color: #0F172A;
}
.cc-key {
  font-size: 12px;
  color: #94A3B8;
  font-family: monospace;
}
.cc-desc {
  font-size: 13px;
  color: #bfbfbf;
  margin-bottom: 12px;
  line-height: 1.5;
}
.cc-value {
  background: #F8FAFC;
  border-radius: 6px;
  padding: 12px;
  max-height: 200px;
  overflow-y: auto;
}
.cc-value pre {
  margin: 0;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #475569;
}
</style>
