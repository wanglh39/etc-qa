<template>
  <el-card>
    <template #header>审核历史记录</template>
    <div style="margin-bottom:12px">
      <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="起始日期" end-placeholder="结束日期"/>
      <el-button style="margin-left:10px" type="primary">筛选</el-button>
      <el-button style="margin-left:10px">导出Excel</el-button>
    </div>
    <el-table :data="historyList" border>
      <el-table-column prop="auditId" label="审核编号" width="120"/>
      <el-table-column prop="problem" label="审核问题" min-width="200"/>
      
      <!-- 【新增】标准化答案字段 -->
      <el-table-column prop="standardAnswer" label="标准化答案" min-width="200">
        <template #default="{row}">
          <!-- 如果内容为空显示占位符，避免空白 -->
          <span style="color: #909399;">{{ row.standardAnswer || '暂无' }}</span>
        </template>
      </el-table-column>
      
      <el-table-column prop="result" label="审核结果" width="100">
        <template #default="{row}">
          <el-tag :type="row.result==='入库'?'success':'warning'">{{row.result}}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="操作管理员" width="120"/>
      <el-table-column prop="auditTime" label="审核时间" width="180"/>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const dateRange = ref()

// 模拟数据中增加了 standardAnswer 字段
const historyList = ref([
  {
    auditId: 'HIS001',
    problem: '登录验证码过期处理',
    standardAnswer: '请用户检查短信拦截设置或稍后重试', // 示例数据
    result: '入库',
    operator: '管理员',
    auditTime: '2026-07-09 10:21:00'
  },
  {
    auditId: 'HIS002',
    problem: '月卡自动续费疑问',
    standardAnswer: '', // 示例数据（空值）
    result: '驳回',
    operator: '管理员',
    auditTime: '2026-07-10 15:40:00'
  }
])
</script>