<template>
  <div class="batch-page">
    <div class="page-header">
      <h2 class="page-title">馃搵 鎵归噺鎵弿</h2>
      <el-button @click="fetchBatches" :icon="Refresh" circle />
    </div>

    <!-- 鍒涘缓鎵归噺浠诲姟 -->
    <div class="batch-form-card">
      <el-form :model="form" label-position="top">
        <el-form-item label="鎵弿妯″紡">
          <el-radio-group v-model="form.scanType" size="large">
            <el-radio-button value="HomePage_Scan">馃彔 棣栭〉鎵弿</el-radio-button>
            <el-radio-button value="SecondPage_Scan">浜岀骇椤甸潰鎵弿</el-radio-button>
            <el-radio-button value="AllSite_Scan">馃寪 鍏ㄧ珯鎵弿</el-radio-button>
            <el-radio-button value="CustomPage_Scan">馃搫 鑷畾涔夋壂鎻?/el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="鐩爣 URL 鍒楄〃锛堜竴琛屼竴涓級">
          <el-input
            v-model="form.urlsText"
            type="textarea"
            :rows="8"
            placeholder="https://site1.com&#10;https://site2.com&#10;https://site3.com"
            resize="vertical"
            :disabled="submitting"
          />
          <div class="url-hint">
            鍏?{{ urlCount }} 涓?URL
            <span v-if="form.urlsText" class="url-count">{{ urlCount }} 涓?/span>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            @click="handleCreateBatch"
            style="width: 200px"
          >
            {{ submitting ? '鍒涘缓涓?..' : '馃殌 寮€濮嬫壒閲忔壂鎻? }}
          </el-button>
          <el-button size="large" @click="form.urlsText = ''" :disabled="submitting">
            娓呯┖
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 娲昏穬鎵规 -->
    <div v-if="activeBatch" class="batch-progress-card">
      <div class="batch-progress-header">
        <div>
          <h3>馃攳 鎵规鎵弿涓?/h3>
          <p class="batch-meta">
            鎵规ID: <code>{{ activeBatch.id }}</code> 路
            浠诲姟鏁? {{ activeBatch.total }} 路
            绫诲瀷: {{ scanTypeLabel(activeBatch.scan_type) }}
          </p>
        </div>
        <el-tag type="primary" size="large">杩涜涓?/el-tag>
      </div>

      <el-progress
        :percentage="Math.round((activeBatch.completed / activeBatch.total) * 100)"
        :stroke-width="12"
        status="primary"
      />

      <el-row :gutter="12" class="batch-stats">
        <el-col :span="6">
          <div class="batch-stat">
            <div class="batch-stat-num">{{ activeBatch.total }}</div>
            <div class="batch-stat-label">鎬昏</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="batch-stat success">
            <div class="batch-stat-num">{{ activeBatch.success }}</div>
            <div class="batch-stat-label">鎴愬姛</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="batch-stat error">
            <div class="batch-stat-num">{{ activeBatch.error }}</div>
            <div class="batch-stat-label">寮傚父</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="batch-stat running">
            <div class="batch-stat-num">{{ activeBatch.running + activeBatch.pending }}</div>
            <div class="batch-stat-label">杩涜涓?/div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 鍘嗗彶鎵规 -->
    <div class="section">
      <h3 class="section-title">馃摐 鍘嗗彶鎵规</h3>

      <el-table :data="batches" stripe v-loading="loading" empty-text="鏆傛棤鎵归噺鎵弿璁板綍">
        <el-table-column label="鎵规ID" prop="id" width="100">
          <template #default="{ row }">
            <code style="color: #00d4ff">{{ row.id }}</code>
          </template>
        </el-table-column>
        <el-table-column label="鎵弿妯″紡" prop="scan_type" width="130">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ scanTypeLabel(row.scan_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="浠诲姟鏁? prop="total" width="80" align="center" />
        <el-table-column label="鎴愬姛" prop="success" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #00e676">{{ row.success || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="寮傚父" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #ff5252">{{ (row.error || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="鍒涘缓鏃堕棿" prop="created_at" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="鎿嶄綔" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="viewBatchDetail(row)">
              璇︽儏
            </el-button>
            <el-button text type="danger" size="small" @click="handleDeleteBatch(row.id)">
              鍒犻櫎
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 鎵规璇︽儏寮圭獥 -->
    <el-dialog v-model="detailVisible" title="鎵规璇︽儏" width="900px" destroy-on-close>
      <div v-if="detailData">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="鎵规ID"><code style="color:#00d4ff">{{ detailData.id }}</code></el-descriptions-item>
          <el-descriptions-item label="鎵弿绫诲瀷">{{ scanTypeLabel(detailData.scan_type) }}</el-descriptions-item>
          <el-descriptions-item label="鍒涘缓鏃堕棿">{{ formatTime(detailData.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-row :gutter="12" class="batch-stats">
          <el-col :span="6"><div class="batch-stat"><div class="batch-stat-num">{{ detailData.total }}</div><div class="batch-stat-label">鎬昏</div></div></el-col>
          <el-col :span="6"><div class="batch-stat success"><div class="batch-stat-num">{{ detailData.success || 0 }}</div><div class="batch-stat-label">鎴愬姛</div></div></el-col>
          <el-col :span="6"><div class="batch-stat error"><div class="batch-stat-num">{{ detailData.error || 0 }}</div><div class="batch-stat-label">寮傚父</div></div></el-col>
          <el-col :span="6"><div class="batch-stat"><div class="batch-stat-num">{{ (detailData.running || 0) + (detailData.pending || 0) }}</div><div class="batch-stat-label">杩涜涓?/div></div></el-col>
        </el-row>

        <el-divider />

        <el-table :data="detailResults" size="small" max-height="400" empty-text="鏆傛棤缁撴灉">
          <el-table-column label="URL" prop="taskurl" min-width="180" show-overflow-tooltip />
          <el-table-column label="鐘舵€? prop="status" width="80">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="榛戦摼" prop="blacklink_count" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.blacklink_count ? 'danger-text' : ''">{{ row.blacklink_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="鍚庨棬" prop="backdoor_count" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.backdoor_count ? 'danger-text' : ''">{{ row.backdoor_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="杩濊" prop="violativelink_count" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.violativelink_count ? 'warn-text' : ''">{{ row.violativelink_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="姝婚摼" prop="diedlink_count" width="60" align="center">
            <template #default="{ row }">{{ row.diedlink_count || 0 }}</template>
          </el-table-column>
          <el-table-column label="鎶ュ憡" width="100" fixed="right">
            <template #default="{ row }">
              <el-dropdown size="small" @command="(fmt) => exportReport(row.task_id, fmt)">
                <el-button text type="primary" size="small">瀵煎嚭 鈫?/el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="pdf">馃搫 PDF 鎶ュ憡</el-dropdown-item>
                    <el-dropdown-item command="csv">馃搳 CSV 瀵煎嚭</el-dropdown-item>
                    <el-dropdown-item command="json">馃搵 JSON 鏁版嵁</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { createBatch, getBatchStatus, listBatches, deleteBatch, getReportUrl } from '../api/Orion'

const form = reactive({
  scanType: 'HomePage_Scan',
  urlsText: '',
})
const submitting = ref(false)
const batches = ref([])
const loading = ref(false)
const activeBatch = ref(null)
const detailVisible = ref(false)
const detailData = ref(null)
let pollTimer = null

const urlCount = computed(() => {
  return form.urlsText.split('\n').filter(u => u.trim()).length
})

const fetchBatches = async () => {
  loading.value = true
  try {
    const res = await listBatches()
    batches.value = res.data.batches || []
    // Check if any batch is still running
    const running = batches.value.find(b =>
      b.task_ids && b.task_ids.length > 0 &&
      b.completed < b.total
    )
    if (running) {
      activeBatch.value = running
      startPolling()
    } else {
      activeBatch.value = null
      stopPolling()
    }
  } catch (e) {
    ElMessage.error('鑾峰彇鎵规鍒楄〃澶辫触')
  } finally {
    loading.value = false
  }
}

const handleCreateBatch = async () => {
  const urls = form.urlsText.split('\n').map(u => u.trim()).filter(u => u)
  if (!urls.length) {
    ElMessage.warning('璇疯緭鍏ヨ嚦灏戜竴涓?URL')
    return
  }
  submitting.value = true
  try {
    const res = await createBatch(urls, form.scanType)
    ElMessage.success(`鎵归噺鎵弿宸插垱寤猴紝鍏?${res.data.total} 涓换鍔)
    await fetchBatches()
    // Auto-watch the new batch
    const newBatch = batches.value.find(b => b.id === res.data.batch_id)
    if (newBatch) {
      activeBatch.value = newBatch
      startPolling()
    }
  } catch (e) {
    ElMessage.error('鍒涘缓鎵归噺鎵弿澶辫触')
  } finally {
    submitting.value = false
  }
}

const viewBatchDetail = async (row) => {
  try {
    const res = await getBatchStatus(row.id)
    detailData.value = res.data
    detailVisible.value = true
  } catch (e) {
    ElMessage.error('鑾峰彇璇︽儏澶辫触')
  }
}

const handleDeleteBatch = async (batchId) => {
  await deleteBatch(batchId)
  ElMessage.success('宸插垹闄?)
  fetchBatches()
}

const exportReport = (taskId, fmt) => {
  window.open(getReportUrl(taskId, fmt), '_blank')
}

const detailResults = computed(() => {
  if (!detailData.value?.results) return []
  return Object.values(detailData.value.results)
})

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!activeBatch.value) return
    try {
      const res = await getBatchStatus(activeBatch.value.id)
      activeBatch.value = res.data
      if (res.data.completed >= res.data.total) {
        activeBatch.value = null
        stopPolling()
        fetchBatches()
      }
    } catch {}
  }, 5000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const scanTypeLabel = (t) => ({
  HomePage_Scan: '棣栭〉鎵弿', SecondPage_Scan: '浜岀骇鎵弿',
  AllSite_Scan: '鍏ㄧ珯鎵弿', CustomPage_Scan: '鑷畾涔夋壂鎻?,
}[t] || t)

const statusType = (s) => ({ success: 'success', error: 'danger', timeout: 'warning', running: 'primary' }[s] || 'info')

const formatTime = (iso) => iso ? new Date(iso).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '-'

import { reactive } from 'vue'
onMounted(fetchBatches)
onUnmounted(stopPolling)
</script>

<style scoped>
.batch-page { color: #1a1a2e; }
.url-textarea textarea::placeholder { color: #8a94a6 !important; opacity: 1 !important; }
.url-textarea .el-textarea__inner { background: #ffffff !important; }

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 22px; font-weight: 600; color: #1a1a2e; }
.batch-form-card, .batch-progress-card, .section {
  background: #ffffff; border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid #e8eaed;
}
.batch-progress-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.batch-progress-header h3 { margin: 0 0 4px; color: #1a1a2e; }
.batch-meta { margin: 0; font-size: 13px; color: #5a6474; }
.batch-meta code { color: #2a6adb; background: #e8f0ff; padding: 1px 6px; border-radius: 4px; }
.url-hint { margin-top: 6px; font-size: 12px; color: #5a6474; }
.url-count { color: #2a6adb; margin-left: 8px; }
.batch-stats { margin-top: 16px; }
.batch-stat { background: #f8f9fb; border-radius: 10px; padding: 12px; text-align: center; }
.batch-stat-num { font-size: 24px; font-weight: 700; color: #1a1a2e; }
.batch-stat-label { font-size: 11px; color: #8a94a6; margin-top: 2px; }
.batch-stat.success .batch-stat-num { color: #1a9a5c; }
.batch-stat.error .batch-stat-num { color: #d93636; }
.batch-stat.running .batch-stat-num { color: #c87c00; }
.section-title { margin: 0 0 16px; font-size: 16px; color: #1a1a2e; }
.danger-text { color: #d93636; font-weight: 600; }
.warn-text { color: #c87c00; }
</style>

<style>
/* 鍏ㄥ眬瑕嗙洊 textarea placeholder */
.batch-page .el-textarea__inner::placeholder { color: #8a94a6 !important; opacity: 1 !important; }
.batch-page .el-textarea__inner { background: #ffffff !important; }
</style>
