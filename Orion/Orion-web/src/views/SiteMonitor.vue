<template>
  <div class="monitor-page">

    <!-- 椤甸潰鏍囬 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">馃尅锔?缃戠珯鐘舵€佺洃鎺?/h2>
        <p class="page-desc">瀹炴椂鎺㈡祴缃戠珯鍙揪鎬с€佸搷搴旀椂闂翠笌 SSL 璇佷功鐘舵€?/p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="dialogFormVisible = true">
          <el-icon><Plus /></el-icon> 娣诲姞鐩戞帶
        </el-button>
        <el-button type="success" @click="handleCheckAll" :loading="checkingAll">
          馃攧 绔嬪嵆妫€娴嬪叏閮?        </el-button>
        <el-button @click="fetchMonitors" :icon="Refresh" circle />
      </div>
    </div>

    <!-- 缁熻鍗＄墖 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon blue">馃彚</div>
        <div class="stat-body">
          <div class="stat-num">{{ stats.total || 0 }}</div>
          <div class="stat-label">鐩戞帶鎬绘暟</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon green">鉁?/div>
        <div class="stat-body">
          <div class="stat-num green">{{ stats.online || 0 }}</div>
          <div class="stat-label">鍦ㄧ嚎</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon red">鉂?/div>
        <div class="stat-body">
          <div class="stat-num red">{{ stats.offline || 0 }}</div>
          <div class="stat-label">绂荤嚎</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon orange">鈿狅笍</div>
        <div class="stat-body">
          <div class="stat-num orange">{{ stats.error || 0 }}</div>
          <div class="stat-label">寮傚父</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon">馃攼</div>
        <div class="stat-body">
          <div class="stat-num" :class="stats.ssl_expired > 0 ? 'red' : stats.ssl_warn > 0 ? 'orange' : ''">
            {{ stats.ssl_warn || 0 }}
          </div>
          <div class="stat-label">SSL 鍛婅</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon">馃摗</div>
        <div class="stat-body">
          <div class="stat-num">{{ stats.avg_rtt_ms || 0 }}<span class="stat-unit">ms</span></div>
          <div class="stat-label">骞冲潎寤惰繜</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 鎼滅储杩囨护 -->
    <div class="white-card filter-card">
      <el-input v-model="search" placeholder="鎼滅储鐩戞帶鍚嶇О / URL" clearable size="default"
        style="width:300px" @input="debounceFetch">
        <template #prefix><span>馃攳</span></template>
      </el-input>
      <el-select v-model="filterStatus" size="default" style="width:140px" clearable
        placeholder="鐘舵€佺瓫閫? @change="fetchMonitors">
        <el-option value="online" label="鉁?鍦ㄧ嚎" />
        <el-option value="offline" label="鉂?绂荤嚎" />
        <el-option value="error" label="鈿狅笍 寮傚父" />
        <el-option value="unknown" label="鉂?鏈煡" />
      </el-select>
    </div>

    <!-- 鐩戞帶鍒楄〃 -->
    <div class="white-card">
      <el-table :data="filteredMonitors" stripe v-loading="loading" empty-text="鏆傛棤鐩戞帶鐩爣锛岀偣鍑讳笂鏂规坊鍔?>
        <!-- 鐘舵€佹寚绀哄櫒 -->
        <el-table-column label="鐘舵€? width="80" align="center">
          <template #default="{ row }">
            <span class="status-indicator" :class="'status-' + (row.last_status || 'unknown')">
              <span class="status-dot"></span>
            </span>
          </template>
        </el-table-column>

        <!-- 鐩戞帶鍚嶇О & URL -->
        <el-table-column label="鐩戞帶鐩爣" min-width="200">
          <template #default="{ row }">
            <div class="monitor-name">{{ row.name }}</div>
            <a :href="row.url" target="_blank" class="monitor-url">{{ row.url }}</a>
          </template>
        </el-table-column>

        <!-- HTTP 鐘舵€?-->
        <el-table-column label="HTTP鐘舵€? width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.last_status_code > 0"
              :type="row.last_status_code < 400 ? 'success' : row.last_status_code < 500 ? 'warning' : 'danger'"
              size="small">
              {{ row.last_status_code }}
            </el-tag>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>

        <!-- 鍝嶅簲鏃堕棿 -->
        <el-table-column label="鍝嶅簲鏃堕棿" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.last_rtt_ms > 0" class="rtt-value" :class="rttClass(row.last_rtt_ms)">
              {{ row.last_rtt_ms }} ms
            </span>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>

        <!-- SSL 鐘舵€?-->
        <el-table-column label="SSL 璇佷功" width="150" align="center">
          <template #default="{ row }">
            <template v-if="row.ssl_valid === 1">
              <el-tag v-if="row.ssl_days_left <= 0" type="danger" size="small">宸茶繃鏈?/el-tag>
              <el-tag v-else-if="row.ssl_days_left <= 30" type="warning" size="small">
                馃攼 {{ row.ssl_days_left }} 澶?              </el-tag>
              <el-tag v-else type="success" size="small">
                馃攼 {{ row.ssl_days_left }} 澶?              </el-tag>
            </template>
            <span v-else-if="row.ssl_valid === 0" class="ssl-bad">馃敀 鏃犳晥</span>
            <span v-else class="muted">闈濰TTPS</span>
          </template>
        </el-table-column>

        <!-- 涓婃妫€娴?-->
        <el-table-column label="涓婃妫€娴? width="150">
          <template #default="{ row }">
            <span class="check-time">{{ formatTime(row.last_checked_at) }}</span>
          </template>
        </el-table-column>

        <!-- 閿欒淇℃伅 -->
        <el-table-column label="閿欒淇℃伅" min-width="150">
          <template #default="{ row }">
            <span v-if="row.last_error" class="error-msg">{{ row.last_error }}</span>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>

        <!-- 鎿嶄綔 -->
        <el-table-column label="鎿嶄綔" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleCheck(row)" :loading="checkingId === row.id">
              馃攧
            </el-button>
            <el-button text type="info" size="small" @click="openHistory(row)">馃搳</el-button>
            <el-button text type="primary" size="small" @click="handleEdit(row)">鉁忥笍</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">馃棏锔?/el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 鍒嗛〉 -->
      <div class="pagination-bar" v-if="totalMonitors > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalMonitors"
          layout="prev, pager, next"
          @current-change="fetchMonitors"
        />
      </div>
    </div>

    <!-- 娣诲姞/缂栬緫鐩戞帶寮圭獥 -->
    <el-dialog v-model="dialogFormVisible" :title="editingMonitor ? '鉁忥笍 缂栬緫鐩戞帶' : '鉃?娣诲姞鐩戞帶'" width="520px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="鐩戞帶鍚嶇О" required>
          <el-input v-model="form.name" placeholder="渚嬪锛氶潚宀涘啘澶т富椤? clearable />
        </el-form-item>
        <el-form-item label="鐩爣 URL" required>
          <el-input v-model="form.url" placeholder="https://www.qau.edu.cn" clearable />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="妫€娴嬮棿闅旓紙绉掞級">
              <el-input-number v-model="form.check_interval" :min="10" :max="3600" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="瓒呮椂鏃堕棿锛堢锛?>
              <el-input-number v-model="form.timeout_seconds" :min="3" :max="60" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="鍚敤鐩戞帶">
          <el-switch v-model="formEnabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogFormVisible = false">鍙栨秷</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ editingMonitor ? '淇濆瓨淇敼' : '纭娣诲姞' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 妫€娴嬪巻鍙插脊绐?-->
    <el-dialog v-model="dialogHistoryVisible" :title="'馃搳 ' + (historyMonitor?.name || '') + ' 妫€娴嬪巻鍙?" width="700px" destroy-on-close>
      <el-table :data="history" stripe size="small" max-height="400" v-loading="historyLoading" empty-text="鏆傛棤鍘嗗彶璁板綍">
        <el-table-column label="鐘舵€? width="80" align="center">
          <template #default="{ row }">
            <span class="status-indicator" :class="'status-' + row.status">
              <span class="status-dot"></span>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="HTTP鐘舵€? width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status_code > 0"
              :type="row.status_code < 400 ? 'success' : 'danger'" size="small">
              {{ row.status_code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="鍝嶅簲鏃堕棿" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.rtt_ms > 0">{{ row.rtt_ms }} ms</span>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>
        <el-table-column label="SSL 鍓╀綑" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.ssl_days_left >= 0">{{ row.ssl_days_left }} 澶?/span>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>
        <el-table-column label="閿欒淇℃伅" min-width="150">
          <template #default="{ row }">
            <span v-if="row.error_msg" class="error-msg">{{ row.error_msg }}</span>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>
        <el-table-column label="妫€娴嬫椂闂? width="150">
          <template #default="{ row }">{{ formatTime(row.checked_at) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus } from '@element-plus/icons-vue'
import {
  getSiteMonitors, getSiteMonitorStats, createSiteMonitor,
  updateSiteMonitor, deleteSiteMonitor, checkSiteMonitor,
  checkAllSiteMonitors, getSiteMonitorHistory,
} from '../api/Orion'

const loading = ref(false)
const checkingAll = ref(false)
const checkingId = ref(null)
const monitors = ref([])
const stats = ref({})
const totalMonitors = ref(0)
const currentPage = ref(1)
const pageSize = 50
const search = ref('')
const filterStatus = ref('')

// Dialogs
const dialogFormVisible = ref(false)
const dialogHistoryVisible = ref(false)
const editingMonitor = ref(null)
const saving = ref(false)
const formEnabled = ref(true)

// Form
const form = ref({
  name: '', url: '', check_interval: 60, timeout_seconds: 10, enabled: 1
})

// History
const historyMonitor = ref(null)
const history = ref([])
const historyLoading = ref(false)

const filteredMonitors = computed(() => {
  if (!filterStatus.value) return monitors.value
  return monitors.value.filter(m => m.last_status === filterStatus.value)
})

const rttClass = (ms) => {
  if (ms < 100) return 'rtt-good'
  if (ms < 500) return 'rtt-warn'
  return 'rtt-bad'
}

// 鈹€鈹€ Fetch 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

const fetchMonitors = () => {
  loading.value = true
  getSiteMonitors({ page: currentPage.value, page_size: pageSize, search: search.value })
    .then(r => {
      monitors.value = r.data.monitors || []
      totalMonitors.value = r.data.total || 0
    })
    .catch(e => ElMessage.error('鑾峰彇鐩戞帶鍒楄〃澶辫触: ' + (e.message || '')))
    .finally(() => loading.value = false)
}

const fetchStats = () => {
  getSiteMonitorStats().then(r => { stats.value = r.data || {} }).catch(() => {})
}

// 鈹€鈹€ CRUD 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

const handleSave = () => {
  if (!form.value.name.trim()) { ElMessage.warning('璇疯緭鍏ョ洃鎺у悕绉?); return }
  if (!form.value.url.trim()) { ElMessage.warning('璇疯緭鍏ョ洰鏍?URL'); return }
  saving.value = true

  const payload = {
    ...form.value,
    enabled: formEnabled.value ? 1 : 0,
  }

  const op = editingMonitor.value
    ? updateSiteMonitor(editingMonitor.value.id, payload)
    : createSiteMonitor(payload)

  op.then(() => {
    ElMessage.success(editingMonitor.value ? '鐩戞帶宸叉洿鏂? : '鐩戞帶宸叉坊鍔?)
    dialogFormVisible.value = false
    editingMonitor.value = null
    fetchMonitors()
    fetchStats()
  }).catch(e => {
    ElMessage.error('淇濆瓨澶辫触: ' + (e.response?.data?.error || e.message || ''))
  }).finally(() => { saving.value = false })
}

const handleEdit = (row) => {
  editingMonitor.value = row
  form.value = { name: row.name, url: row.url, check_interval: row.check_interval || 60, timeout_seconds: row.timeout_seconds || 10 }
  formEnabled.value = row.enabled === 1
  dialogFormVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`纭鍒犻櫎鐩戞帶 "${row.name}" ?`, '鍒犻櫎纭', { type: 'warning' }).then(() => {
    deleteSiteMonitor(row.id).then(() => {
      ElMessage.success('宸插垹闄?)
      fetchMonitors()
      fetchStats()
    }).catch(() => ElMessage.error('鍒犻櫎澶辫触'))
  }).catch(() => {})
}

// 鈹€鈹€ Check 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

const handleCheck = (row) => {
  checkingId.value = row.id
  checkSiteMonitor(row.id)
    .then(() => {
      ElMessage.success({ message: `${row.name}: ${row.url} 妫€娴嬪畬鎴恅, duration: 3000 })
      fetchMonitors()
      fetchStats()
    })
    .catch(e => ElMessage.error('妫€娴嬪け璐? ' + (e.message || '')))
    .finally(() => { checkingId.value = null })
}

const handleCheckAll = () => {
  checkingAll.value = true
  checkAllSiteMonitors()
    .then(r => {
      ElMessage.success({ message: `宸插畬鎴?${r.data.checked || 0} 涓珯鐐圭殑妫€娴媊, duration: 3000 })
      fetchMonitors()
      fetchStats()
    })
    .catch(e => ElMessage.error('鎵归噺妫€娴嬪け璐? ' + (e.message || '')))
    .finally(() => { checkingAll.value = false })
}

// 鈹€鈹€ History 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

const openHistory = (row) => {
  historyMonitor.value = row
  dialogHistoryVisible.value = true
  historyLoading.value = true
  getSiteMonitorHistory(row.id)
    .then(r => { history.value = r.data.history || [] })
    .catch(() => ElMessage.error('鑾峰彇鍘嗗彶璁板綍澶辫触'))
    .finally(() => { historyLoading.value = false })
}

// 鈹€鈹€ Helpers 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

const formatTime = (iso) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

let debounceTimer = null
const debounceFetch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { currentPage.value = 1; fetchMonitors() }, 400)
}

// Auto-refresh every 60 seconds
let autoRefreshTimer = null
onMounted(() => {
  fetchMonitors()
  fetchStats()
  autoRefreshTimer = setInterval(() => {
    fetchMonitors()
    fetchStats()
  }, 60000)
})
onUnmounted(() => { clearInterval(autoRefreshTimer) })
</script>

<style scoped>
.monitor-page { color: #1a1a2e; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 20px;
}
.page-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: #8a94a6; }
.header-actions { display: flex; gap: 8px; align-items: center; }

.white-card {
  background: #ffffff; border-radius: 14px; padding: 20px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 16px;
}
.filter-card { padding: 14px 20px; }

.stat-row { margin-bottom: 4px; }
.stat-card {
  display: flex; align-items: center; gap: 12px;
  background: #ffffff; border-radius: 14px; padding: 16px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.stat-icon { font-size: 24px; }
.stat-body { flex: 1; }
.stat-num { font-size: 24px; font-weight: 800; color: #4f8ef7; line-height: 1; }
.stat-num.green { color: #00c853; }
.stat-num.red { color: #f44; }
.stat-num.orange { color: #ff9800; }
.stat-label { font-size: 11px; color: #8a94a6; margin-top: 4px; }
.stat-unit { font-size: 12px; font-weight: 400; color: #8a94a6; margin-left: 2px; }

.status-indicator { display: flex; align-items: center; justify-content: center; }
.status-dot {
  width: 10px; height: 10px; border-radius: 50%; display: inline-block;
}
.status-indicator.status-online .status-dot { background: #00c853; box-shadow: 0 0 6px #00c853; }
.status-indicator.status-offline .status-dot { background: #f44; box-shadow: 0 0 6px #f44; }
.status-indicator.status-error .status-dot { background: #ff9800; box-shadow: 0 0 6px #ff9800; }
.status-indicator.status-unknown .status-dot { background: #8a94a6; }

.monitor-name { font-weight: 600; color: #1a1a2e; font-size: 13px; }
.monitor-url { font-size: 12px; color: #4f8ef7; text-decoration: none; }
.monitor-url:hover { text-decoration: underline; }

.rtt-value { font-size: 12px; font-weight: 600; }
.rtt-good { color: #00c853; }
.rtt-warn { color: #ff9800; }
.rtt-bad { color: #f44; }

.ssl-bad { font-size: 12px; color: #f44; font-weight: 600; }

.check-time { font-size: 12px; color: #5a6474; }
.error-msg { font-size: 12px; color: #f44; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; max-width: 200px; }
.muted { font-size: 12px; color: #8a94a6; }

.pagination-bar { display: flex; justify-content: center; margin-top: 16px; }
</style>
