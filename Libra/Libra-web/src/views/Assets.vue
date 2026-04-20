<template>
  <div class="assets-page">
    <div class="page-header">
      <h2>🛡️ 资产发现</h2>
      <div class="header-actions">
        <el-button @click="refresh" :loading="loading" circle title="刷新">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button type="success" @click="showAddDialog = true">➕ 手动添加</el-button>
        <el-button type="primary" @click="showBatchDialog = true">📤 批量导入</el-button>
        <el-button @click="exportAssets" :loading="exporting">📥 导出</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="mini-stat" style="background:#eef2ff">
          <div class="mstat-num" style="color:#4f8ef7">{{ stats.total_assets || 0 }}</div>
          <div class="mstat-label">总资产</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat" style="background:#e8faf0">
          <div class="mstat-num" style="color:#00c853">{{ stats.by_status?.active || 0 }}</div>
          <div class="mstat-label">活跃</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat" style="background:#fff8e0">
          <div class="mstat-num" style="color:#ff9800">{{ stats.ip_ranges || 0 }}</div>
          <div class="mstat-label">IP 段</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat" style="background:#fff0f0">
          <div class="mstat-num" style="color:#f44">{{ stats.pending_alerts || 0 }}</div>
          <div class="mstat-label">待处理告警</div>
        </div>
      </el-col>
    </el-row>

    <!-- 搜索 + 筛选 -->
    <div class="filter-bar">
      <el-input v-model="search" placeholder="搜索域名 / IP / 标题" clearable style="max-width:300px" @change="page=1; fetchAssets()" />
      <el-select v-model="filterType" placeholder="资产类型" clearable style="width:140px" @change="page=1; fetchAssets()">
        <el-option value="domain" label="域名" />
        <el-option value="ip" label="IP" />
        <el-option value="cert" label="证书" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:120px" @change="page=1; fetchAssets()">
        <el-option value="active" label="活跃" />
        <el-option value="inactive" label="不活跃" />
        <el-option value="unknown" label="未知" />
      </el-select>
      <el-button @click="page=1; fetchAssets()">🔍 搜索</el-button>
    </div>

    <!-- 资产表格 -->
    <div class="asset-table-wrap">
      <el-table :data="assets" v-loading="loading" stripe size="small" max-height="480"
        empty-text="暂无资产，点击上方按钮添加">
        <el-table-column label="类型" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.asset_type)" size="small">{{ typeLabel(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="域名 / IP" min-width="180">
          <template #default="{ row }">
            <div class="asset-value">
              <span class="scheme">{{ row.scheme }}://</span>{{ row.value }}:{{ row.port }}
            </div>
            <div class="asset-domain">{{ row.value }}</div>
          </template>
        </el-table-column>
        <el-table-column label="网站标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="editingId !== row.id" class="title-cell" :class="{ garbled: isGarbled(row.title) }">
              {{ row.title || '-' }}
            </span>
            <el-input v-else v-model="editTitle" size="small" maxlength="200" style="max-width:200px"
              @keyup.enter="saveTitle(row)" @keyup.escape="editingId = null" />
          </template>
        </el-table-column>
        <el-table-column label="协议" width="90">
          <template #default="{ row }">{{ row.scheme }}:{{ row.port }}</template>
        </el-table-column>
        <el-table-column label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="tags-cell">{{ row.tags || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最近发现" width="150">
          <template #default="{ row }">{{ formatTime(row.last_seen) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="editingId !== row.id" text type="primary" size="small" @click="startEditTitle(row)">✏️ 改标题</el-button>
            <el-button v-else text type="success" size="small" @click="saveTitle(row)">✅ 保存</el-button>
            <el-button text type="danger" size="small" @click="deleteAsset(row)">🗑️</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <span class="pagination-info">共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next"
          @current-change="fetchAssets"
          @size-change="pageSizeChange"
        />
      </div>
    </div>

    <!-- IP 段管理 -->
    <div class="ip-section">
      <div class="section-header">
        <h3>🌐 IP 段管理</h3>
        <el-button size="small" type="primary" @click="showIpDialog = true">➕ 添加 IP 段</el-button>
      </div>
      <el-table :data="ipRanges" stripe size="small" max-height="200" v-loading="ipLoading"
        empty-text="暂无 IP 段">
        <el-table-column label="CIDR" prop="cidr" min-width="160" />
        <el-table-column label="备注" prop="note" min-width="200" show-overflow-tooltip />
        <el-table-column label="资产数" prop="asset_count" width="80" align="center" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="scanIpRange(row)">🔍 扫描</el-button>
            <el-button text type="danger" size="small" @click="deleteIpRange(row)">🗑️</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加资产对话框 -->
    <el-dialog v-model="showAddDialog" title="➕ 手动添加资产" width="480px">
      <el-form :model="addForm" label-width="90px">
        <el-form-item label="资产类型">
          <el-select v-model="addForm.asset_type" style="width:100%">
            <el-option value="domain" label="域名" />
            <el-option value="ip" label="IP" />
          </el-select>
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="addForm.value" placeholder="example.com 或 1.2.3.4" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="addForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="addForm.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addForm.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addAsset" :loading="addLoading">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showBatchDialog" title="📤 批量导入资产" width="620px" destroy-on-close>
      <div class="batch-tip">支持以下格式（第一行会自动识别为表头）：</div>
      <div class="batch-format">
        <div class="format-label">CSV 格式示例：</div>
        <pre class="format-example">value,port,asset_type,tags,note
example.com,443,domain,官网,主站
sub.example.com,443,domain,官网,子站
1.2.3.4,80,ip,服务器,测试机</pre>
        <div class="format-label" style="margin-top:8px">或直接粘贴纯文本（每行一个地址）：</div>
        <pre class="format-example">example.com
sub.example.com:8080
1.2.3.4</pre>
      </div>
      <el-tabs v-model="batchTab" style="margin-top:12px">
        <el-tab-pane label="📋 粘贴文本" name="text">
          <el-input v-model="batchText" type="textarea" :rows="8"
            placeholder="粘贴 CSV 内容或每行一个地址，支持格式：&#10;value,port,type,tags&#10;example.com,443,domain,官网&#10;或直接粘贴地址列表" />
        </el-tab-pane>
        <el-tab-pane label="📁 上传文件" name="file">
          <el-upload ref="uploadRef" drag :auto-upload="false" :limit="1"
            accept=".csv,.txt,.xlsx,.xls" :on-change="onFileChange"
            style="text-align:center">
            <el-icon><UploadFilled /></el-icon>
            <div>拖拽文件到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 CSV、TXT、Excel 文件</div>
            </template>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showBatchDialog = false">取消</el-button>
        <el-button type="primary" @click="doBatchImport" :loading="batchLoading">
          确认导入 {{ batchPreviewCount > 0 ? '(' + batchPreviewCount + ' 条)' : '' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加 IP 段对话框 -->
    <el-dialog v-model="showIpDialog" title="🌐 添加 IP 段" width="440px">
      <el-form :model="ipForm" label-width="80px">
        <el-form-item label="CIDR">
          <el-input v-model="ipForm.cidr" placeholder="210.44.49.0/28" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="ipForm.note" placeholder="青岛农业大学 HPC 网段" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showIpDialog = false">取消</el-button>
        <el-button type="primary" @click="addIpRange" :loading="ipLoading">确认</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, UploadFilled } from '@element-plus/icons-vue'
import { getAssets, addAssetApi, updateAssetTitleApi, deleteAssetApi,
         getIpRanges, addIpRangeApi, deleteIpRangeApi, scanIpRangeApi,
         getAssetStats, exportAssetsApi, batchImportAssetsApi } from '../api/libra'

const loading = ref(false)
const exporting = ref(false)
const addLoading = ref(false)
const ipLoading = ref(false)
const batchLoading = ref(false)
const assets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)
const search = ref('')
const filterType = ref('')
const filterStatus = ref('')
const stats = ref({})
const ipRanges = ref([])

// Dialogs
const showAddDialog = ref(false)
const showIpDialog = ref(false)
const showBatchDialog = ref(false)
const editingId = ref(null)
const editTitle = ref('')

// Add form
const addForm = ref({ asset_type: 'domain', value: '', port: 443, tags: '', note: '' })

// IP range form
const ipForm = ref({ cidr: '', note: '' })

// Batch import
const batchTab = ref('text')
const batchText = ref('')
const batchFile = ref(null)
const uploadRef = ref(null)

const batchPreviewCount = computed(() => {
  const text = batchText.value.trim()
  if (!text) return 0
  return text.split('\n').filter(l => l.trim()).length
})

const fetchAssets = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: page.value, page_size: pageSize.value })
    if (search.value) params.set('search', search.value)
    if (filterType.value) params.set('type', filterType.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    const r = await getAssets(params.toString())
    const d = r.data
    assets.value = d.assets || []
    total.value = d.total || 0
  } catch (e) {
    ElMessage.error('获取资产列表失败')
  } finally { loading.value = false }
}

