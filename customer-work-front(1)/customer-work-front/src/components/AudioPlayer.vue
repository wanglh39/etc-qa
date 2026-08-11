<template>
  <div class="audio-wrapper">
    <!-- 独立闭合audio, 内部不放任何div -->
    <audio controls preload="metadata" :src="audioUrl"></audio> <!-- 👈 在这里添加了 </audio> -->

    <!-- 转写div放在audio外面, 平级布局 -->
    <div class="voice-trans">语音转写: {{ transText }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  audioUrl: string
  transText: string
}>()
</script>

<style scoped>
.audio-wrapper {
  width: 100%;
}
.audio-wrapper audio {
  width: 100%;
}
.voice-trans {
  margin-top: 10px;
  color: #444;
  line-height: 1.6;
}
</style>