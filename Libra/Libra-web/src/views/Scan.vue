<template>
  <div class="scan-page">
    <div class="page-header">
      <h2 class="page-title">发起扫描</h2>
    </div>

    <div class="white-card">
      <el-form :model="form" label-position="top">
        <el-form-item label="目标 URL">
          <el-input v-model="form.url" placeholder="https://example.com" size="large" clearable :disabled="scanning">
            <template #prefix><el-icon><Promotion /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="扫描模式">
          <el-radio-group v-model="form.scanType" :disabled="scanning" size="large">
            <el-radio-button value="HomePage_Scan">首页扫描</el-radio-button>
            <el-radio-button value="SecondPage_Scan">二级页面扫描</el-radio-button>
            <el-radio-button value="AllSite_Scan">全站扫描</el-radio-button>
            <el-radio-button value="CustomPage_Scan">自定义扫描</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="scanning" @click="handleStartScan" style="width:200px">
            {{ scanning ? '扫描进行中...' : '开始扫描' }}
          </el-button>
          <el-button size="large" @click="form.url=''" :disabled="scanning">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-if="scanning || currentTaskId" class="white-card progress-card">
      <div class="progress-header">
        <div class="progress-info">
          <h3>扫描进行中</h3>
          <p class="progress-url">{{ form.url }}</p>
        </div>
        <el-tag type="primary" size="large">进行中</el-tag>
      </div>
      <el-progress :percentage="progress" :stroke-width="10" status="primary" />
      <p class="progress-hint">正在分析页面内容，请稍候...</p>
    </div>

    <div v-if="scanResult" class="white-card result-card">
      <div class="result-header">
        <h3>扫描结果</h3>
        <el-tag :type="scanResult.status === 'sussess' ? 'success' : 'danger'">
          {{ scanResult.status === 'sussess' ? '完成' : '异常' }}
        </el-tag>
      </div>
      <el-row :gutter="16" class="result-summary">
        <el-col :span="6">
          <div class="result-item" :class="{ danger: scanResult.blacklink_list?.length }">
            <div class="result-count">{{ scanResult.blacklink_list?.length || 0 }}</div>
            <div class="result-label">黑链</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item" :class="{ danger: scanResult.backdoor_list?.length }">
            <div class="result-count">{{ scanResult.backdoor_list?.length || 0 }}</div>
            <div class="result-label">后门</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item" :class="{ warn: scanResult.violativelink_list?.length }">
            <div class="result-count">{{ scanResult.violativelink_list?.length || 0 }}</div>
            <div class="result-label">违规</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-count">{{ scanResult.diedlink_list?.length || 0 }}</div>
            <div class="result-label">死链</div>
          </div>
        </el-col>
      </el-row>
      <div class="result-details">
        <el-collapse v-if="scanResult.blacklink_list?.length">
          <el-collapse-item title="黑链详情" name="blacklink">
            <div v-for="(item, idx) in scanResult.blacklink_list" :key="idx" class="result-block">
              <div class="result-block-title">问题地址: {{ item.url }}</div>
              <div v-for="(link, i) in item.blacklinkres" :key="i" class="result-block-content">{{ link }}</div>
              <div class="result-block-source">来源: {{ item.master?.join(', ') }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="scanResult.backdoor_list?.length">
          <el-collapse-item title="后门详情" name="backdoor">
            <div v-for="(item, idx) in scanResult.backdoor_list" :key="idx" class="result-block">
              <div class="result-block-title">问题地址: {{ item.url }}</div>
              <div v-for="(bk, i) in item.backdoorres" :key="i" class="result-block-content">{{ bk }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="scanResult.violativelink_list?.length">
          <el-collapse-item title="违规详情" name="violative">
            <div v-for="(item, idx) in scanResult.violativelink_list" :key="idx" class="result-block">
              <div class="result-block-title">问题地址: {{ item.url }}</div>
              <div v-for="(v, i) in item.violativelinkres" :key="i" class="result-block-content">{{ v }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="scanResult.diedlink_list?.length">
          <el-collapse-item title="死链详情" name="diedlink">
            <div v-for="(item, idx) in scanResult.diedlink_list" :key="idx" class="result-block">
              <div class="result-block-title">失效地址: {{ item.url }}</div>
              <div class="result-block-content">状态码: {{ item.status_code }}</div>
              <div class="result-block-source">来源: {{ item.master?.join(', ') }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-empty v-if="!scanResult.blacklink_list?.length && !scanResult.backdoor_list?.length && !scanResult.violativelink_list?.length && !scanResult.diedlink_list?.length"
          description="未发现任何威胁，网站安全状况良好！" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import { startScan, getScanStatus } from '../api/libra'

const form = reactive({ url: '', scanType: 'HomePage_Scan' })
const scanning = ref(false)
const currentTaskId = ref(null)
const progress = ref(0)
const scanResult = ref(null)

const handleStartScan = async () => {
  if (!form.url) { ElMessage.warning('请输入目标 URL'); return }
  scanning.value = true; currentTaskId.value = null; progress.value = 0; scanResult.value = null
  try {
    const res = await startScan(form.url, form.scanType)
    currentTaskId.value = res.data.task_id
    ElMessage.success('扫描任务已启动')
    pollScanStatus()
  } catch { ElMessage.error('启动扫描失败') } finally { scanning.value = false }
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
        progress.value = 100; scanResult.value = task.result; ElMessage.success('扫描完成')
      } else {
        scanning.value = false; ElMessage.error('扫描失败')
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