const fetchStats = async () => {
  try {
    const r = await getAssetStats()
    stats.value = r.data || {}
  } catch {}
}

const fetchIpRanges = async () => {
  ipLoading.value = true
  try {
    const r = await getIpRanges()
    ipRanges.value = r.data.ip_ranges || []
  } catch {} finally { ipLoading.value = false }
}

const refresh = () => { page.value = 1; fetchAssets(); fetchStats(); fetchIpRanges() }

const pageSizeChange = (sz) => { pageSize.value = sz; page.value = 1; fetchAssets() }

const addAsset = async () => {
  if (!addForm.value.value) { ElMessage.warning('请输入地址'); return }
  addLoading.value = true
  try {
    const d = { asset_type: addForm.value.asset_type, value: addForm.value.value,
                port: addForm.value.port, tags: addForm.value.tags, note: addForm.value.note }
    await addAssetApi(d)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.value = { asset_type: 'domain', value: '', port: 443, tags: '', note: '' }
    fetchAssets(); fetchStats()
  } catch (e) { ElMessage.error('添加失败') } finally { addLoading.value = false }
}

const startEditTitle = (row) => { editingId.value = row.id; editTitle.value = row.title || '' }

const saveTitle = async (row) => {
  try {
    await updateAssetTitleApi(row.id, editTitle.value)
    row.title = editTitle.value
    editingId.value = null
    ElMessage.success('标题已更新')
  } catch { ElMessage.error('更新失败') }
}

