<template>
  <div class="sites-page">
    <div class="page-header">
      <h2 class="page-title">馃彚 璧勪骇绠＄悊</h2>
      <div class="header-actions">
        <el-button type="primary" @click="dialogVisible = true">
          <el-icon><Plus /></el-icon> 娣诲姞绔欑偣
        </el-button>
        <el-button @click="fetchSites" :icon="Refresh" circle />
      </div>
    </div>

    <!-- 缁熻 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-num">{{ sites.length }}</div>
          <div class="stat-label">绔欑偣鎬绘暟</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-num">{{ enabledSites }}</div>
          <div class="stat-label">鐩戞帶涓?/div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card red">
          <div class="stat-num">{{ sslWarning }}</div>
          <div class="stat-label">SSL 鍛婅</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card orange">
          <div class="stat-num">{{ sites.length - enabledSites }}</div>
          <div class="stat-label">宸叉殏鍋?/div>
        </div>
      </el-col>
    </el-row>

    <!-- 绔欑偣鍒楄〃 -->
    <div class="white-card">
      <el-table :data="filteredSites" stripe v-loading="loading" empty-text="鏆傛棤绔欑偣锛岀偣鍑讳笂鏂规坊鍔?>
        <el-table-column label="绔欑偣鍚嶇О" min-width="150">
          <template #default="{ row }">
            <div class="site-name">
              <el-tag v-if="!row.enabled" type="info" size="small">宸叉殏鍋?/el-tag>
              <span class="name-text">{{ row.name }}</span>
            </div>
            <div class="site-url">{{ row.url }}</div>
          </template>
        </el-table-column>
        <el-table-column label="閮ㄩ棬" prop="org" width="120" />
        <el-table-column label="璐熻矗浜? prop="owner" width="100" />
        <el-table-column label="鎵弿绫诲瀷" width="110">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ scanTypeLabel(row.scan_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="SSL 鐘舵€? width="130">
          <template #default="{ row }">
            <template v-if="row.ssl_days_left !== null && row.ssl_days_left !== undefined">
              <el-tag v-if="row.ssl_days_left <= 0" type="danger" size="small">宸茶繃鏈?/el-tag>
              <el-tag v-else-if="row.ssl_days_left <= row.ssl_expiry_warn" type="warning" size="small">
                {{ row.ssl_days_left }} 澶╁埌鏈?              </el-tag>
              <el-tag v-else type="success" size="small">{{ row.ssl_days_left }} 澶?/el-tag>
            </template>
            <el-tag v-else type="info" size="small">鏈娴?/el-tag>
          </template>
        </el-table-column>
        <el-table-column label="瀹氭椂浠诲姟" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.schedule" type="primary" size="small">宸茶缃?/el-tag>
            <span v-else class="muted">鈥?/span>
          </template>
        </el-table-column>
        <el-table-column label="鎿嶄綔" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleScan(row)">馃搵 鎵弿浠诲姟</el-button>
            <el-button text type="primary" size="small" @click="handleSslCheck(row)">SSL</el-button>
            <el-button text type="primary" size="small" @click="handleEdit(row)">缂栬緫</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">鍒犻櫎</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 娣诲姞/缂栬緫寮圭獥 -->
    <el-dialog v-model="dialogVisible" :title="editingSite ? '缂栬緫绔欑偣' : '娣诲姞绔欑偣'" width="560px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="绔欑偣鍚嶇О" required>
          <el-input v-model="form.name" placeholder="渚嬪锛氭暀鍔″" />
        </el-form-item>
        <el-form-item label="绔欑偣 URL" required>
          <el-input v-model="form.url" placeholder="https://jwc.qau.edu.cn" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="鎵€灞為儴闂?>
              <el-input v-model="form.org" placeholder="淇℃伅鍔? />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="璐熻矗浜?>
              <el-input v-model="form.owner" placeholder="寮犱笁" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="鎵弿绫诲瀷">
              <el-select v-model="form.scan_type" style="width:100%">
                <el-option value="HomePage_Scan" label="棣栭〉鎵弿" />
                <el-option value="SecondPage_Scan" label="浜岀骇椤甸潰鎵弿" />
                <el-option value="AllSite_Scan" label="鍏ㄧ珯鎵弿" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="SSL 鍛婅闃堝€硷紙澶╋級">
              <el-input-number v-model="form.ssl_expiry_warn" :min="7" :max="365" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="瀹氭椂浠诲姟锛圕ron 琛ㄨ揪寮忥級">
          <el-input v-model="form.schedule" placeholder="0 2 * * * (姣忓ぉ鍑屾櫒2鐐?" />
          <div class="form-tip">鐣欑┖鍒欎笉鍚敤瀹氭椂浠诲姟</div>
        </el-form-item>
        <el-form-item label="鍚敤鐩戞帶">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">鍙栨秷</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">淇濆瓨</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { getSites, createSite, updateSite, deleteSite, checkSiteSsl } from '../api/Orion'

const sites = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingSite = ref(null)

const form = ref({
  name: '', url: '', org: '', owner: '', contact: '',
  scan_type: 'HomePage_Scan', schedule: '', enabled: true, ssl_expiry_warn: 30
})

const enabledSites = computed(() => sites.value.filter(s => s.enabled).length)
const sslWarning = computed(() => sites.value.filter(s => s.ssl_days_left !== null && s.ssl_days_left <= s.ssl_expiry_warn).length)
const filteredSites = computed(() => sites.value)

const scanTypeLabel = (t) => ({
  HomePage_Scan: '棣栭〉鎵弿', SecondPage_Scan: '浜岀骇鎵弿', AllSite_Scan: '鍏ㄧ珯鎵弿'
}[t] || t)

const fetchSites = async () => {
  loading.value = true
  try {
    const r = await getSites()
    sites.value = r.data
  } catch (e) {
    ElMessage.error('鑾峰彇绔欑偣鍒楄〃澶辫触')
  } finally { loading.value = false }
}

const handleEdit = (row) => {
  editingSite.value = row
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name || !form.value.url) {
    ElMessage.warning('璇峰～鍐欑珯鐐瑰悕绉板拰 URL')
    return
  }
  saving.value = true
  try {
    if (editingSite.value) {
      await updateSite(editingSite.value.id, form.value)
      ElMessage.success('绔欑偣宸叉洿鏂?)
    } else {
      await createSite(form.value)
      ElMessage.success('绔欑偣宸叉坊鍔?)
    }
    dialogVisible.value = false
    fetchSites()
  } catch (e) {
    ElMessage.error('淇濆瓨澶辫触')
  } finally { saving.value = false }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`纭畾鍒犻櫎绔欑偣"${row.name}"锛焋, '纭鍒犻櫎', { type: 'warning' })
  try {
    await deleteSite(row.id)
    ElMessage.success('宸插垹闄?)
    fetchSites()
  } catch { ElMessage.error('鍒犻櫎澶辫触') }
}

const handleScan = (row) => {
  ElMessage.info(`璺宠浆鑷虫壂鎻忛〉闈㈠ ${row.url} 鍙戣捣鎵弿`)
  window.location.href = `/scan?url=${encodeURIComponent(row.url)}&type=${row.scan_type}`
}

const handleSslCheck = async (row) => {
  try {
    const r = await checkSiteSsl(row.id)
    const ssl = r.data.ssl || {}
    if (ssl.error) {
      ElMessage.error('SSL 妫€娴嬪け璐ワ細' + ssl.error)
    } else {
      ElMessage.success({
        message: `鍩熷悕: ${ssl.domain}\n棰佸彂鏈烘瀯: ${ssl.issuer}\n鏈夋晥鏈? ${ssl.valid_from} ~ ${ssl.valid_until}\n鍓╀綑: ${ssl.days_left} 澶ー,
        duration: 6000
      })
    }
    fetchSites()
  } catch { ElMessage.error('SSL 妫€娴嬭姹傚け璐?) }
}

onMounted(() => { fetchSites() })
</script>

<style scoped>
.sites-page { color: #1a1a2e; }

.page-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;
}
.page-title { margin: 0; font-size: 22px; font-weight: 600; color: #1a1a2e; }
.header-actions { display: flex; gap: 8px; align-items: center; }

.stat-row { margin-bottom: 20px; }
.stat-card {
  background: #ffffff; border-radius: 14px; padding: 18px;
  border: 1px solid #e0e4ec; text-align: center;
}
.stat-num { font-size: 28px; font-weight: 800; color: #1a1a2e; }
.stat-label { font-size: 12px; color: #5a6474; margin-top: 4px; }
.stat-card.green .stat-num { color: #1a9a5c; }
.stat-card.red .stat-num { color: #c02020; }
.stat-card.orange .stat-num { color: #c05c00; }

.white-card {
  background: #ffffff; border-radius: 16px; padding: 20px;
  border: 1px solid #e0e4ec;
}

.site-name { display: flex; align-items: center; gap: 6px; }
.name-text { font-weight: 600; color: #1a1a2e; font-size: 14px; }
.site-url { font-size: 12px; color: #8a94a6; margin-top: 2px; }
.muted { color: #aab0bc; }

.form-tip { font-size: 11px; color: #8a94a6; margin-top: 4px; }
</style>
