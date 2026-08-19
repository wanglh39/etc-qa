<template>
  <div class="oplog-wrap">
    <!-- KPI概览卡片 -->
    <div class="kpi-row">
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ total }}</div>
            <div class="kpi-label">总操作数</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24"><CirclePlus /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ actionCount('create') }}</div>
            <div class="kpi-label">创建操作</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24"><Edit /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ actionCount('update') }}</div>
            <div class="kpi-label">修改操作</div>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-inner">
          <div class="kpi-icon">
            <el-icon :size="24"><Delete /></el-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-num">{{ actionCount('delete') }}</div>
            <div class="kpi-label">删除操作</div>
          </div>
        </div>
      </el-card>
    </div>

    <el-card class="full-card">
      <div class="card-body-inner">
        <div class="header-bar">
          <h3>操作日志</h3>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="table">表格</el-radio-button>
            <el-radio-button label="timeline">时间线</el-radio-button>
          </el-radio-group>
        </div>

        <div class="filter-bar">
          <el-input v-model="filterOperator" placeholder="操作人筛选" clearable style="width: 180px" @keyup.enter="handleSearch" />
          <el-select v-model="filterAction" placeholder="动作筛选" clearable style="width: 160px; margin-left: 12px" @change="handleSearch">
            <el-option label="创建" value="create" />
            <el-option label="修改" value="update" />
            <el-option label="删除" value="delete" />
            <el-option label="重置密码" value="reset_password" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="handleSearch">搜索</el-button>
          <el-button style="margin-left: 8px" @click="handleReset">重置</el-button>
        </div>

        <!-- 表格视图 -->
        <el-table v-if="viewMode === 'table'" border :max-height="'calc(100vh - 380px)'" :data="tableData">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="操作人" width="130">
            <template #default="{ row }">
              <div class="op-cell">
                <div class="op-avatar">{{ row.operator.charAt(0).toUpperCase() }}</div>
                <span>{{ row.operator }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="动作" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="actionTagType(row.action)" effect="dark">
                <el-icon style="margin-right:2px"><component :is="actionIcon(row.action)" /></el-icon>
                {{ actionLabel(row.action) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_type" label="对象类型" width="110" align="center" />
          <el-table-column prop="target_id" label="对象ID" width="80" align="center" />
          <el-table-column prop="detail" label="详情" min-width="250" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="170" align="center" />
        </el-table>

        <!-- 时间线视图 -->
        <div v-else class="timeline-view">
          <el-timeline>
            <el-timeline-item
              v-for="log in tableData"
              :key="log.id"
              :timestamp="log.created_at"
              placement="top"
              :type="actionTagType(log.action) as any"
            >
              <el-card shadow="hover" class="timeline-card">
                <div class="tl-header">
                  <div class="op-cell">
                    <div class="op-avatar">{{ log.operator.charAt(0).toUpperCase() }}</div>
                    <span class="tl-operator">{{ log.operator }}</span>
                  </div>
                  <el-tag :type="actionTagType(log.action)" effect="dark" size="small">
                    {{ actionLabel(log.action) }}
                  </el-tag>
                </div>
                <div class="tl-detail">{{ log.detail }}</div>
                <div class="tl-meta">
                  <span v-if="log.target_type">对象: {{ log.target_type }}</span>
                  <span v-if="log.target_id">ID: {{ log.target_id }}</span>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, CirclePlus, Edit, Delete, Refresh, Warning } from '@element-plus/icons-vue'
import { getOperationList, type OperationLogItem } from '@/api/system'

const filterOperator = ref('')
const filterAction = ref('')
const page = ref(1)
const pageSize = ref(20)
const tableData = ref<OperationLogItem[]>([])
const total = ref(0)
const viewMode = ref('table')

const actionCount = (action: string) => tableData.value.filter(r => r.action === action).length

const actionLabel = (a: string) => {
  const map: Record<string, string> = { create: '创建', update: '修改', delete: '删除', reset_password: '重置密码' }
  return map[a] || a
}
const actionTagType = (a: string): 'primary' | 'info' => {
  const map: Record<string, 'primary' | 'info'> = { create: 'primary', update: 'info', delete: 'info', reset_password: 'info' }
  return map[a] || 'info'
}
const actionIcon = (a: string) => {
  const map: Record<string, any> = { create: CirclePlus, update: Edit, delete: Delete, reset_password: Refresh }
  return map[a] || Warning
}

const loadData = async () => {
  try {
    const res = await getOperationList({
      page: page.value, page_size: pageSize.value,
      operator: filterOperator.value || undefined, action: filterAction.value || undefined
    })
    tableData.value = res.items
    total.value = res.total
  } catch { ElMessage.error('加载操作日志失败') }
}

const handleSearch = () => { page.value = 1; loadData() }
const handleReset = () => { filterOperator.value = ''; filterAction.value = ''; page.value = 1; loadData() }

onMounted(() => { loadData() })
</script>

<style scoped>
.oplog-wrap {
  width: 100%;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  background-color: #F8FAFC;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.kpi-card { transition: transform 0.2s; height: 100%; }
.kpi-card:hover { border-color: #CBD5E1 !important; }
.kpi-inner { display: flex; align-items: center; gap: 12px; }
.kpi-icon {
  width: 48px; height: 48px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; color: #fff;
  background: #F1F5F9; color: #1677FF;
}
.kpi-num { font-size: 24px; font-weight: 700; color: #0F172A; line-height: 1.2; }
.kpi-label { font-size: 13px; color: #bfbfbf; margin-top: 4px; }

.full-card { display: flex; flex-direction: column; }
:deep(.el-card__body) { padding: 20px; display: flex; flex-direction: column; }
.card-body-inner { display: flex; flex-direction: column; }
.header-bar {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}
.filter-bar { margin: 12px 0; display: flex; align-items: center; }

.op-cell { display: flex; align-items: center; gap: 8px; }
.op-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: #F1F5F9; color: #1677FF; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600;
}

.timeline-view {
  max-height: calc(100vh - 380px);
  overflow-y: auto;
  padding: 8px;
}
.timeline-card {
  margin-bottom: 0;
}
.tl-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
}
.tl-operator { font-weight: 500; color: #0F172A; }
.tl-detail { font-size: 13px; color: #475569; line-height: 1.5; margin-bottom: 4px; }
.tl-meta {
  font-size: 12px; color: #bfbfbf; display: flex; gap: 12px;
}
</style>