const deleteAsset = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除资产 ' + row.value + '？', '确认', { type: 'warning' })
    await deleteAssetApi(row.id)
    ElMessage.success('已删除')
    fetchAssets(); fetchStats()
  } catch {}
}

const addIpRange = async () => {
  if (!ipForm.value.cidr) { ElMessage.warning('请输入 CIDR'); return }
  ipLoading.value = true
  try {
    await addIpRangeApi({ cidr: ipForm.value.cidr, note: ipForm.value.note })
    ElMessage.success('IP 段已添加')
    showIpDialog.value = false
    ipForm.value = { cidr: '', note: '' }
    fetchIpRanges()
  } catch { ElMessage.error('添加失败') } finally { ipLoading.value = false }
}

const deleteIpRange = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除 IP 段 ' + row.cidr + '？', '确认', { type: 'warning' })
    await deleteIpRangeApi(row.id)
    ElMessage.success('已删除')
    fetchIpRanges()
  } catch {}
}

const scanIpRange = async (row) => {
  try {
    await scanIpRangeApi(row.id, row.cidr, '80,443')
    ElMessage.success('IP 段 ' + row.cidr + ' 扫描已启动')
  } catch { ElMessage.error('启动扫描失败') }
}

const exportAssets = async () => {
  exporting.value = true
  try {
    const r = await exportAssetsApi()
    const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'assets_' + Date.now() + '.json'; a.click()
    URL.revokeObjectURL(url)
  } catch { ElMessage.error('导出失败') } finally { exporting.value = false }
}

