<template>
  <div class="scan-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">&#128269; 安全扫描</h2>
        <p class="page-desc">输入目标 URL 或批量导入，开始全面的网站安全扫描</p>
      </div>
    </div>

    <!-- mode tabs -->
    <div class="mode-tabs">
      <el-radio-group v-model="mode" size="large">
        <el-radio-button value="single">&#128433; 单站扫描</el-radio-button>
        <el-radio-button value="batch">&#128203; 批量扫描</el-radio-button>
        <el-radio-button value="history">&#128203; 扫描记录</el-radio-button>
      </el-radio-group>
    </div>

    <!-- single scan -->
    <div v-show="mode === 'single'" class="section">
      <div class="white-card scan-form">
        <div class="form-title">&#127919; 目标站点</div>
        <el-form :model="singleForm" label-position="top">
          <el-form-item label="目标 URL">
            <el-input
              v-model="singleForm.url"
              placeholder="https://example.com"
              size="large"
              clearable
              @keyup.enter="handleSingleScan"
            >
              <template #append>
                <el-select v-model="singleForm.scanType" style="width:140px">
                  <el-option value="HomePage_Scan" label="首页" />
                  <el-option value="SecondPage_Scan" label="二级" />
                  <el-option value="AllSite_Scan" label="全站" />
                </el-select>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item v-if="settings.aiEnabled">
            <el-checkbox v-model="singleForm.aiAnalysis">&#129504; AI 智能分析</el-checkbox>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="singleLoading" @click="handleSingleScan">
              {{ singleLoading ? '扫描中...' : '&#128640; 开始扫描' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- single result -->
      <div v-if="singleResult || singleError" class="white-card result-card">
        <div v-if="singleError" class="error-box">{{ singleError }}</div>
        <div v-else-if="singleResult">
          <div class="result-header">
            <div class="result-url">{{ singleResult.url }}</div>
            <div class="result-meta">
              <el-tag :type="singleResult.status === 'success' ? 'success' : 'danger'" size="small">
                {{ singleResult.status }}
              </el-tag>
            </div>
          </div>
          <el-row :gutter="12" class="risk-row">
            <el-col :xs="12" :sm="6" :md="3">
              <div class="risk-item" :class="{danger: singleResult.blacklink_list?.length}">
                <div class="risk-num">{{ singleResult.blacklink_list?.length || 0 }}</div>
                <div class="risk-label">&#128993; 暗链</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6" :md="3">
              <div class="risk-item" :class="{danger: singleResult.backdoor_list?.length}">
                <div class="risk-num">{{ singleResult.backdoor_list?.length || 0 }}</div>
                <div class="risk-label">&#128008; 后门</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6" :md="3">
              <div class="risk-item" :class="{warn: singleResult.violativelink_list?.length}">
                <div class="risk-num">{{ singleResult.violativelink_list?.length || 0 }}</div>
                <div class="risk-label">&#128694; 违规</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6" :md="3">
              <div class="risk-item">
                <div class="risk-num">{{ singleResult.diedlink_list?.length || 0 }}</div>
                <div class="risk-label">&#9760; 死链</div>
              </div>
            </el-col>
          </el-row>
          <div v-if="singleAIResult" class="ai-box">
            <div class="ai-title">&#129504; AI 安全分析</div>
            <div class="ai-content">{{ typeof singleAIResult === 'string' ? singleAIResult : JSON.stringify(singleAIResult, null, 2) }}</div>
          </div>
          <el-collapse v-if="singleResult.blacklink_list?.length" class="detail-collapse">
            <el-collapse-item title="&#128993; 暗链详情" name="bl">
              <div v-for="(item, idx) in singleResult.blacklink_list" :key="idx" class="detail-item">
                <div class="detail-url danger">{{ item.url }}</div>
                <div v-for="(l, i) in (item.blacklinkres || [])" :key="i" class="detail-text">{{ l }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-collapse v-if="singleResult.backdoor_list?.length" class="detail-collapse">
            <el-collapse-item title="&#128008; 后门详情" name="bd">
              <div v-for="(item, idx) in singleResult.backdoor_list" :key="idx" class="detail-item">
                <div class="detail-url danger">{{ item.url }}</div>
                <div v-for="(b, i) in (item.backdoorres || [])" :key="i" class="detail-text">{{ b }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-collapse v-if="singleResult.violativelink_list?.length" class="detail-collapse">
            <el-collapse-item title="&#128694; 违规详情" name="vl">
              <div v-for="(item, idx) in singleResult.violativelink_list" :key="idx" class="detail-item">
                <div class="detail-url warn">{{ item.url }}</div>
                <div v-for="(v, i) in (item.violativelinkres || [])" :key="i" class="detail-text">{{ v }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>

    <!-- batch scan -->
    <div v-show="mode === 'batch'" class="section">
      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
          <div class="white-card scan-form">
            <div class="form-title">&#128203; 批量配置</div>
            <el-form :model="batchForm" label-position="top">
              <el-form-item label="扫描模式">
                <el-radio-group v-model="batchForm.scanType" size="default">
                  <el-radio-button value="HomePage_Scan">首页</el-radio-button>
                  <el-radio-button value="SecondPage_Scan">二级</el-radio-button>
                  <el-radio-button value="AllSite_Scan">全站</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="目标 URL 列表（一行一个）">
                <el-input
                  v-model="batchForm.urlsText"
                  type="textarea"
                  :rows="10"
                  placeholder="https://site1.com&#10;https://site2.com&#10;https://site3.com"
                  resize="vertical"
                  :disabled="submitting"
                />
                <div class="url-hint">共 {{ urlCount }} 个 URL</div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="default" :loading="submitting" @click="handleCreateBatch">
                  {{ submitting ? '创建中...' : '&#128640; 开始批量扫描' }}
                </el-button>
                <el-button size="default" @click="batchForm.urlsText = ''" :disabled="submitting">清空</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-col>

        <el-col :xs="24" :lg="12">
          <div v-if="activeBatch" class="white-card batch-card">
            <div class="batch-header">
              <div>
                <div class="batch-title">&#128269; 批次扫描中</div>
                <div class="batch-meta">ID: <code>{{ activeBatch.id?.substring(0, 8) }}</code> · {{ activeBatch.completed }}/{{ activeBatch.total }}</div>
              </div>
              <el-tag type="primary">进行中</el-tag>
            </div>
            <el-progress :percentage="Math.round((activeBatch.completed / activeBatch.total) * 100)" :stroke-width="10" status="primary" />
            <el-row :gutter="8" class="batch-stats">
              <el-col :span="6"><div class="batch-stat"><div class="batch-stat-num">{{ activeBatch.total }}</div><div class="batch-stat-label">总计</div></div></el-col>
              <el-col :span="6"><div class="batch-stat success"><div class="batch-stat-num">{{ activeBatch.completed }}</div><div class="batch-stat-label">完成</div></div></el-col>
              <el-col :span="6"><div class="batch-stat danger"><div class="batch-stat-num">{{ activeBatch.error || 0 }}</div><div class="batch-stat-label">异常</div></div></el-col>
              <el-col :span="6"><div class="batch-stat"><div class="batch-stat-num">{{ activeBatch.total - activeBatch.completed }}</div><div class="batch-stat-label">进行中</div></div></el-col>
            </el-row>
          </div>

          <div v-else class="empty-batch">
            <div class="empty-icon">&#128203;</div>
            <div class="empty-text">在左侧输入 URL 列表，<br>点击开始批量扫描</div>
          </div>

          <div class="white-card" style="margin-top:16px">
            <div class="history-header">
              <span class="form-title" style="margin:0">&#128203; 历史批次</span>
              <el-button text size="small" @click="fetchBatches">刷新</el-button>
            </div>
            <div class="batch-list">
              <div v-if="batchesLoading" style="text-align:center;padding:20px;color:#8a94a6">加载中...</div>
              <div v-else-if="batches.length === 0" class="empty-tip">暂无历史记录</div>
              <div v-else>
                <div v-for="b in batches.slice(0, 5)" :key="b.id" class="batch-item">
                  <div class="batch-left">
                    <span class="batch-id">{{ b.id?.substring(0, 8) }}</span>
                    <span class="batch-urls">{{ b.total }} 个 URL</span>
                  </div>
                  <div class="batch-right">
                    <span class="batch-status" :class="b.completed === b.total ? 'done' : 'progress'">
                      {{ b.completed === b.total ? '&#10004;' : '&#8987;' }} {{ b.completed }}/{{ b.total }}
                    </span>
                    <span v-if="b.error" class="batch-error">&#9888; {{ b.error }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- history -->
    <div v-show="mode === 'history'" class="section">
      <div class="white-card">
        <div class="filter-bar">
          <el-input v-model="historySearch" placeholder="搜索 URL" clearable size="default" style="max-width:280px" @input="debounceHistory">
            <template #prefix><span>&#128269;</span></template>
          </el-input>
          <el-select v-model="historyStatus" size="default" style="width:130px" clearable placeholder="状态" @change="fetchHistory">
            <el-option value="success" label="&#10004; 成功" />
            <el-option value="error" label="&#9888; 异常" />
            <el-option value="running" label="&#8987; 进行中" />
          </el-select>
        </div>

        <el-table :data="historyTasks" stripe size="small" v-loading="historyLoading" empty-text="暂无记录">
          <el-table-column label="URL" prop="url" min-width="180" show-overflow-tooltip />
          <el-table-column label="扫描类型" width="100">
            <template #default="{ row }">{{ scanTypeLabel(row.scan_type) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <span :class="'status-dot status-' + row.status">{{ statusLabel(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="威胁" width="140" align="center">
            <template #default="{ row }">
              <span class="threat-badges">
                <span v-if="row.blacklink_count" class="badge danger">&#128993;{{ row.blacklink_count }}</span>
                <span v-if="row.backdoor_count" class="badge danger">&#128008;{{ row.backdoor_count }}</span>
                <span v-if="row.violative_count" class="badge warn">&#128694;{{ row.violative_count }}</span>
                <span v-if="!row.blacklink_count && !row.backdoor_count && !row.violative_count">-</span>
              </span>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="140">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="viewTaskResult(row)">查看</el-button>
              <el-button text size="small" @click="exportReport(row, 'pdf')">&#128229;</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-bar" v-if="historyTotal > historyPageSize">
          <el-pagination v-model:current-page="historyPage" :page-size="historyPageSize" :total="historyTotal" layout="prev, pager, next" @current-change="fetchHistory" />
        </div>
      </div>

      <!-- detail dialog -->
      <el-dialog v-model="detailVisible" :title="'&#128203; ' + (selectedTask?.url || '')" width="700px" destroy-on-close>
        <div v-if="selectedTask">
          <div class="result-meta" style="margin-bottom:12px">
            <el-tag :type="selectedTask.status === 'success' ? 'success' : 'danger'" size="small">{{ selectedTask.status }}</el-tag>
            <span style="margin-left:8px;font-size:12px;color:#8a94a6">{{ scanTypeLabel(selectedTask.scan_type) }} · {{ formatTime(selectedTask.created_at) }}</span>
          </div>
          <el-row :gutter="10" class="risk-row">
            <el-col :xs="12" :sm="6"><div class="risk-item" :class="{danger: selectedTask.blacklink_count}"><div class="risk-num">{{ selectedTask.blacklink_count || 0 }}</div><div class="risk-label">&#128993; 暗链</div></div></el-col>
            <el-col :xs="12" :sm="6"><div class="risk-item" :class="{danger: selectedTask.backdoor_count}"><div class="risk-num">{{ selectedTask.backdoor_count || 0 }}</div><div class="risk-label">&#128008; 后门</div></div></el-col>
            <el-col :xs="12" :sm="6"><div class="risk-item" :class="{warn: selectedTask.violative_count}"><div class="risk-num">{{ selectedTask.violative_count || 0 }}</div><div class="risk-label">&#128694; 违规</div></div></el-col>
            <el-col :xs="12" :sm="6"><div class="risk-item"><div class="risk-num">{{ selectedTask.diedlink_count || 0 }}</div><div class="risk-label">&#9760; 死链</div></div></el-col>
          </el-row>
          <el-collapse v-if="taskDetail?.blacklink_list?.length" class="detail-collapse">
            <el-collapse-item title="&#128993; 暗链" name="bl">
              <div v-for="(item, idx) in taskDetail.blacklink_list" :key="idx" class="detail-item">
                <div class="detail-url danger">{{ item.url }}</div>
                <div v-for="(l, i) in (item.blacklinkres || [])" :key="i" class="detail-text">{{ l }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-collapse v-if="taskDetail?.backdoor_list?.length" class="detail-collapse">
            <el-collapse-item title="&#128008; 后门" name="bd">
              <div v-for="(item, idx) in taskDetail.backdoor_list" :key="idx" class="detail-item">
                <div class="detail-url danger">{{ item.url }}</div>
                <div v-for="(b, i) in (item.backdoorres || [])" :key="i" class="detail-text">{{ b }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-collapse v-if="taskDetail?.violativelink_list?.length" class="detail-collapse">
            <el-collapse-item title="&#128694; 违规" name="vl">
              <div v-for="(item, idx) in taskDetail.violativelink_list" :key="idx" class="detail-item">
                <div class="detail-url warn">{{ item.url }}</div>
                <div v-for="(v, i) in (item.violativelinkres || [])" :key="i" class="detail-text">{{ v }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/libra'

const mode = ref('single')
const singleForm = ref({ url: '', scanType: 'HomePage_Scan', aiAnalysis: true })
const singleLoading = ref(false)
const singleResult = ref(null)
const singleAIResult = ref(null)
const singleError = ref('')

const batchForm = ref({ urlsText: '', scanType: 'HomePage_Scan' })
const submitting = ref(false)
const batches = ref([])
const batchesLoading = ref(false)
const activeBatch = ref(null)
const urlCount = computed(() => {
  return (batchForm.value.urlsText || '').split('\n').map(u => u.trim()).filter(u => u.length > 0).length
})

const historyTasks = ref([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = 20
const historyLoading = ref(false)
const historySearch = ref('')
const historyStatus = ref('')
const selectedTask = ref(null)
const taskDetail = ref(null)
const detailVisible = ref(false)
const settings = ref({ aiEnabled: false })

const scanTypeLabel = (t) => ({ HomePage_Scan: '首页', SecondPage_Scan: '二级', AllSite_Scan: '全站', CustomPage_Scan: '自定义' }[t] || t)
const statusLabel = (s) => ({ success: 'OK', error: 'ERR', running: 'RUN', pending: 'PEN' }[s] || s)
const formatTime = (iso) => {
  if (!iso) return '-'
  try { return new Date(iso).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' }) } catch { return iso }
}

let historyTimer = null
const debounceHistory = () => {
  clearTimeout(historyTimer)
  historyTimer = setTimeout(() => { historyPage.value = 1; fetchHistory() }, 400)
}

const handleSingleScan = () => {
  let url = singleForm.value.url.trim()
  if (!url) { ElMessage.warning('请输入目标 URL'); return }
  if (!url.startsWith('http')) url = 'https://' + url
  singleLoading.value = true
  singleError.value = ''
  singleResult.value = null
  singleAIResult.value = null
  api.post('/scan', { url, scan_type: singleForm.value.scanType })
    .then(r => { pollSingleTask(r.data.task_id) })
    .catch(e => { singleError.value = '创建任务失败: ' + (e.message || ''); singleLoading.value = false })
}

const pollSingleTask = (taskId) => {
  api.get('/scan/' + taskId).then(r => {
    const task = r.data
    if (task.status === 'pending' || task.status === 'running') {
      setTimeout(() => pollSingleTask(taskId), 2000)
    } else {
      singleLoading.value = false
      if (task.status === 'success' && task.result) {
        singleResult.value = task.result
        if (singleForm.value.aiAnalysis) {
          api.post('/ai/analyze', { result: task.result }).then(ar => { singleAIResult.value = ar.data }).catch(() => {})
        }
      } else if (task.status === 'error') {
        singleError.value = task.error || '扫描失败'
      }
    }
  }).catch(() => setTimeout(() => pollSingleTask(taskId), 3000))
}

const handleCreateBatch = () => {
  const urls = (batchForm.value.urlsText || '').split('\n').map(u => u.trim()).filter(u => u)
  if (urls.length === 0) { ElMessage.warning('请输入至少一个 URL'); return }
  submitting.value = true
  api.post('/batch', { urls, scan_type: batchForm.value.scanType })
    .then(r => {
      ElMessage.success({ message: '已创建批量任务，包含 ' + urls.length + ' 个 URL', duration: 3000 })
      submitting.value = false
      batchForm.value.urlsText = ''
      fetchBatches()
    })
    .catch(e => { ElMessage.error('创建失败: ' + (e.message || '')); submitting.value = false })
}

const fetchBatches = () => {
  batchesLoading.value = true
  api.get('/batch').then(r => {
    batches.value = r.data.batches || []
    activeBatch.value = batches.value.find(b => b.completed < b.total && !b.error) || null
  }).catch(() => {}).finally(() => { batchesLoading.value = false })
}

const fetchHistory = () => {
  historyLoading.value = true
  const params = new URLSearchParams({ page: historyPage.value, page_size: historyPageSize, search: historySearch.value, status: historyStatus.value })
  api.get('/tasks/paginated?' + params.toString())
    .then(r => { historyTasks.value = r.data.tasks || []; historyTotal.value = r.data.total || 0 })
    .catch(() => { historyTasks.value = [] })
    .finally(() => { historyLoading.value = false })
}

const viewTaskResult = (t) => {
  selectedTask.value = t
  detailVisible.value = true
  if (t.result) {
    taskDetail.value = typeof t.result === 'string' ? JSON.parse(t.result) : t.result
  } else {
    api.get('/scan/' + t.id).then(r => { taskDetail.value = r.data.result || null }).catch(() => { taskDetail.value = null })
  }
}

const exportReport = (t, format) => {
  window.open('http://210.44.49.21:5188/api/report/' + t.id + '/' + format, '_blank')
}

let pollBatchTimer = null
onMounted(() => { fetchBatches(); fetchHistory(); pollBatchTimer = setInterval(fetchBatches, 8000) })
onUnmounted(() => { clearInterval(pollBatchTimer) })
</script>

<style scoped>
.scan-page { color: #1a1a2e; }
.page-header { margin-bottom: 20px; }
.page-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: #8a94a6; }
.mode-tabs { margin-bottom: 20px; }
.section {}

.white-card { background: #ffffff; border-radius: 14px; padding: 20px; border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 16px; }
.scan-form {}
.form-title { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }

.result-card { margin-top: 16px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.result-url { font-size: 14px; font-weight: 600; color: #1a1a2e; word-break: break-all; }
.result-meta { display: flex; align-items: center; gap: 8px; }

.risk-row { margin: 12px 0; }
.risk-item { background: #f8f9fb; border-radius: 8px; padding: 10px; text-align: center; border: 1px solid #e8eaed; }
.risk-item.danger { background: #fff0f0; border-color: #ffcdd2; }
.risk-item.warn { background: #fff8e0; border-color: #ffe0b2; }
.risk-num { font-size: 22px; font-weight: 800; color: #1a1a2e; }
.risk-label { font-size: 11px; color: #8a94a6; margin-top: 2px; }

.ai-box { background: #f0f4ff; border-radius: 10px; padding: 12px 14px; margin: 12px 0; }
.ai-title { font-size: 13px; font-weight: 600; color: #4f8ef7; margin-bottom: 6px; }
.ai-content { font-size: 12px; color: #1a1a2e; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }

.detail-collapse { margin-top: 8px; }
.detail-item { background: #f8f9fb; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; }
.detail-url { font-size: 13px; font-weight: 500; margin-bottom: 2px; word-break: break-all; }
.detail-url.danger { color: #f44; }
.detail-url.warn { color: #ff9800; }
.detail-text { font-size: 12px; color: #5a6474; margin-bottom: 1px; word-break: break-all; }

.url-hint { font-size: 12px; color: #8a94a6; margin-top: 4px; }

.batch-card { border-left: 4px solid #4f8ef7; margin-bottom: 16px; }
.batch-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.batch-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px; }
.batch-meta { font-size: 12px; color: #8a94a6; }
.batch-stats { margin-top: 12px; }
.batch-stat { background: #f8f9fb; border-radius: 8px; padding: 10px; text-align: center; }
.batch-stat.success { background: #e8faf0; }
.batch-stat.danger { background: #fff0f0; }
.batch-stat-num { font-size: 20px; font-weight: 800; color: #1a1a2e; }
.batch-stat-label { font-size: 11px; color: #8a94a6; margin-top: 2px; }

.empty-batch { background: #ffffff; border-radius: 14px; padding: 40px; border: 1px solid #e8eaed; text-align: center; margin-bottom: 16px; }
.empty-icon { font-size: 40px; margin-bottom: 10px; }
.empty-text { font-size: 13px; color: #8a94a6; line-height: 1.6; }

.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.batch-list { max-height: 400px; overflow-y: auto; }
.batch-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-radius: 8px; margin-bottom: 4px; background: #f8f9fb; flex-wrap: wrap; gap: 4px; }
.batch-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.batch-id { font-size: 12px; color: #4f8ef7; font-family: 'Courier New', monospace; }
.batch-urls { font-size: 12px; color: #1a1a2e; }
.batch-right { display: flex; align-items: center; gap: 8px; }
.batch-status { font-size: 12px; }
.batch-status.done { color: #00c853; }
.batch-status.progress { color: #4f8ef7; }
.batch-error { font-size: 11px; color: #f44; }

.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }

.threat-badges { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
.badge { font-size: 11px; padding: 1px 6px; border-radius: 6px; font-weight: 500; }
.badge.danger { background: #fff0f0; color: #f44; }
.badge.warn { background: #fff8e0; color: #ff9800; }

.status-dot { font-size: 12px; }
.status-dot.status-success { color: #00c853; }
.status-dot.status-error { color: #f44; }
.status-dot.status-running { color: #4f8ef7; }
.status-dot.status-pending { color: #8a94a6; }

.pagination-bar { display: flex; justify-content: center; margin-top: 16px; }
.empty-tip { text-align: center; padding: 24px; color: #8a94a6; font-size: 13px; }
.error-box { background: #fff0f0; border: 1px solid #ffcdd2; border-radius: 8px; padding: 12px; color: #f44; font-size: 13px; }
</style>
