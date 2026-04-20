<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">📊 ShieldEye 安全监控面板</h2>
        <p class="page-desc">实时监控网站安全状态，跟踪威胁趋势</p>
      </div>
      <div class="header-actions">
        <el-button @click="fetchAll" :icon="Refresh" circle />
      </div>
    </div>

    <!-- 第一行：监控概览 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon blue">🏢</div>
        <div class="stat-body">
          <div class="stat-num">{{ siteCount }}</div>
          <div class="stat-label">已监控站点</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon teal">🛰️</div>
        <div class="stat-body">
          <div class="stat-num teal">{{ assetCount }}</div>
          <div class="stat-label">资产总数</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon">🔍</div>
        <div class="stat-body">
          <div class="stat-num">{{ stats.total || 0 }}</div>
          <div class="stat-label">总扫描次数</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon green">✅</div>
        <div class="stat-body">
          <div class="stat-num green">{{ stats.success || 0 }}</div>
          <div class="stat-label">成功完成</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon red">⚠️</div>
        <div class="stat-body">
          <div class="stat-num red">{{ stats.error || 0 }}</div>
          <div class="stat-label">异常/失败</div>
        </div>
      </div></el-col>
      <el-col :span="4"><div class="stat-card">
        <div class="stat-icon orange">⏳</div>
        <div class="stat-body">
          <div class="stat-num orange">{{ stats.running || 0 }}</div>
          <div class="stat-label">正在扫描</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 第二行：威胁聚合 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6"><div class="stat-card threat-card">
        <div class="stat-icon">⛓️</div>
        <div class="stat-body">
          <div class="stat-num danger">{{ threats.total_blacklinks || 0 }}</div>
          <div class="stat-label">累计暗链总数</div>
          <div class="stat-sub">本周 +{{ threats.week_blacklinks || 0 }}</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card threat-card">
        <div class="stat-icon">🐚</div>
        <div class="stat-body">
          <div class="stat-num danger">{{ threats.total_backdoors || 0 }}</div>
          <div class="stat-label">累计后门总数</div>
          <div class="stat-sub">本周 +{{ threats.week_backdoors || 0 }}</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card threat-card">
        <div class="stat-icon">🚫</div>
        <div class="stat-body">
          <div class="stat-num warn">{{ threats.total_violations || 0 }}</div>
          <div class="stat-label">累计违规总数</div>
          <div class="stat-sub">本周 +{{ threats.week_violations || 0 }}</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card">
        <div class="stat-icon">🏢</div>
        <div class="stat-body">
          <div class="stat-num blue">{{ dashStats?.assets?.total || assetCount }}</div>
          <div class="stat-label">资产发现</div>
          <div class="stat-sub">存活 {{ dashStats?.assets?.active || 0 }}</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 第三行：图表 + 威胁 Top 模式 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="8">
        <div class="white-card">
          <div class="card-title">🎯 威胁类型分布</div>
          <div style="height:220px">
            <v-chart :option="threatDistOption" autoresize v-if="hasThreats" />
            <el-empty v-else description="暂无威胁数据" :image-size="60" />
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="white-card">
          <div class="card-title">📈 扫描趋势</div>
          <div style="height:220px">
            <v-chart :option="scanTrendOption" autoresize />
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="white-card">
          <div class="card-title">🔴 高频暗链模式 Top</div>
          <div class="top-threats" v-if="(threats.top_blacklink_patterns || []).length">
            <div v-for="(t, i) in (threats.top_blacklink_patterns || []).slice(0, 8)" :key="i" class="threat-pattern">
              <span class="pattern-rank">#{{ i+1 }}</span>
              <span class="pattern-text">{{ t.pattern.substring(0, 40) }}{{ t.pattern.length > 40 ? '...' : '' }}</span>
              <span class="pattern-count">{{ t.count }}次</span>
            </div>
          </div>
          <el-empty v-else description="暂无暗链数据" :image-size="50" />
        </div>
      </el-col>
    </el-row>

    <!-- 第四行：最新扫描详情 + 历史记录 -->
    <el-row :gutter="16" class="bottom-row">
      <el-col :span="12">
        <div class="white-card">
          <div class="card-title">📋 最新扫描详情</div>
          <div v-if="!selectedTask && !scanResult" class="empty-tip">点击下方历史记录中的任务查看详情</div>
          <div v-else-if="scanResult">
            <div class="result-header">
              <div class="result-url">{{ scanResult.taskurl || scanResult.url }}</div>
              <div class="result-meta">
                <el-tag type="info" size="small">{{ scanTypeLabel(scanResult.tasktype || scanResult.scan_type) }}</el-tag>
                <span v-if="scanResult.status === 'success'" class="status-tag success">成功</span>
                <span v-else class="status-tag error">异常</span>
              </div>
            </div>
            <el-row :gutter="10" class="risk-row">
              <el-col :span="6"><div class="risk-item" :class="{danger: scanResult.blacklink_list?.length}">
                <div class="risk-num">{{ scanResult.blacklink_list?.length || 0 }}</div>
                <div class="risk-label">暗链</div>
              </div></el-col>
              <el-col :span="6"><div class="risk-item" :class="{danger: scanResult.backdoor_list?.length}">
                <div class="risk-num">{{ scanResult.backdoor_list?.length || 0 }}</div>
                <div class="risk-label">后门</div>
              </div></el-col>
              <el-col :span="6"><div class="risk-item" :class="{warn: scanResult.violativelink_list?.length}">
                <div class="risk-num">{{ scanResult.violativelink_list?.length || 0 }}</div>
                <div class="risk-label">违规</div>
              </div></el-col>
              <el-col :span="6"><div class="risk-item">
                <div class="risk-num">{{ scanResult.diedlink_list?.length || 0 }}</div>
                <div class="risk-label">死链</div>
              </div></el-col>
            </el-row>
            <el-collapse v-if="scanResult.blacklink_list?.length" class="detail-collapse">
              <el-collapse-item title="🔗 暗链详情" name="bl">
                <div v-for="(item, idx) in scanResult.blacklink_list" :key="idx" class="detail-item">
                  <div class="detail-url danger">{{ item.url }}</div>
                  <div v-for="(l, i) in item.blacklinkres" :key="i" class="detail-text">{{ l }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
            <el-collapse v-if="scanResult.backdoor_list?.length" class="detail-collapse">
              <el-collapse-item title="🐚 后门详情" name="bd">
                <div v-for="(item, idx) in scanResult.backdoor_list" :key="idx" class="detail-item">
                  <div class="detail-url danger">{{ item.url }}</div>
                  <div v-for="(b, i) in item.backdoorres" :key="i" class="detail-text">{{ b }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
            <el-collapse v-if="scanResult.violativelink_list?.length" class="detail-collapse">
              <el-collapse-item title="🚫 违规详情" name="vl">
                <div v-for="(item, idx) in scanResult.violativelink_list" :key="idx" class="detail-item">
                  <div class="detail-url warn">{{ item.url }}</div>
                  <div v-for="(v, i) in item.violativelinkres" :key="i" class="detail-text">{{ v }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </el-col>

      <!-- 历史记录 -->
      <el-col :span="12">
        <div class="white-card">
          <div class="card-title">📜 扫描历史</div>
          <div class="filter-bar">
            <el-input v-model="historySearch" placeholder="搜索 URL" clearable size="small" style="width:180px" @input="debounceHistory">
              <template #prefix><span>🔍</span></template>
            </el-input>
            <el-select v-model="historyStatus" size="small" style="width:120px" clearable placeholder="状态" @change="fetchHistory">
              <el-option value="success" label="✅ 成功" />
              <el-option value="error" label="⚠️ 异常" />
              <el-option value="running" label="⏳ 进行中" />
              <el-option value="pending" label="📋 待处理" />
            </el-select>
          </div>
          <div class="history-list">
            <div v-if="historyLoading" style="text-align:center;padding:20px;color:#8a94a6">加载中...</div>
            <div v-else-if="historyTasks.length === 0" class="empty-tip">暂无历史记录</div>
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
                    🔗{{ t.blacklink_count || 0 }} 🐚{{ t.backdoor_count || 0 }} 🚫{{ t.violative_count || 0 }}
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
            共 {{ historyTotal }} 条，第 {{ historyPage }} / {{ Math.ceil(historyTotal / historyPageSize) }} 页
          </div>
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
import api from '../api/libra'

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
        { value: t.total_blacklinks || 0, name: '暗链', itemStyle: { color: '#f44' } },
        { value: t.total_backdoors || 0, name: '后门', itemStyle: { color: '#ff6b35' } },
        { value: t.total_violations || 0, name: '违规', itemStyle: { color: '#ff9800' } },
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
    legend: { data: ['成功', '异常'] },
    grid: { left: 40, right: 16, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: weekData.map(d => d.date), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '成功', type: 'bar', data: weekData.map(d => d.success), itemStyle: { color: '#00c853' } },
      { name: '异常', type: 'bar', data: weekData.map(d => d.error), itemStyle: { color: '#f44' } },
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

const scanTypeLabel = (t) => ({ HomePage_Scan: '首页扫描', FullSite_Scan: '全站扫描', Critical_Scan: '漏洞扫描' }[t] || t || '未知')
const statusLabel = (s) => ({ success: '✅', error: '⚠️', running: '⏳', pending: '📋' }[s] || s || '')
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