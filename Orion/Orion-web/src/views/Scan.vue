<template>
  <div class="scan-page">
    <div class="page-header">
      <h2 class="page-title">鍙戣捣鎵弿</h2>
    </div>

    <div class="white-card">
      <el-form :model="form" label-position="top">
        <el-form-item label="鐩爣 URL">
          <el-input v-model="form.url" placeholder="https://example.com" size="large" clearable :disabled="scanning">
            <template #prefix><el-icon><Promotion /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="鎵弿妯″紡">
          <el-radio-group v-model="form.scanType" :disabled="scanning" size="large">
            <el-radio-button value="HomePage_Scan">棣栭〉鎵弿</el-radio-button>
            <el-radio-button value="SecondPage_Scan">浜岀骇椤甸潰鎵弿</el-radio-button>
            <el-radio-button value="AllSite_Scan">鍏ㄧ珯鎵弿</el-radio-button>
            <el-radio-button value="CustomPage_Scan">鑷畾涔夋壂鎻?/el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="scanning" @click="handleStartScan" style="width:200px">
            {{ scanning ? '鎵弿杩涜涓?..' : '寮€濮嬫壂鎻? }}
          </el-button>
          <el-button size="large" @click="form.url=''" :disabled="scanning">閲嶇疆</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-if="scanning || currentTaskId" class="white-card progress-card">
      <div class="progress-header">
        <div class="progress-info">
          <h3>鎵弿杩涜涓?/h3>
          <p class="progress-url">{{ form.url }}</p>
        </div>
        <el-tag type="primary" size="large">杩涜涓?/el-tag>
      </div>
      <el-progress :percentage="progress" :stroke-width="10" status="primary" />
      <p class="progress-hint">姝ｅ湪鍒嗘瀽椤甸潰鍐呭锛岃绋嶅€?..</p>
    </div>

    <div v-if="scanResult" class="white-card result-card">
      <div class="result-header">
        <h3>鎵弿缁撴灉</h3>
        <el-tag :type="scanResult.status === 'sussess' ? 'success' : 'danger'">
          {{ scanResult.status === 'sussess' ? '瀹屾垚' : '寮傚父' }}
        </el-tag>
      </div>
      <el-row :gutter="16" class="result-summary">
        <el-col :span="6">
          <div class="result-item" :class="{ danger: scanResult.blacklink_list?.length }">
            <div class="result-count">{{ scanResult.blacklink_list?.length || 0 }}</div>
            <div class="result-label">榛戦摼</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item" :class="{ danger: scanResult.backdoor_list?.length }">
            <div class="result-count">{{ scanResult.backdoor_list?.length || 0 }}</div>
            <div class="result-label">鍚庨棬</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item" :class="{ warn: scanResult.violativelink_list?.length }">
            <div class="result-count">{{ scanResult.violativelink_list?.length || 0 }}</div>
            <div class="result-label">杩濊</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-count">{{ scanResult.diedlink_list?.length || 0 }}</div>
            <div class="result-label">姝婚摼</div>
          </div>
        </el-col>
      </el-row>
      <div class="result-details">
        <el-collapse v-if="scanResult.blacklink_list?.length">
          <el-collapse-item title="榛戦摼璇︽儏" name="blacklink">
            <div v-for="(item, idx) in scanResult.blacklink_list" :key="idx" class="result-block">
              <div class="result-block-title">闂鍦板潃: {{ item.url }}</div>
              <div v-for="(link, i) in item.blacklinkres" :key="i" class="result-block-content">{{ link }}</div>
              <div class="result-block-source">鏉ユ簮: {{ item.master?.join(', ') }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="scanResult.backdoor_list?.length">
          <el-collapse-item title="鍚庨棬璇︽儏" name="backdoor">
            <div v-for="(item, idx) in scanResult.backdoor_list" :key="idx" class="result-block">
              <div class="result-block-title">闂鍦板潃: {{ item.url }}</div>
              <div v-for="(bk, i) in item.backdoorres" :key="i" class="result-block-content">{{ bk }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="scanResult.violativelink_list?.length">
          <el-collapse-item title="杩濊璇︽儏" name="violative">
            <div v-for="(item, idx) in scanResult.violativelink_list" :key="idx" class="result-block">
              <div class="result-block-title">闂鍦板潃: {{ item.url }}</div>
              <div v-for="(v, i) in item.violativelinkres" :key="i" class="result-block-content">{{ v }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="scanResult.diedlink_list?.length">
          <el-collapse-item title="姝婚摼璇︽儏" name="diedlink">
            <div v-for="(item, idx) in scanResult.diedlink_list" :key="idx" class="result-block">
              <div class="result-block-title">澶辨晥鍦板潃: {{ item.url }}</div>
              <div class="result-block-content">鐘舵€佺爜: {{ item.status_code }}</div>
              <div class="result-block-source">鏉ユ簮: {{ item.master?.join(', ') }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-empty v-if="!scanResult.blacklink_list?.length && !scanResult.backdoor_list?.length && !scanResult.violativelink_list?.length && !scanResult.diedlink_list?.length"
          description="鏈彂鐜颁换浣曞▉鑳侊紝缃戠珯瀹夊叏鐘跺喌鑹ソ锛? />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import { startScan, getScanStatus } from '../api/Orion'

const form = reactive({ url: '', scanType: 'HomePage_Scan' })
const scanning = ref(false)
const currentTaskId = ref(null)
const progress = ref(0)
const scanResult = ref(null)

const handleStartScan = async () => {
  if (!form.url) { ElMessage.warning('璇疯緭鍏ョ洰鏍?URL'); return }
  scanning.value = true; currentTaskId.value = null; progress.value = 0; scanResult.value = null
  try {
    const res = await startScan(form.url, form.scanType)
    currentTaskId.value = res.data.task_id
    ElMessage.success('鎵弿浠诲姟宸插惎鍔?)
    pollScanStatus()
  } catch { ElMessage.error('鍚姩鎵弿澶辫触') } finally { scanning.value = false }
}

const pollScanStatus = async () => {
  if (!currentTaskId.value) return
  const poll = async () => {
    if (!currentTaskId.value) return
    try {
      const res = await getScanStatus(currentTaskId.value)
      const task = res.data
      if (task.status === 'running') {
        progress.value = Math.min(progress.value + 10, 90)
        setTimeout(poll, 3000)
      } else if (task.status === 'success') {
        progress.value = 100; scanResult.value = task.result; ElMessage.success('鎵弿瀹屾垚')
      } else {
        scanning.value = false; ElMessage.error('鎵弿澶辫触')
      }
    } catch { setTimeout(poll, 5000) }
  }
  setTimeout(poll, 2000)
}
</script>

<style scoped>
.scan-page { color: #1a1a2e; max-width: 900px; }
.page-header { margin-bottom: 24px; }
.page-title { margin: 0; font-size: 22px; font-weight: 600; color: #1a1a2e; }
.white-card {
  background: #ffffff; border-radius: 16px; padding: 24px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 12px rgba(0,0,0,0.04); margin-bottom: 20px;
}
.progress-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.progress-info h3 { margin: 0 0 4px; color: #1a1a2e; }
.progress-url { margin: 0; font-size: 13px; color: #8a94a6; }
.progress-hint { margin: 12px 0 0; font-size: 12px; color: #8a94a6; text-align: center; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.result-header h3 { margin: 0; color: #1a1a2e; }
.result-summary { margin-bottom: 20px; }
.result-item {
  background: #f8f9fb; border-radius: 12px; padding: 16px; text-align: center;
  border: 1px solid #e8eaed;
}
.result-item.danger { background: #fff0f0; border-color: #ffcdd2; }
.result-item.warn { background: #fff8e0; border-color: #ffe082; }
.result-count { font-size: 32px; font-weight: 700; color: #1a1a2e; }
.result-label { font-size: 12px; color: #8a94a6; margin-top: 4px; }
.result-details { margin-top: 8px; }
.result-block { background: #f8f9fb; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.result-block-title { font-size: 13px; color: #f44; margin-bottom: 8px; word-break: break-all; }
.result-block-content { font-size: 12px; color: #5a6474; margin-bottom: 4px; word-break: break-all; }
.result-block-source { font-size: 11px; color: #8a94a6; margin-top: 4px; }
</style>
