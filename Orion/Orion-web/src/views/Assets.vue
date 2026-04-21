<template>
  <div class="assets-page">
    <div class="page-header">
      <h2>馃洝锔?璧勪骇鍙戠幇</h2>
      <div class="header-actions">
        <el-button @click="refresh" :loading="loading" circle title="鍒锋柊">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button type="success" @click="showAddDialog = true">鉃?鎵嬪姩娣诲姞</el-button>
        <el-button type="primary" @click="showBatchDialog = true">馃摛 鎵归噺瀵煎叆</el-button>
        <el-button @click="exportAssets" :loading="exporting">馃摜 瀵煎嚭</el-button>
      </div>
    </div>

    <!-- 缁熻鍗＄墖 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="mini-stat" style="background:#eef2ff">
          <div class="mstat-num" style="color:#4f8ef7">{{ stats.total_assets || 0 }}</div>
          <div class="mstat-label">鎬昏祫浜?/div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat" style="background:#e8faf0">
          <div class="mstat-num" style="color:#00c853">{{ stats.by_status?.active || 0 }}</div>
          <div class="mstat-label">娲昏穬</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat" style="background:#fff8e0">
          <div class="mstat-num" style="color:#ff9800">{{ stats.ip_ranges || 0 }}</div>
          <div class="mstat-label">IP 娈?/div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat" style="background:#fff0f0">
          <div class="mstat-num" style="color:#f44">{{ stats.pending_alerts || 0 }}</div>
          <div class="mstat-label">寰呭鐞嗗憡璀?/div>
        </div>
      </el-col>
    </el-row>

    <!-- 鎼滅储 + 绛涢€?-->
    <div class="filter-bar">
      <el-input v-model="search" placeholder="鎼滅储鍩熷悕 / IP / 鏍囬" clearable style="max-width:300px" @change="page=1; fetchAssets()" />
      <el-select v-model="filterType" placeholder="璧勪骇绫诲瀷" clearable style="width:140px" @change="page=1; fetchAssets()">
        <el-option value="domain" label="鍩熷悕" />
        <el-option value="ip" label="IP" />
        <el-option value="cert" label="璇佷功" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="鐘舵€? clearable style="width:120px" @change="page=1; fetchAssets()">
        <el-option value="active" label="娲昏穬" />
        <el-option value="inactive" label="涓嶆椿璺? />
        <el-option value="unknown" label="鏈煡" />
      </el-select>
      <el-button @click="page=1; fetchAssets()">馃攳 鎼滅储</el-button>
    </div>

    <!-- 璧勪骇琛ㄦ牸 -->
    <div class="asset-table-wrap">
      <el-table :data="assets" v-loading="loading" stripe size="small" max-height="480"
        empty-text="鏆傛棤璧勪骇锛岀偣鍑讳笂鏂规寜閽坊鍔?>
        <el-table-column label="绫诲瀷" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.asset_type)" size="small">{{ typeLabel(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="鍩熷悕 / IP" min-width="180">
          <template #default="{ row }">
            <div class="asset-value">
              <span class="scheme">{{ row.scheme }}://</span>{{ row.value }}:{{ row.port }}
            </div>
            <div class="asset-domain">{{ row.value }}</div>
          </template>
        </el-table-column>
        <el-table-column label="缃戠珯鏍囬" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="editingId !== row.id" class="title-cell" :class="{ garbled: isGarbled(row.title) }">
              {{ row.title || '-' }}
            </span>
            <el-input v-else v-model="editTitle" size="small" maxlength="200" style="max-width:200px"
              @keyup.enter="saveTitle(row)" @keyup.escape="editingId = null" />
          </template>
        </el-table-column>
        <el-table-column label="鍗忚" width="90">
          <template #default="{ row }">{{ row.scheme }}:{{ row.port }}</template>
        </el-table-column>
        <el-table-column label="鐘舵€? width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="鏍囩" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="tags-cell">{{ row.tags || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="鏈€杩戝彂鐜? width="150">
          <template #default="{ row }">{{ formatTime(row.last_seen) }}</template>
        </el-table-column>
        <el-table-column label="鎿嶄綔" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="editingId !== row.id" text type="primary" size="small" @click="startEditTitle(row)">鉁忥笍 鏀规爣棰?/el-button>
            <el-button v-else text type="success" size="small" @click="saveTitle(row)">鉁?淇濆瓨</el-button>
            <el-button text type="danger" size="small" @click="deleteAsset(row)">馃棏锔?/el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 鍒嗛〉 -->
      <div class="pagination-bar">
        <span class="pagination-info">鍏?{{ total }} 鏉★紝绗?{{ page }} / {{ totalPages }} 椤?/span>
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

    <!-- IP 娈电鐞?-->
    <div class="ip-section">
      <div class="section-header">
        <h3>馃寪 IP 娈电鐞?/h3>
        <el-button size="small" type="primary" @click="showIpDialog = true">鉃?娣诲姞 IP 娈?/el-button>
      </div>
      <el-table :data="ipRanges" stripe size="small" max-height="200" v-loading="ipLoading"
        empty-text="鏆傛棤 IP 娈?>
        <el-table-column label="CIDR" prop="cidr" min-width="160" />
        <el-table-column label="澶囨敞" prop="note" min-width="200" show-overflow-tooltip />
        <el-table-column label="璧勪骇鏁? prop="asset_count" width="80" align="center" />
        <el-table-column label="鎿嶄綔" width="120">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="scanIpRange(row)">馃攳 鎵弿</el-button>
            <el-button text type="danger" size="small" @click="deleteIpRange(row)">馃棏锔?/el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 娣诲姞璧勪骇瀵硅瘽妗?-->
    <el-dialog v-model="showAddDialog" title="鉃?鎵嬪姩娣诲姞璧勪骇" width="480px">
      <el-form :model="addForm" label-width="90px">
        <el-form-item label="璧勪骇绫诲瀷">
          <el-select v-model="addForm.asset_type" style="width:100%">
            <el-option value="domain" label="鍩熷悕" />
            <el-option value="ip" label="IP" />
          </el-select>
        </el-form-item>
        <el-form-item label="鍦板潃">
          <el-input v-model="addForm.value" placeholder="example.com 鎴?1.2.3.4" />
        </el-form-item>
        <el-form-item label="绔彛">
          <el-input-number v-model="addForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="鏍囩">
          <el-input v-model="addForm.tags" placeholder="澶氫釜鏍囩鐢ㄩ€楀彿鍒嗛殧" />
        </el-form-item>
        <el-form-item label="澶囨敞">
          <el-input v-model="addForm.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">鍙栨秷</el-button>
        <el-button type="primary" @click="addAsset" :loading="addLoading">纭娣诲姞</el-button>
      </template>
    </el-dialog>

    <!-- 鎵归噺瀵煎叆瀵硅瘽妗?-->
    <el-dialog v-model="showBatchDialog" title="馃摛 鎵归噺瀵煎叆璧勪骇" width="620px" destroy-on-close>
      <div class="batch-tip">鏀寔浠ヤ笅鏍煎紡锛堢涓€琛屼細鑷姩璇嗗埆涓鸿〃澶达級锛?/div>
      <div class="batch-format">
        <div class="format-label">CSV 鏍煎紡绀轰緥锛?/div>
        <pre class="format-example">value,port,asset_type,tags,note
