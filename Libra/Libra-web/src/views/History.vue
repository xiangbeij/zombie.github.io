<template>
  <div class="history-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">📋 扫描历史</h2>
        <p class="page-desc">查看和管理所有扫描任务记录</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showAddMonitorDialog">
          <el-icon><Plus /></el-icon> 添加监控
        </el-button>
        <el-button v-if="selectedIds.length" type="danger" @click="batchDelete">
          <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
        </el-button>
      </div>
    </div>

    <!-- 过滤栏 -->
    <div class="filter-bar">
      <el-input v-model="search" placeholder="搜索 URL / 域名" clearable size="default" style="width:240px" @input="debounceSearch">
        <template #prefix><span>🔍</span></template>
      </el-input>
      <el-select v-model="filterStatus" clearable placeholder="全部状态" size="default" style="width:130px" @change="fetchList">
        <el-option value="success" label="✅ 成功" />
        <el-option value="error" label="⚠️ 异常" />
        <el-option value="running" label="⏳ 进行中" />
        <el-option value="pending" label="📋 待处理" />
      </el-select>
      <el-select v-model="filterType" clearable placeholder="扫描类型" size="default" style="width:160px" @change="fetchList">
        <el-option value="HomePage_Scan" label="首页扫描" />
        <el-option value="FullSite_Scan" label="全站扫描" />
        <el-option value="Critical_Scan" label="漏洞扫描" />
      </el-select>
      <el-select v-model="sortOrder" size="default" style="width:130px" @change="fetchList">
        <el-option value="desc" label="最新优先" />
        <el-option value="asc" label="最早优先" />
      </el-select>
    </div>

    <!-- 全选 + 表头 -->
    <div class="table-container">
      <el-table :data="tasks" v-loading="loading" stripe size="small" @selection-change="onSelectionChange"
        :row-class-name="rowClassName">
        <el-table-column type="selection" width="40" />
        <el-table-column label="URL" min-width="220" prop="url">
          <template #default="{ row }">
            <div class="url-cell">
              <span class="task-url" @click="showDetail(row)">{{ row.url }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <span class="type-link" @click="filterByType(row.task_type || row.scan_type)">
              {{ scanTypeLabel(row.task_type || row.scan_type) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="暗链" width="70" align="center">
          <template #default="{ row }">
            <span :class="row.blacklink_count ? 'count-danger' : 'count-zero'">{{ row.blacklink_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="后门" width="70" align="center">
          <template #default="{ row }">
            <span :class="row.backdoor_count ? 'count-danger' : 'count-zero'">{{ row.backdoor_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="违规" width="70" align="center">
          <template #default="{ row }">
            <span :class="row.violative_count || row.violativelink_count ? 'count-warn' : 'count-zero'">{{ row.violative_count || row.violativelink_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80" align="center">
          <template #default="{ row }">{{ row.duration ? row.duration + 's' : '-' }}</template>
        </el-table-column>
        <el-table-column label="时间" width="150" prop="created_at">
          <template #default="{ row }">
            <span class="time-cell">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="fetchList"
        background
      />
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="扫描详情" size="600px" direction="rtl">
      <div v-if="detailData" class="detail-body">
        <div class="detail-meta">
          <el-tag type="info">{{ scanTypeLabel(detailData.task_type || detailData.scan_type) }}</el-tag>
          <el-tag :type="statusTagType(detailData.status)">{{ statusLabel(detailData.status) }}</el-tag>
          <span class="detail-time">{{ formatTime(detailData.created_at) }}</span>
        </div>
        <div class="detail-url-row">{{ detailData.url }}</div>
        <el-row :gutter="12" class="detail-stats">
          <el-col :span="6"><div class="stat-box" :class="{red: detailData.blacklink_count}">
            <div class="stat-num-lg">{{ detailData.blacklink_count || 0 }}</div>
            <div class="stat-lbl">暗链</div>
          </div></el-col>
          <el-col :span="6"><div class="stat-box" :class="{orange: detailData.backdoor_count}">
            <div class="stat-num-lg">{{ detailData.backdoor_count || 0 }}</div>
            <div class="stat-lbl">后门</div>
          </div></el-col>
          <el-col :span="6"><div class="stat-box" :class="{warn: detailData.violative_count || detailData.violativelink_count}">
            <div class="stat-num-lg">{{ detailData.violative_count || detailData.violativelink_count || 0 }}</div>
            <div class="stat-lbl">违规</div>
          </div></el-col>
          <el-col :span="6"><div class="stat-box">
            <div class="stat-num-lg">{{ detailData.diedlink_count || 0 }}</div>
            <div class="stat-lbl">死链</div>
          </div></el-col>
        </el-row>
        <div v-if="detailData.blacklink_list?.length" class="detail-section">
          <div class="section-title danger">🔗 暗链 ({{ detailData.blacklink_list.length }})</div>
          <div v-for="(item, idx) in detailData.blacklink_list" :key="idx" class="detail-item">
            <div class="detail-url-danger">{{ item.url }}</div>
            <div v-for="(l, i) in item.blacklinkres" :key="i" class="detail-text">{{ l }}</div>
          </div>
        </div>
        <div v-if="detailData.backdoor_list?.length" class="detail-section">
          <div class="section-title danger">🐚 后门 ({{ detailData.backdoor_list.length }})</div>
          <div v-for="(item, idx) in detailData.backdoor_list" :key="idx" class="detail-item">
            <div class="detail-url-danger">{{ item.url }}</div>
            <div v-for="(b, i) in item.backdoorres" :key="i" class="detail-text">{{ b }}</div>
          </div>
        </div>
        <div v-if="detailData.violativelink_list?.length" class="detail-section">
          <div class="section-title warn">🚫 违规 ({{ detailData.violativelink_list.length }})</div>
          <div v-for="(item, idx) in detailData.violativelink_list" :key="idx" class="detail-item">
            <div class="detail-url-warn">{{ item.url }}</div>
            <div v-for="(v, i) in item.violativelinkres" :key="i" class="detail-text">{{ v }}</div>
          </div>
        </div>
        <div v-if="!detailData.blacklink_list?.length && !detailData.backdoor_list?.length && !detailData.violativelink_list?.length" class="detail-clean">
          ✅ 未发现威胁
        </div>
      </div>
    </el-drawer>

    <!-- 添加监控弹窗 -->
    <el-dialog v-model="addMonitorVisible" title="添加监控站点" width="540px" destroy-on-close>
      <div class="add-monitor-tip">支持批量添加，每行一个 URL，支持 CSV 格式粘贴</div>
      <el-input v-model="addMonitorText" type="textarea" :rows="8" placeholder="https://example.com&#10;https://foo.com&#10;...
或粘贴：
URL,站点名称
https://a.com,站点A
https://b.com,站点B" />
      <template #footer>
        <el-button @click="addMonitorVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddMonitor" :loading="addLoading">
          确认添加 ({{ countAddMonitorLines }} 个)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '../api/libra'

const tasks = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const search = ref('')
const filterStatus = ref('')
const filterType = ref('')
const sortOrder = ref('desc')
const selectedIds = ref([])
const detailVisible = ref(false)
const detailData = ref(null)
const addMonitorVisible = ref(false)
const addMonitorText = ref('')
const addLoading = ref(false)

const countAddMonitorLines = computed(() => {
  const lines = addMonitorText.value.split('\n').filter(l => l.trim())
  return lines.length
})

const fetchList = () => {
  loading.value = true
  const params = { page: page.value, page_size: pageSize.value, order: sortOrder.value }
  if (search.value) params.search = search.value
  if (filterStatus.value) params.status = filterStatus.value
  if (filterType.value) params.scan_type = filterType.value
  api.get('/tasks/paginated', { params }).then(r => {
    tasks.value = r.data.tasks || []
    total.value = r.data.total || 0
  }).catch(() => { tasks.value = [] }).finally(() => { loading.value = false })
}

let debounceTimer = null
const debounceSearch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; fetchList() }, 400)
}

const onSelectionChange = (rows) => {
  selectedIds.value = rows.map(r => r.id)
}

const batchDelete = () => {
  if (!selectedIds.value.length) return
  ElMessageBox.confirm('确认删除选中的 ' + selectedIds.value.length + ' 条记录？', '批量删除').then(() => {
    Promise.all(selectedIds.value.map(id => api.delete('/scan/' + id).catch(() => {})))
      .then(() => {
        ElMessage.success('已删除 ' + selectedIds.value.length + ' 条')
        selectedIds.value = []
        fetchList()
      }).catch(() => ElMessage.error('删除失败'))
  }).catch(() => {})
}

const showDetail = (row) => {
  detailData.value = row
  detailVisible.value = true
}

const filterByType = (type) => {
  filterType.value = type
  page.value = 1
  fetchList()
}

const showAddMonitorDialog = () => {
  addMonitorText.value = ''
  addMonitorVisible.value = true
}

const submitAddMonitor = () => {
  const lines = addMonitorText.value.split('\n').filter(l => l.trim())
  if (!lines.length) { ElMessage.warning('请输入 URL'); return }
  addLoading.value = true
  // Parse: CSV or one-per-line
  const sites = lines.map(l => {
    const parts = l.split(',')
    return { url: parts[0].trim(), name: parts[1] ? parts[1].trim() : '' }
  }).filter(s => s.url)
  Promise.all(sites.map(s => api.post('/sites', { url: s.url, name: s.name || s.url }).catch(() => {})))
    .then(() => {
      ElMessage.success('已添加 ' + sites.length + ' 个监控站点')
      addMonitorVisible.value = false
    }).catch(() => ElMessage.error('添加失败')).finally(() => { addLoading.value = false })
}

const scanTypeLabel = (t) => ({ HomePage_Scan: '首页扫描', FullSite_Scan: '全站扫描', Critical_Scan: '漏洞扫描' }[t] || t || '-')
const statusLabel = (s) => ({ success: '成功', error: '异常', running: '进行中', pending: '待处理' }[s] || s || '-')
const statusTagType = (s) => ({ success: 'success', error: 'danger', running: 'warning', pending: 'info' }[s] || 'info')
const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'
const rowClassName = ({ row }) => row.blacklink_count || row.backdoor_count ? 'danger-row' : ''

onMounted(fetchList)
</script>

<style scoped>
.history-page { color: #1a1a2e; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: #8a94a6; }
.header-actions { display: flex; gap: 8px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }
.table-container { background: #ffffff; border-radius: 14px; border: 1px solid #e8eaed; overflow: hidden; }
.url-cell { display: flex; align-items: center; }
.task-url { color: #4f8ef7; cursor: pointer; font-size: 13px; }
.task-url:hover { text-decoration: underline; }
.type-link { color: #4f8ef7; cursor: pointer; font-size: 12px; }
.type-link:hover { text-decoration: underline; }
.count-danger { color: #f44; font-weight: 600; }
.count-warn { color: #ff9800; font-weight: 600; }
.count-zero { color: #8a94a6; }
.time-cell { font-size: 12px; color: #8a94a6; }
.pagination-wrap { display: flex; justify-content: center; margin-top: 16px; }
.detail-body { padding: 0 16px; }
.detail-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.detail-time { font-size: 12px; color: #8a94a6; margin-left: 8px; }
.detail-url-row { font-size: 15px; font-weight: 600; color: #1a1a2e; word-break: break-all; margin-bottom: 16px; padding: 8px 12px; background: #f8f9fb; border-radius: 8px; }
.detail-stats { margin-bottom: 16px; }
.stat-box { background: #f8f9fb; border-radius: 10px; padding: 14px; text-align: center; border: 1px solid #e8eaed; }
.stat-box.red { background: #fff0f0; border-color: #ffcdd2; }
.stat-box.orange { background: #fff3e0; border-color: #ffe0b2; }
.stat-box.warn { background: #fff8e0; border-color: #ffe082; }
.stat-num-lg { font-size: 26px; font-weight: 800; color: #1a1a2e; }
.stat-lbl { font-size: 11px; color: #8a94a6; margin-top: 2px; }
.detail-section { margin-bottom: 16px; }
.section-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; padding: 6px 0; border-bottom: 1px solid #f0f2f5; }
.section-title.danger { color: #f44; }
.section-title.warn { color: #ff9800; }
.detail-item { background: #f8f9fb; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; }
.detail-url-danger { font-size: 13px; font-weight: 500; color: #f44; margin-bottom: 2px; word-break: break-all; }
.detail-url-warn { font-size: 13px; font-weight: 500; color: #ff9800; margin-bottom: 2px; word-break: break-all; }
.detail-text { font-size: 12px; color: #5a6474; margin-bottom: 1px; word-break: break-all; }
.detail-clean { text-align: center; padding: 32px; color: #00c853; font-size: 16px; }
.add-monitor-tip { font-size: 12px; color: #8a94a6; margin-bottom: 10px; padding: 8px 12px; background: #f8f9fb; border-radius: 6px; }
</style>

<style>
.el-table .danger-row td { background-color: #fff5f5; }
</style>