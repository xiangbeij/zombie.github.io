<template>
  <div class="dashboard">
    <h1>LOCAL BUILD TEST ABCXYZ</h1>
    <p>siteCount={{ siteCount }} assetCount={{ assetCount }}</p>
  </div>
</template>
<script setup>
import { ref } from 'vue'
const siteCount = ref(999)
const assetCount = ref(888)
</script>
<style scoped>
.dashboard { padding: 20px; }
</style>