example.com,443,domain,瀹樼綉,涓荤珯
sub.example.com,443,domain,瀹樼綉,瀛愮珯
1.2.3.4,80,ip,鏈嶅姟鍣?娴嬭瘯鏈?/pre>
        <div class="format-label" style="margin-top:8px">鎴栫洿鎺ョ矘璐寸函鏂囨湰锛堟瘡琛屼竴涓湴鍧€锛夛細</div>
        <pre class="format-example">example.com
sub.example.com:8080
1.2.3.4</pre>
      </div>
      <el-tabs v-model="batchTab" style="margin-top:12px">
        <el-tab-pane label="馃搵 绮樿创鏂囨湰" name="text">
          <el-input v-model="batchText" type="textarea" :rows="8"
            placeholder="绮樿创 CSV 鍐呭鎴栨瘡琛屼竴涓湴鍧€锛屾敮鎸佹牸寮忥細&#10;value,port,type,tags&#10;example.com,443,domain,瀹樼綉&#10;鎴栫洿鎺ョ矘璐村湴鍧€鍒楄〃" />
        </el-tab-pane>
        <el-tab-pane label="馃搧 涓婁紶鏂囦欢" name="file">
          <el-upload ref="uploadRef" drag :auto-upload="false" :limit="1"
            accept=".csv,.txt,.xlsx,.xls" :on-change="onFileChange"
            style="text-align:center">
            <el-icon><UploadFilled /></el-icon>
            <div>鎷栨嫿鏂囦欢鍒版澶勶紝鎴?<em>鐐瑰嚮涓婁紶</em></div>
            <template #tip>
              <div class="el-upload__tip">鏀寔 CSV銆乀XT銆丒xcel 鏂囦欢</div>
            </template>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showBatchDialog = false">鍙栨秷</el-button>
        <el-button type="primary" @click="doBatchImport" :loading="batchLoading">
          纭瀵煎叆 {{ batchPreviewCount > 0 ? '(' + batchPreviewCount + ' 鏉?' : '' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 娣诲姞 IP 娈靛璇濇 -->
    <el-dialog v-model="showIpDialog" title="馃寪 娣诲姞 IP 娈? width="440px">
      <el-form :model="ipForm" label-width="80px">
        <el-form-item label="CIDR">
          <el-input v-model="ipForm.cidr" placeholder="210.44.49.0/28" />
        </el-form-item>
        <el-form-item label="澶囨敞">
          <el-input v-model="ipForm.note" placeholder="闈掑矝鍐滀笟澶у HPC 缃戞" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showIpDialog = false">鍙栨秷</el-button>
        <el-button type="primary" @click="addIpRange" :loading="ipLoading">纭</el-button>
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
         getAssetStats, exportAssetsApi, batchImportAssetsApi } from '../api/Orion'

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
    ElMessage.error('鑾峰彇璧勪骇鍒楄〃澶辫触')
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
  if (!addForm.value.value) { ElMessage.warning('璇疯緭鍏ュ湴鍧€'); return }
  addLoading.value = true
  try {
    const d = { asset_type: addForm.value.asset_type, value: addForm.value.value,
                port: addForm.value.port, tags: addForm.value.tags, note: addForm.value.note }
    await addAssetApi(d)
    ElMessage.success('娣诲姞鎴愬姛')
    showAddDialog.value = false
    addForm.value = { asset_type: 'domain', value: '', port: 443, tags: '', note: '' }
    fetchAssets(); fetchStats()
  } catch (e) { ElMessage.error('娣诲姞澶辫触') } finally { addLoading.value = false }
}