const onFileChange = (uploadFile) => {
  batchFile.value = uploadFile
  const reader = new FileReader()
  reader.onload = (e) => { batchText.value = e.target.result }
  reader.readAsText(uploadFile.raw)
}

const doBatchImport = async () => {
  let text = batchText.value.trim()
  if (!text && !batchFile.value) {
    ElMessage.warning('请输入或上传数据')
    return
  }
  batchLoading.value = true
  try {
    const r = await batchImportAssetsApi({ text })
    const d = r.data
    ElMessage.success('导入完成：新增 ' + d.imported + ' 条' + (d.skipped > 0 ? '，跳过 ' + d.skipped + ' 条' : ''))
    showBatchDialog.value = false
    batchText.value = ''
    batchFile.value = null
    if (uploadRef.value) uploadRef.value.clearFiles()
    fetchAssets(); fetchStats()
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.error || e.message || ''))
  } finally { batchLoading.value = false }
}

const isGarbled = (s) => { if (!s) return false; return /[ھᆡ]/.test(s) || (s.length > 3 && /[?]/.test(s) && !/[\u4e00-\u9fa5]/.test(s)) }
const formatTime = (iso) => iso ? new Date(iso).toLocaleString('zh-CN', { timeZone:'Asia/Shanghai' }) : '-'
const typeLabel = (t) => ({ domain:'域名', ip:'IP', cert:'证书' }[t] || t)
const typeTag = (t) => ({ domain:'primary', ip:'success', cert:'warning' }[t] || 'info')
const statusLabel = (s) => ({ active:'活跃', inactive:'不活跃', unknown:'未知' }[s] || s)
const statusTag = (s) => ({ active:'success', inactive:'warning', unknown:'info' }[s] || 'info')

onMounted(() => { fetchAssets(); fetchStats(); fetchIpRanges() })
</script>

<style scoped>
.assets-page { padding: 20px; color: #1a1a2e; }

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 700; color: #1a1a2e; }
.header-actions { display: flex; gap: 8px; align-items: center; }

.stat-row { margin-bottom: 16px; }
.mini-stat { border-radius: 12px; padding: 14px 20px; }
.mstat-num { font-size: 24px; font-weight: 800; line-height: 1; }
.mstat-label { font-size: 12px; color: #8a94a6; margin-top: 4px; }

.filter-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; background: #fff; border-radius: 12px; padding: 12px 16px; border: 1px solid #e8eaed; }

.asset-table-wrap { background: #fff; border-radius: 16px; border: 1px solid #e8eaed; overflow: hidden; margin-bottom: 20px; }

.asset-value { font-size: 13px; font-weight: 500; }
.asset-value .scheme { color: #8a94a6; font-weight: 400; }
.asset-domain { font-size: 11px; color: #8a94a6; }
.title-cell { font-size: 13px; }
.title-cell.garbled { color: #f44; }

.pagination-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-top: 1px solid #f0f2f5; }
.pagination-info { font-size: 12px; color: #8a94a6; }

.ip-section { background: #fff; border-radius: 16px; border: 1px solid #e8eaed; padding: 16px 20px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-header h3 { margin: 0; font-size: 14px; font-weight: 600; color: #1a1a2e; }

.tags-cell { font-size: 12px; color: #8a94a6; }

.batch-tip { font-size: 12px; color: #8a94a6; margin-bottom: 8px }
.batch-format { background: #f8f9fb; border-radius: 8px; padding: 12px; margin-bottom: 4px; }
.format-label { font-size: 12px; color: #5a6474; font-weight: 500; margin-bottom: 4px; }
.format-example { font-family: 'Courier New', monospace; font-size: 12px; color: #5a6474; background: #fff; border: 1px solid #e8eaed; border-radius: 6px; padding: 8px; margin: 4px 0 0; white-space: pre-wrap; }
</style>
