<template>
  <div class="batch-page">
    <div class="page-header">
      <h2 class="page-title">📋 批量扫描</h2>
      <el-button @click="fetchBatches" :icon="Refresh" circle />
    </div>

    <!-- 创建批量任务 -->
    <div class="batch-form-card">
      <el-form :model="form" label-position="top">
        <el-form-item label="扫描模式">
          <el-radio-group v-model="form.scanType" size="large">
            <el-radio-button value="HomePage_Scan">🏠 首页扫描</el-radio-button>
            <el-radio-button value="SecondPage_Scan">二级页面扫描</el-radio-button>
            <el-radio-button value="AllSite_Scan">🌐 全站扫描</el-radio-button>
            <el-radio-button value="CustomPage_Scan">📄 自定义扫描</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="目标 URL 列表（一行一个）">
          <el-input
            v-model="form.urlsText"
            type="textarea"
            :rows="8"
            placeholder="https://site1.com&#10;https://site2.com&#10;https://site3.com"
            resize="vertical"
            :disabled="submitting"
          />
          <div class="url-hint">
            共 {{ urlCount }} 个 URL
            <span v-if="form.urlsText" class="url-count">{{ urlCount }} 个</span>
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
            {{ submitting ? '创建中...' : '🚀 开始批量扫描' }}
          </el-button>
          <el-button size="large" @click="form.urlsText = ''" :disabled="submitting">
            清空
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 活跃批次 -->
    <div v-if="activeBatch" class="batch-progress-card">
      <div class="batch-progress-header">
        <div>
          <h3>🔍 批次扫描中</h3>
          <p class="batch-meta">
            批次ID: <code>{{ activeBatch.id }}</code> ·
            任务数: {{ activeBatch.total }} ·
            类型: {{ scanTypeLabel(activeBatch.scan_type) }}
          </p>
        </div>
        <el-tag type="primary" size="large">进行中</el-tag>
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
            <div class="batch-stat-label">总计</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="batch-stat success">
            <div class="batch-stat-num">{{ activeBatch.success }}</div>
            <div class="batch-stat-label">成功</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="batch-stat error">
            <div class="batch-stat-num">{{ activeBatch.error }}</div>
            <div class="batch-stat-label">异常</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="batch-stat running">
            <div class="batch-stat-num">{{ activeBatch.running + activeBatch.pending }}</div>
            <div class="batch-stat-label">进行中</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 历史批次 -->
    <div class="section">
      <h3 class="section-title">📜 历史批次</h3>

      <el-table :data="batches" stripe v-loading="loading" empty-text="暂无批量扫描记录">
        <el-table-column label="批次ID" prop="id" width="100">
          <template #default="{ row }">
            <code style="color: #00d4ff">{{ row.id }}</code>
          </template>
        </el-table-column>
        <el-table-column label="扫描模式" prop="scan_type" width="130">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ scanTypeLabel(row.scan_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="任务数" prop="total" width="80" align="center" />
        <el-table-column label="成功" prop="success" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #00e676">{{ row.success || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="异常" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #ff5252">{{ (row.error || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="created_at" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="viewBatchDetail(row)">
              详情
            </el-button>
            <el-button text type="danger" size="small" @click="handleDeleteBatch(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 批次详情弹窗 -->
    <el-dialog v-model="detailVisible" title="批次详情" width="900px" destroy-on-close>
      <div v-if="detailData">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="批次ID"><code style="color:#00d4ff">{{ detailData.id }}</code></el-descriptions-item>
          <el-descriptions-item label="扫描类型">{{ scanTypeLabel(detailData.scan_type) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detailData.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-row :gutter="12" class="batch-stats">
          <el-col :span="6"><div class="batch-stat"><div class="batch-stat-num">{{ detailData.total }}</div><div class="batch-stat-label">总计</div></div></el-col>
          <el-col :span="6"><div class="batch-stat success"><div class="batch-stat-num">{{ detailData.success || 0 }}</div><div class="batch-stat-label">成功</div></div></el-col>
          <el-col :span="6"><div class="batch-stat error"><div class="batch-stat-num">{{ detailData.error || 0 }}</div><div class="batch-stat-label">异常</div></div></el-col>
          <el-col :span="6"><div class="batch-stat"><div class="batch-stat-num">{{ (detailData.running || 0) + (detailData.pending || 0) }}</div><div class="batch-stat-label">进行中</div></div></el-col>
        </el-row>

        <el-divider />

        <el-table :data="detailResults" size="small" max-height="400" empty-text="暂无结果">
          <el-table-column label="URL" prop="taskurl" min-width="180" show-overflow-tooltip />
          <el-table-column label="状态" prop="status" width="80">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="黑链" prop="blacklink_count" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.blacklink_count ? 'danger-text' : ''">{{ row.blacklink_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="后门" prop="backdoor_count" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.backdoor_count ? 'danger-text' : ''">{{ row.backdoor_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="违规" prop="violativelink_count" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.violativelink_count ? 'warn-text' : ''">{{ row.violativelink_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="死链" prop="diedlink_count" width="60" align="center">
            <template #default="{ row }">{{ row.diedlink_count || 0 }}</template>
          </el-table-column>
          <el-table-column label="报告" width="100" fixed="right">
            <template #default="{ row }">
              <el-dropdown size="small" @command="(fmt) => exportReport(row.task_id, fmt)">
                <el-button text type="primary" size="small">导出 ↓</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="pdf">📄 PDF 报告</el-dropdown-item>
                    <el-dropdown-item command="csv">📊 CSV 导出</el-dropdown-item>
                    <el-dropdown-item command="json">📋 JSON 数据</el-dropdown-item>
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
import { createBatch, getBatchStatus, listBatches, deleteBatch, getReportUrl } from '../api/libra'

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
    ElMessage.error('获取批次列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreateBatch = async () => {
  const urls = form.urlsText.split('\n').map(u => u.trim()).filter(u => u)
  if (!urls.length) {
    ElMessage.warning('请输入至少一个 URL')
    return
  }
  submitting.value = true
  try {
    const res = await createBatch(urls, form.scanType)
    ElMessage.success(`批量扫描已创建，共 ${res.data.total} 个任务`)
    await fetchBatches()
    // Auto-watch the new batch
    const newBatch = batches.value.find(b => b.id === res.data.batch_id)
    if (newBatch) {
      activeBatch.value = newBatch
      startPolling()
    }
  } catch (e) {
    ElMessage.error('创建批量扫描失败')
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
    ElMessage.error('获取详情失败')
  }
}

const handleDeleteBatch = async (batchId) => {
  await deleteBatch(batchId)
  ElMessage.success('已删除')
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
  HomePage_Scan: '首页扫描', SecondPage_Scan: '二级扫描',
  AllSite_Scan: '全站扫描', CustomPage_Scan: '自定义扫描',
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
/* 全局覆盖 textarea placeholder */
.batch-page .el-textarea__inner::placeholder { color: #8a94a6 !important; opacity: 1 !important; }
.batch-page .el-textarea__inner { background: #ffffff !important; }
</style>
