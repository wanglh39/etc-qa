<template>
  <PageLayout page-title="智能办结问题" class="page-wrap">
    <div class="container-root">
      <!-- 顶部操作按钮 -->
      <div class="top-actions">
        <el-button type="primary"> 刷新数据 </el-button>
        <el-button type="primary"> 一键采用回复 </el-button>
        <el-button type="info"> 标记无效 </el-button>
        <el-button type="primary"> 创建CRM工单 </el-button>
      </div>

      <div class="main-content">
        <!-- 左侧用户列表 -->
        <el-card shadow="never" class="left-panel">
          <template #header>
            <div class="card-header">用户列表</div>
          </template>
          <el-scrollbar height="100%">
            <div v-for="i in 20" :key="i" class="user-item" :class="{ active: i === 2 }">
              U000{{ i }}
            </div>
          </el-scrollbar>
        </el-card>

        <!-- 右侧两个文本域 -->
        <el-card shadow="never" class="right-panel">
          <div class="detail-form">
            <div class="form-item">
              <el-input
                type="textarea"
                placeholder="请输入内容"
                resize="none"
                model-value="客户来电询问商品质保时长"
              />
            </div>
            <div class="form-item">
              <el-input
                type="textarea"
                placeholder="请输入内容"
                resize="none"
                model-value="【标准问题】商品质保多久？
【AI推荐方案】商品质保一年，自购买之日起计算。如超出保修期，可提供付费维修服务。"
              />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts"></script>

<style scoped>
/* 1.最外层页面强制高度，禁止父容器滚动 */
.page-wrap {
  height: 100vh;
  overflow: hidden;
}

/* 全局强制穿透PageLayout所有层级容器，全部禁止滚动、撑满高度 */
:deep(.el-main),
:deep(.layout-content),
:deep(.page-main) {
  height: calc(100vh - 60px) !important;
  overflow: hidden !important;
  padding: 16px !important;
  box-sizing: border-box;
}

.container-root {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 顶部按钮固定不压缩 */
.top-actions {
  flex-shrink: 0;
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}

/* 左右区域占剩余全部高度 */
.main-content {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}

/* 左侧面板 */
.left-panel {
  width: 260px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.card-header {
  font-weight: bold;
}
.user-item {
  padding: 12px 14px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}
.user-item.active {
  background: #e6f4ff;
  color: #1677ff;
}

/* 右侧面板 */
.right-panel {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 卡片body强制撑满 */
.right-panel :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 0;
}

.detail-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}
.form-item {
  flex: 1;
  min-height: 0;
}

/* 文本域彻底清除默认高度限制 */
.form-item :deep(.el-textarea) {
  height: 100% !important;
}
.form-item :deep(.el-textarea__inner) {
  height: 100% !important;
  min-height: 0 !important;
  resize: none;
}
</style>
