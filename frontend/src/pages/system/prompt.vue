<template>
  <div class="prompt-page">
    <div class="two-col">
      <!-- 左栏：提示词列表 -->
      <div class="left-col">
        <el-card shadow="hover">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">提示词模板</span>
              <el-tag size="small" type="info">{{ promptList.length }} 个</el-tag>
            </div>
          </template>
          <div class="prompt-list">
            <div
              v-for="item in promptList"
              :key="item.prompt_key"
              class="prompt-item"
              :class="{ active: selectedKey === item.prompt_key }"
              @click="selectPrompt(item.prompt_key)"
            >
              <div class="pi-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="pi-info">
                <div class="pi-name">{{ promptDisplayName(item.prompt_key) }}</div>
                <div class="pi-meta">
                  <span v-if="item.latest_version">v{{ item.latest_version }}</span>
                  <el-tag v-if="item.active_count" size="small" type="success" style="margin-left:4px">{{ item.active_count }}活跃</el-tag>
                  <el-tag v-if="item.shadow_count" size="small" type="warning" style="margin-left:4px">{{ item.shadow_count }}影子</el-tag>
                </div>
              </div>
            </div>
            <div v-if="promptList.length === 0" class="empty-tip">暂无提示词模板</div>
          </div>
        </el-card>
      </div>

      <!-- 右栏：版本管理 -->
      <div class="right-col">
        <el-card shadow="hover" v-if="selectedKey">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">{{ promptDisplayName(selectedKey) }} 版本管理</span>
              <el-button type="primary" size="small" @click="openPublishDialog">
                <el-icon><Plus /></el-icon> 发布新版本
              </el-button>
            </div>
          </template>

          <!-- 版本列表 -->
          <div class="version-list">
            <div
              v-for="v in versionList"
              :key="v.version"
              class="version-item"
              :class="{ 'version-active': v.is_active, 'version-shadow': v.status === 'shadow' }"
              @click="viewVersion(v.version)"
            >
              <div class="vi-left">
                <div class="vi-version">v{{ v.version }}</div>
                <el-tag v-if="v.is_active" size="small" type="success" effect="dark">活跃</el-tag>
                <el-tag v-else-if="v.status === 'shadow'" size="small" type="warning" effect="dark">影子</el-tag>
                <el-tag v-else size="small" type="info">历史</el-tag>
              </div>
              <div class="vi-desc">{{ v.description || '暂无描述' }}</div>
              <div class="vi-time">{{ v.created_at || '' }}</div>
              <div class="vi-actions" v-if="!v.is_active">
                <el-button link type="warning" size="small" @click.stop="handleRollback(v.version)">回滚</el-button>
              </div>
            </div>
          </div>

          <!-- 版本内容预览 -->
          <el-dialog v-model="previewVisible" :title="`版本 v${previewVersion} 内容`" width="700px">
            <div class="preview-content">
              <pre>{{ previewText }}</pre>
            </div>
          </el-dialog>
        </el-card>

        <el-card v-else class="empty-card">
          <div class="select-prompt-tip">
            <el-icon :size="48"><DocumentRemove /></el-icon>
            <p>请从左侧选择一个提示词模板</p>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 发布新版本对话框 -->
    <el-dialog v-model="publishVisible" title="发布新版本" width="700px">
      <el-form label-width="80px">
        <el-form-item label="模板">
          <span>{{ promptDisplayName(selectedKey) }}</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="publishForm.description" placeholder="版本描述（可选）" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="publishForm.templateText"
            type="textarea"
            :rows="12"
            placeholder="输入模板内容（Jinja2格式）"
            style="font-family: monospace;"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="handlePublish">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, DocumentRemove, Plus } from '@element-plus/icons-vue'
import {
  listPrompts, listVersions, getVersion, publishPrompt, rollbackPrompt,
  type PromptKeySummary, type PromptVersionInfo
} from '@/api/system'

const promptList = ref<PromptKeySummary[]>([])
const selectedKey = ref('')
const versionList = ref<PromptVersionInfo[]>([])

const previewVisible = ref(false)
const previewVersion = ref(0)
const previewText = ref('')

const publishVisible = ref(false)
const publishForm = ref({ description: '', templateText: '' })
const publishing = ref(false)

const promptNameMap: Record<string, string> = {
  rag_answer: 'RAG回答模板',
  standardize: '问题标准化模板',
  categorize: '分类模板',
  extract: '信息提取模板'
}
const promptDisplayName = (key: string) => promptNameMap[key] || key

const loadPrompts = async () => {
  try {
    promptList.value = await listPrompts()
    if (promptList.value.length > 0 && !selectedKey.value) {
      selectPrompt(promptList.value[0].prompt_key)
    }
  } catch {
    ElMessage.error('加载提示词列表失败')
  }
}

const selectPrompt = async (key: string) => {
  selectedKey.value = key
  try {
    versionList.value = await listVersions(key)
  } catch {
    ElMessage.error('加载版本列表失败')
  }
}

const viewVersion = async (version: number) => {
  try {
    const res = await getVersion(selectedKey.value, version)
    previewVersion.value = version
    previewText.value = res.template_text || JSON.stringify(res, null, 2)
    previewVisible.value = true
  } catch {
    ElMessage.error('加载版本内容失败')
  }
}

const openPublishDialog = () => {
  publishForm.value = { description: '', templateText: '' }
  publishVisible.value = true
}

const handlePublish = async () => {
  if (!publishForm.value.templateText.trim()) {
    ElMessage.warning('请输入模板内容')
    return
  }
  publishing.value = true
  try {
    await publishPrompt(selectedKey.value, publishForm.value.templateText, publishForm.value.description)
    ElMessage.success('新版本已发布')
    publishVisible.value = false
    selectPrompt(selectedKey.value)
    loadPrompts()
  } catch {
    ElMessage.error('发布失败')
  } finally {
    publishing.value = false
  }
}

const handleRollback = async (version: number) => {
  try {
    await ElMessageBox.confirm(`确认回滚到 v${version}？`, '回滚确认', { type: 'warning' })
    await rollbackPrompt(selectedKey.value, version)
    ElMessage.success(`已回滚到 v${version}`)
    selectPrompt(selectedKey.value)
    loadPrompts()
  } catch {
    ElMessage.error('回滚失败')
  }
}

onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.prompt-page {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #f0f2f5;
}

.two-col {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title {
  font-size: 16px;
  font-weight: 600;
}

.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.prompt-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.prompt-item:hover {
  background: #f5f7fa;
}
.prompt-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}
.pi-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pi-name {
  font-weight: 500;
  color: #303133;
}
.pi-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
  display: flex;
  align-items: center;
}
.empty-tip {
  text-align: center;
  color: #c0c4cc;
  padding: 20px;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.version-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition: all 0.2s;
}
.version-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.version-active {
  border-color: #67c23a;
  background: #f0f9eb;
}
.version-shadow {
  border-color: #e6a23c;
  background: #fdf6ec;
}
.vi-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}
.vi-version {
  font-weight: 700;
  color: #303133;
}
.vi-desc {
  flex: 1;
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vi-time {
  font-size: 12px;
  color: #c0c4cc;
}
.vi-actions {
  margin-left: 8px;
}

.preview-content {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  max-height: 500px;
  overflow-y: auto;
}
.preview-content pre {
  color: #4caf50;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.empty-card {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
.select-prompt-tip {
  text-align: center;
  color: #c0c4cc;
}
</style>