const startEditTitle = (row) => { editingId.value = row.id; editTitle.value = row.title || '' }

const saveTitle = async (row) => {
  try {
    await updateAssetTitleApi(row.id, editTitle.value)
    row.title = editTitle.value
    editingId.value = null
    ElMessage.success('鏍囬宸叉洿鏂?)
  } catch { ElMessage.error('鏇存柊澶辫触') }
}

const deleteAsset = async (row) => {
  try {
    await ElMessageBox.confirm('纭畾鍒犻櫎璧勪骇 ' + row.value + '锛?, '纭', { type: 'warning' })
    await deleteAssetApi(row.id)
    ElMessage.success('宸插垹闄?)
    fetchAssets(); fetchStats()
  } catch {}
}

const addIpRange = async () => {
  if (!ipForm.value.cidr) { ElMessage.warning('璇疯緭鍏?CIDR'); return }
  ipLoading.value = true
  try {
    await addIpRangeApi({ cidr: ipForm.value.cidr, note: ipForm.value.note })
    ElMessage.success('IP 娈靛凡娣诲姞')
    showIpDialog.value = false
    ipForm.value = { cidr: '', note: '' }
    fetchIpRanges()
  } catch { ElMessage.error('娣诲姞澶辫触') } finally { ipLoading.value = false }
}

const deleteIpRange = async (row) => {
  try {
    await ElMessageBox.confirm('纭畾鍒犻櫎 IP 娈?' + row.cidr + '锛?, '纭', { type: 'warning' })
    await deleteIpRangeApi(row.id)
    ElMessage.success('宸插垹闄?)
    fetchIpRanges()
  } catch {}
}

const scanIpRange = async (row) => {
  try {
    await scanIpRangeApi(row.id, row.cidr, '80,443')
    ElMessage.success('IP 娈?' + row.cidr + ' 鎵弿宸插惎鍔?)
  } catch { ElMessage.error('鍚姩鎵弿澶辫触') }
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
  } catch { ElMessage.error('瀵煎嚭澶辫触') } finally { exporting.value = false }
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
    ElMessage.warning('璇疯緭鍏ユ垨涓婁紶鏁版嵁')
    return
  }
  batchLoading.value = true
  try {
    const r = await batchImportAssetsApi({ text })
    const d = r.data
    ElMessage.success('瀵煎叆瀹屾垚锛氭柊澧?' + d.imported + ' 鏉? + (d.skipped > 0 ? '锛岃烦杩?' + d.skipped + ' 鏉? : ''))
    showBatchDialog.value = false
    batchText.value = ''
    batchFile.value = null
    if (uploadRef.value) uploadRef.value.clearFiles()
    fetchAssets(); fetchStats()
  } catch (e) {
    ElMessage.error('瀵煎叆澶辫触锛? + (e.response?.data?.error || e.message || ''))
  } finally { batchLoading.value = false }
}

const isGarbled = (s) => { if (!s) return false; return /[诰釂/.test(s) || (s.length > 3 && /[?]/.test(s) && !/[\u4e00-\u9fa5]/.test(s)) }
const formatTime = (iso) => iso ? new Date(iso).toLocaleString('zh-CN', { timeZone:'Asia/Shanghai' }) : '-'
const typeLabel = (t) => ({ domain:'鍩熷悕', ip:'IP', cert:'璇佷功' }[t] || t)
const typeTag = (t) => ({ domain:'primary', ip:'success', cert:'warning' }[t] || 'info')
const statusLabel = (s) => ({ active:'娲昏穬', inactive:'涓嶆椿璺?, unknown:'鏈煡' }[s] || s)
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
