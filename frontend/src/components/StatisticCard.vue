<template>
  <el-card class="stat-card" :class="{ clickable: to, alert: alert }" @click="handleClick">
    <div class="stat-top">
      <span class="stat-title">{{ title }}</span>
      <el-icon :size="24" :color="iconColor">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="stat-num">
      {{ displayValue }}
    </div>
    <div class="stat-bottom">
      <span class="stat-desc">{{ desc }}</span>
      <span v-if="growth !== undefined" class="stat-growth" :class="growth >= 0 ? 'up' : 'down'">
        {{ growth >= 0 ? '↑' : '↓' }} {{ Math.abs(growth) }}%
      </span>
    </div>
    <div v-if="progress" class="progress-bar">
      <div
        class="progress-fill"
        :style="{ width: progressPercent + '%', background: alert ? '#64748B' : iconColor }"
      />
    </div>
    <div v-if="sparkline && sparkline.length > 1" class="sparkline-wrap">
      <svg :viewBox="`0 0 ${sparkline.length * 8} 20`" class="sparkline" preserveAspectRatio="none">
        <polyline :points="sparklinePoints" fill="none" :stroke="iconColor" stroke-width="1.5" />
      </svg>
    </div>
    <div v-if="to" class="click-hint">
      <span>点击查看</span>
      <el-icon class="arrow">
        <ArrowRight />
      </el-icon>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import type { Component } from 'vue'

const props = defineProps<{
  title: string
  value: string | number
  desc: string
  icon: Component
  iconColor?: string
  growth?: number
  to?: string
  progress?: { current: number; total: number }
  alert?: boolean
  sparkline?: number[]
}>()

const router = useRouter()
const displayValue = ref('0')

const progressPercent = computed(() => {
  if (!props.progress || props.progress.total === 0) return 0
  return Math.min(100, Math.round((props.progress.current / props.progress.total) * 100))
})

const sparklinePoints = computed(() => {
  if (!props.sparkline || props.sparkline.length === 0) return ''
  const data = props.sparkline
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  return data.map((v, i) => `${i * 8},${20 - ((v - min) / range) * 18 - 1}`).join(' ')
})

const animateCount = (target: number) => {
  if (typeof props.value !== 'number') {
    displayValue.value = String(props.value)
    return
  }
  const duration = 800
  const start = performance.now()
  const step = (now: number) => {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    displayValue.value = String(Math.round(target * eased))
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

watch(
  () => props.value,
  (v) => {
    if (typeof v === 'number') animateCount(v)
    else displayValue.value = String(v)
  }
)

onMounted(() => {
  if (typeof props.value === 'number') animateCount(props.value)
  else displayValue.value = String(props.value)
})

const handleClick = () => {
  if (props.to) router.push(props.to)
}
</script>

<style scoped>
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: default;
  transition: border-color 0.2s;
  position: relative;
  height: 100%;
}
.stat-card.clickable {
  cursor: pointer;
}
.stat-card.clickable:hover {
  border-color: #cbd5e1 !important;
}
.stat-card.alert {
  border-color: #64748b !important;
}
.stat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-title {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}
.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1;
}
.stat-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}
.stat-desc {
  font-size: 12px;
  color: #94a3b8;
}
.stat-growth {
  font-size: 12px;
  font-weight: 600;
}
.stat-growth.up {
  color: #1677ff;
}
.stat-growth.down {
  color: #64748b;
}
.progress-bar {
  height: 3px;
  background: #f1f5f9;
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}
.sparkline-wrap {
}
.sparkline {
  width: 100%;
  height: 20px;
  opacity: 0.5;
}
.click-hint {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 2px;
}
.stat-card.clickable:hover .click-hint {
  color: #1677ff;
}
.arrow {
  transition: transform 0.2s;
}
.stat-card.clickable:hover .arrow {
  transform: translateX(2px);
}
</style>
