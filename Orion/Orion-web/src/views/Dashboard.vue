<template>
  <div class="dashboard">
    <!-- 椤甸潰鏍囬 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">馃搳 ORION 瀹夊叏鐩戞帶闈㈡澘</h2>
        <p class="page-desc">瀹炴椂鐩戞帶缃戠珯瀹夊叏鐘舵€侊紝璺熻釜濞佽儊瓒嬪娍</p>
      </div>
      <div class="header-actions">
        <el-button @click="fetchAll" :icon="Refresh" circle />
      </div>
    </div>

    <!-- 绗竴琛岋細鐩戞帶姒傝 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon blue">馃彚</div>
        <div class="stat-body">
          <div class="stat-num">{{ siteCount }}</div>
          <div class="stat-label">宸茬洃鎺х珯鐐?/div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon teal">馃洶锔?/div>
        <div class="stat-body">
          <div class="stat-num teal">{{ assetCount }}</div>
          <div class="stat-label">璧勪骇鎬绘暟</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon">馃攳</div>
        <div class="stat-body">
          <div class="stat-num">{{ stats.total || 0 }}</div>
          <div class="stat-label">鎬绘壂鎻忔鏁?/div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon green">鉁?/div>
        <div class="stat-body">
          <div class="stat-num green">{{ stats.success || 0 }}</div>
          <div class="stat-label">鎴愬姛瀹屾垚</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon red">鈿狅笍</div>
        <div class="stat-body">
          <div class="stat-num red">{{ stats.error || 0 }}</div>
          <div class="stat-label">寮傚父/澶辫触</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon orange">鈴?/div>
        <div class="stat-body">
          <div class="stat-num orange">{{ stats.running || 0 }}</div>
          <div class="stat-label">姝ｅ湪鎵弿</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 绗簩琛岋細濞佽儊鑱氬悎 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6"><div class="stat-card threat-card">
        <div class="stat-icon">鉀擄笍</div>
        <div class="stat-body">
          <div class="stat-num danger">{{ threats.total_blacklinks || 0 }}</div>
          <div class="stat-label">绱鏆楅摼鎬绘暟</div>
          <div class="stat-sub">鏈懆 +{{ threats.week_blacklinks || 0 }}</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card threat-card">
        <div class="stat-icon">馃悮</div>
        <div class="stat-body">
          <div class="stat-num danger">{{ threats.total_backdoors || 0 }}</div>
          <div class="stat-label">绱鍚庨棬鎬绘暟</div>
          <div class="stat-sub">鏈懆 +{{ threats.week_backdoors || 0 }}</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card threat-card">
        <div class="stat-icon">馃毇</div>
        <div class="stat-body">
          <div class="stat-num warn">{{ threats.total_violations || 0 }}</div>
          <div class="stat-label">绱杩濊鎬绘暟</div>
          <div class="stat-sub">鏈懆 +{{ threats.week_violations || 0 }}</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card">
        <div class="stat-icon">馃彚</div>
        <div class="stat-body">
          <div class="stat-num blue">{{ dashStats?.assets?.total || assetCount }}</div>
          <div class="stat-label">璧勪骇鍙戠幇</div>
          <div class="stat-sub">瀛樻椿 {{ dashStats?.assets?.active || 0 }}</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 绗笁琛岋細鍥捐〃 + 濞佽儊 Top 妯″紡 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="8">
        <div class="white-card">
          <div class="card-title">馃幆 濞佽儊绫诲瀷鍒嗗竷</div>
          <div style="height:220px">
            <v-chart :option="threatDistOption" autoresize v-if="hasThreats" />
            <el-empty v-else description="鏆傛棤濞佽儊鏁版嵁" :image-size="60" />
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="white-card">
          <div class="card-title">馃搱 鎵弿瓒嬪娍</div>
          <div style="height:220px">
            <v-chart :option="scanTrendOption" autoresize />
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="white-card">
          <div class="card-title">馃敶 楂橀鏆楅摼妯″紡 Top</div>
          <div class="top-threats" v-if="(threats.top_blacklink_patterns || []).length">
            <div v-for="(t, i) in (threats.top_blacklink_patterns || []).slice(0, 8)" :key="i" class="threat-pattern">
              <span class="pattern-rank">#{{ i+1 }}</span>
              <span class="pattern-text">{{ t.pattern.substring(0, 40) }}{{ t.pattern.length > 40 ? '...' : '' }}</span>
              <span class="pattern-count">{{ t.count }}娆?/span>
            </div>
          </div>
          <el-empty v-else description="鏆傛棤鏆楅摼鏁版嵁" :image-size="50" />
        </div>
      </el-col>
    </el-row>

    <!-- 绗洓琛岋細鏈€鏂版壂鎻忚鎯?+ 鍘嗗彶璁板綍 -->
    <el-row :gutter="16" class="bottom-row">
      <el-col :span="12">
        <div class="white-card">
          <div class="card-title">馃搵 鏈€鏂版壂鎻忚鎯?/div>
          <div v-if="!selectedTask && !scanResult" class="empty-tip">鐐瑰嚮涓嬫柟鍘嗗彶璁板綍涓殑浠诲姟鏌ョ湅璇︽儏</div>
          <div v-else-if="scanResult">
            <div class="result-header">
              <div class="result-url">{{ scanResult.taskurl || scanResult.url }}</div>
              <div class="result-meta">
                <el-tag type="info" size="small">{{ scanTypeLabel(scanResult.tasktype || scanResult.scan_type) }}</el-tag>
                <span v-if="scanResult.status === 'success'" class="status-tag success">鎴愬姛</span>
                <span v-else class="status-tag error">寮傚父</span>
              </div>
            </div>
            <el-row :gutter="10" class="risk-row">
              <el-col :span="6"><div class="risk-item" :class="{danger: scanResult.blacklink_list?.length}">
                <div class="risk-num">{{ scanResult.blacklink_list?.length || 0 }}</div>
                <div class="risk-label">鏆楅摼</div>
              </div></el-col>
              <el-col :span="6"><div class="risk-item" :class="{danger: scanResult.backdoor_list?.length}">
                <div class="risk-num">{{ scanResult.backdoor_list?.length || 0 }}</div>
                <div class="risk-label">鍚庨棬</div>
              </div></el-col>
              <el-col :span="6"><div class="risk-item" :class="{warn: scanResult.violativelink_list?.length}">
                <div class="risk-num">{{ scanResult.violativelink_list?.length || 0 }}</div>
                <div class="risk-label">杩濊</div>
              </div></el-col>
              <el-col :span="6"><div class="risk-item">
                <div class="risk-num">{{ scanResult.diedlink_list?.length || 0 }}</div>
                <div class="risk-label">姝婚摼</div>
              </div></el-col>
            </el-row>
            <el-collapse v-if="scanResult.blacklink_list?.length" class="detail-collapse">
              <el-collapse-item title="馃敆 鏆楅摼璇︽儏" name="bl">
                <div v-for="(item, idx) in scanResult.blacklink_list" :key="idx" class="detail-item">
                  <div class="detail-url danger">{{ item.url }}</div>
                  <div v-for="(l, i) in item.blacklinkres" :key="i" class="detail-text">{{ l }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
            <el-collapse v-if="scanResult.backdoor_list?.length" class="detail-collapse">
              <el-collapse-item title="馃悮 鍚庨棬璇︽儏" name="bd">
                <div v-for="(item, idx) in scanResult.backdoor_list" :key="idx" class="detail-item">
                  <div class="detail-url danger">{{ item.url }}</div>
                  <div v-for="(b, i) in item.backdoorres" :key="i" class="detail-text">{{ b }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
            <el-collapse v-if="scanResult.violativelink_list?.length" class="detail-collapse">
              <el-collapse-item title="馃毇 杩濊璇︽儏" name="vl">
                <div v-for="(item, idx) in scanResult.violativelink_list" :key="idx" class="detail-item">
                  <div class="detail-url warn">{{ item.url }}</div>
                  <div v-for="(v, i) in item.violativelinkres" :key="i" class="detail-text">{{ v }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </el-col>

      <!-- 鍘嗗彶璁板綍 -->
      <el-col :span="12">
        <div class="white-card">
          <div class="card-title">馃摐 鎵弿鍘嗗彶</div>
          <div class="filter-bar">
            <el-input v-model="historySearch" placeholder="鎼滅储 URL" clearable size="small" style="width:180px" @input="debounceHistory">
              <template #prefix><span>馃攳</span></template>
            </el-input>
            <el-select v-model="historyStatus" size="small" style="width:120px" clearable placeholder="鐘舵€? @change="fetchHistory">
              <el-option value="success" label="鉁?鎴愬姛" />
              <el-option value="error" label="鈿狅笍 寮傚父" />
              <el-option value="running" label="鈴?杩涜涓? />
              <el-option value="pending" label="馃搵 寰呭鐞? />
            </el-select>
          </div>
          <div class="history-list">
            <div v-if="historyLoading" style="text-align:center;padding:20px;color:#8a94a6">鍔犺浇涓?..</div>
            <div v-else-if="historyTasks.length === 0" class="empty-tip">鏆傛棤鍘嗗彶璁板綍</div>
            <div v-else>
              <div v-for="t in historyTasks" :key="t.id"
                class="history-item"
                :class="{selected: selectedTask?.id === t.id}"
                @click="selectTask(t)">
                <div class="history-left">
                  <span class="history-status" :class="'status-' + t.status">
                    {{ statusLabel(t.status) }}
                  </span>
                  <span class="history-url">{{ t.url }}</span>
                </div>
                <div class="history-right">
                  <span class="history-threats" v-if="(t.blacklink_count || t.backdoor_count || t.violative_count)">
                    馃敆{{ t.blacklink_count || 0 }} 馃悮{{ t.backdoor_count || 0 }} 馃毇{{ t.violative_count || 0 }}
                  </span>
                  <span class="history-time">{{ formatTime(t.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="pagination-bar" v-if="historyTotal > historyPageSize">
            <el-pagination
              v-model:current-page="historyPage"
              :page-size="historyPageSize"
              :total="historyTotal"
              layout="prev, pager, next, jumper"
              @current-change="fetchHistory"
              small
              background
            />
          </div>
          <div class="pagination-info" v-if="historyTotal > 0">
            鍏?{{ historyTotal }} 鏉★紝绗?{{ historyPage }} / {{ Math.ceil(historyTotal / historyPageSize) }} 椤?          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import api from '../api/Orion'

const stats = ref({})
const siteCount = ref(0)
const assetCount = ref(0)
const threats = ref({})
const dashStats = ref({})
const historyTasks = ref([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = 20
const historyLoading = ref(false)
const historySearch = ref('')
const historyStatus = ref('')
const selectedTask = ref(null)
const scanResult = ref(null)

const hasThreats = computed(() => {
  const t = threats.value
  return (t.total_blacklinks || 0) + (t.total_backdoors || 0) + (t.total_violations || 0) > 0
})

const threatDistOption = computed(() => {
  const t = threats.value
  return {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false },
      data: [
        { value: t.total_blacklinks || 0, name: '鏆楅摼', itemStyle: { color: '#f44' } },
        { value: t.total_backdoors || 0, name: '鍚庨棬', itemStyle: { color: '#ff6b35' } },
        { value: t.total_violations || 0, name: '杩濊', itemStyle: { color: '#ff9800' } },
      ]
    }]
  }
})

const scanTrendOption = computed(() => {
  const weekData = computed(() => {
    const result = []
    for (let i = 6; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const key = d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
      const dayTasks = historyTasks.value.filter(t => {
        if (!t.created_at) return false
        const tDate = new Date(t.created_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
        return tDate === key
      })
      result.push({ date: key, success: dayTasks.filter(t => t.status === 'success').length, error: dayTasks.filter(t => t.status === 'error').length })
    }
    return result
  }).value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['鎴愬姛', '寮傚父'] },
    grid: { left: 40, right: 16, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: weekData.map(d => d.date), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '鎴愬姛', type: 'bar', data: weekData.map(d => d.success), itemStyle: { color: '#00c853' } },
      { name: '寮傚父', type: 'bar', data: weekData.map(d => d.error), itemStyle: { color: '#f44' } },
    ]
  }
})

const fetchStats = () => api.get('/stats').then(r => { stats.value = r.data }).catch(() => {})
const fetchThreats = () => api.get('/threat-summary').then(r => { threats.value = r.data }).catch(() => {})
const fetchDashStats = () => api.get('/dashboard/stats').then(r => { dashStats.value = r.data }).catch(() => {})

const fetchHistory = () => {
  historyLoading.value = true
  const params = { page: historyPage.value, page_size: historyPageSize }
  if (historySearch.value) params.search = historySearch.value
  if (historyStatus.value) params.status = historyStatus.value
  api.get('/tasks/paginated', { params }).then(r => {
    historyTasks.value = r.data.tasks || []
    historyTotal.value = r.data.total || 0
  }).catch(() => { historyTasks.value = [] }).finally(() => { historyLoading.value = false })
}

let debounceTimer = null
const debounceHistory = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchHistory, 400)
}

const selectTask = (t) => {
  selectedTask.value = t
  if (t.result) {
    try {
      scanResult.value = typeof t.result === 'string' ? JSON.parse(t.result) : t.result
    } catch { scanResult.value = t.result }
  } else {
    api.get('/scan/' + t.id).then(r => {
      scanResult.value = r.data
    }).catch(() => { scanResult.value = null })
  }
}

const fetchAll = () => {
  fetchStats()
  fetchThreats()
  fetchDashStats()
  fetchHistory()
  fetchSiteCount()
}

const fetchSiteCount = () => {
  api.get('/site-monitors').then(r => { siteCount.value = r.data.total || r.data?.length || 0 }).catch(() => {
    api.get('/assets/stats').then(r => { siteCount.value = r.data?.total_sites || r.data?.total || 0 }).catch(() => {})
  })
  fetch('http://localhost:5187/api/assets/stats', { timeout: 3000 })
    .then(r => r.json()).then(d => { assetCount.value = d.total || 0 })
    .catch(() => { api.get('/assets/stats').then(r => { assetCount.value = r.data?.total || 0 }).catch(() => {}) })
}

const scanTypeLabel = (t) => ({ HomePage_Scan: '棣栭〉鎵弿', FullSite_Scan: '鍏ㄧ珯鎵弿', Critical_Scan: '婕忔礊鎵弿' }[t] || t || '鏈煡')
const statusLabel = (s) => ({ success: '鉁?, error: '鈿狅笍', running: '鈴?, pending: '馃搵' }[s] || s || '')
const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''

onMounted(fetchAll)
</script>

<style scoped>
.dashboard { color: #1a1a2e; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: #8a94a6; }
.header-actions { display: flex; gap: 8px; }
.stat-row { margin-bottom: 16px; }
.stat-card {
  display: flex; align-items: center; gap: 14px;
  background: #ffffff; border-radius: 14px; padding: 18px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  min-height: 90px;
}
.threat-card { border-left: 4px solid #f44; }
.stat-icon { font-size: 28px; }
.stat-body { flex: 1; }
.stat-num { font-size: 26px; font-weight: 800; color: #4f8ef7; line-height: 1; min-height: 31px; display: flex; align-items: center; }
.stat-num.green { color: #00c853; }
.stat-num.red { color: #f44; }
.stat-num.orange { color: #ff9800; }
.stat-num.danger { color: #d93636; }
.stat-num.warn { color: #ff9800; }
.stat-num.teal { color: #00b8b0; }
.stat-label { font-size: 12px; color: #8a94a6; margin-top: 4px; }
.stat-sub { font-size: 11px; color: #5a6474; margin-top: 2px; }
.chart-row { margin-bottom: 0; }
.bottom-row { margin-top: 0; }
.top-threats { max-height: 220px; overflow-y: auto; }
.threat-pattern {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: 6px; margin-bottom: 4px;
  background: #f8f9fb; font-size: 12px;
}
.threat-pattern:hover { background: #fff0f0; }
.pattern-rank { color: #f44; font-weight: 700; font-size: 11px; min-width: 24px; }
.pattern-text { flex: 1; color: #1a1a2e; font-family: 'Courier New', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pattern-count { color: #8a94a6; font-size: 11px; white-space: nowrap; }
.white-card {
  background: #ffffff; border-radius: 14px; padding: 20px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 14px; }
.result-header { margin-bottom: 12px; }
.result-url { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px; word-break: break-all; }
.result-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #8a94a6; }
.status-tag { font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 500; }
.status-tag.success { background: #e8faf0; color: #00c853; }
.status-tag.error { background: #fff0f0; color: #f44; }
.risk-row { margin: 12px 0; }
.risk-item {
  background: #f8f9fb; border-radius: 8px; padding: 10px; text-align: center;
  border: 1px solid #e8eaed;
}
.risk-item.danger { background: #fff0f0; border-color: #ffcdd2; }
.risk-item.warn { background: #fff8e0; border-color: #ffe0b2; }
.risk-num { font-size: 22px; font-weight: 800; color: #1a1a2e; }
.risk-label { font-size: 11px; color: #8a94a6; margin-top: 2px; }
.detail-collapse { margin-top: 8px; }
.detail-item { background: #f8f9fb; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; }
.detail-url { font-size: 13px; font-weight: 500; margin-bottom: 2px; word-break: break-all; }
.detail-url.danger { color: #f44; }
.detail-url.warn { color: #ff9800; }
.detail-text { font-size: 12px; color: #5a6474; margin-bottom: 1px; word-break: break-all; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 10px; }
.history-list { max-height: 320px; overflow-y: auto; }
.history-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 4px;
  border: 1px solid transparent; transition: all 0.15s;
}
.history-item:hover { background: #f8f9fb; border-color: #e8eaed; }
.history-item.selected { background: #eef2ff; border-color: #4f8ef7; }
.history-left { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.history-status { font-size: 12px; white-space: nowrap; }
.history-status.status-success { color: #00c853; }
.history-status.status-error { color: #f44; }
.history-status.status-running { color: #4f8ef7; }
.history-url { font-size: 12px; color: #1a1a2e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.history-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.history-threats { font-size: 11px; color: #8a94a6; white-space: nowrap; }
.history-time { font-size: 11px; color: #8a94a6; white-space: nowrap; min-width: 80px; text-align: right; }
.pagination-bar { display: flex; justify-content: center; margin-top: 12px; }
.pagination-info { text-align: center; font-size: 12px; color: #8a94a6; margin-top: 8px; }
.empty-tip { text-align: center; padding: 24px; color: #8a94a6; font-size: 13px; }
</style>