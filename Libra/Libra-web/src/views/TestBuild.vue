<template>
  <div class="test-page">
    <h1>BUILD TEST XYZ123</h1>
    <p>siteCount: {{ siteCount }}</p>
    <p>assetCount: {{ assetCount }}</p>
  </div>
</template>
<script setup>
import { ref } from 'vue'
const siteCount = ref(0)
const assetCount = ref(0)
</script>
<style scoped>
.test-page { padding: 40px; }
</style>