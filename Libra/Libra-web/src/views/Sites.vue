<template>
  <div class="sites-page">
    <div class="page-header">
      <h2 class="page-title">🏢 资产管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="dialogVisible = true">
          <el-icon><Plus /></el-icon> 添加站点
        </el-button>
        <el-button @click="fetchSites" :icon="Refresh" circle />
      </div>
    </div>

    <!-- 统计 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-num">{{ sites.length }}</div>
          <div class="stat-label">站点总数</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-num">{{ enabledSites }}</div>
          <div class="stat-label">监控中</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card red">
          <div class="stat-num">{{ sslWarning }}</div>
          <div class="stat-label">SSL 告警</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card orange">
          <div class="stat-num">{{ sites.length - enabledSites }}</div>
          <div class="stat-label">已暂停</div>
        </div>
      </el-col>
    </el-row>

    <!-- 站点列表 -->
    <div class="white-card">
      <el-table :data="filteredSites" stripe v-loading="loading" empty-text="暂无站点，点击上方添加">
        <el-table-column label="站点名称" min-width="150">
          <template #default="{ row }">
            <div class="site-name">
              <el-tag v-if="!row.enabled" type="info" size="small">已暂停</el-tag>
              <span class="name-text">{{ row.name }}</span>
            </div>
            <div class="site-url">{{ row.url }}</div>
          </template>
        </el-table-column>
        <el-table-column label="部门" prop="org" width="120" />
        <el-table-column label="负责人" prop="owner" width="100" />
        <el-table-column label="扫描类型" width="110">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ scanTypeLabel(row.scan_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="SSL 状态" width="130">
          <template #default="{ row }">
            <template v-if="row.ssl_days_left !== null && row.ssl_days_left !== undefined">
              <el-tag v-if="row.ssl_days_left <= 0" type="danger" size="small">已过期</el-tag>
              <el-tag v-else-if="row.ssl_days_left <= row.ssl_expiry_warn" type="warning" size="small">
                {{ row.ssl_days_left }} 天到期
              </el-tag>
              <el-tag v-else type="success" size="small">{{ row.ssl_days_left }} 天</el-tag>
            </template>
            <el-tag v-else type="info" size="small">未检测</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="定时任务" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.schedule" type="primary" size="small">已设置</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleScan(row)">📋 扫描任务</el-button>
            <el-button text type="primary" size="small" @click="handleSslCheck(row)">SSL</el-button>
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingSite ? '编辑站点' : '添加站点'" width="560px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="站点名称" required>
          <el-input v-model="form.name" placeholder="例如：教务处" />
        </el-form-item>
        <el-form-item label="站点 URL" required>
          <el-input v-model="form.url" placeholder="https://jwc.qau.edu.cn" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="所属部门">
              <el-input v-model="form.org" placeholder="信息办" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input v-model="form.owner" placeholder="张三" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="扫描类型">
              <el-select v-model="form.scan_type" style="width:100%">
                <el-option value="HomePage_Scan" label="首页扫描" />
                <el-option value="SecondPage_Scan" label="二级页面扫描" />
                <el-option value="AllSite_Scan" label="全站扫描" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="SSL 告警阈值（天）">
              <el-input-number v-model="form.ssl_expiry_warn" :min="7" :max="365" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="定时任务（Cron 表达式）">
          <el-input v-model="form.schedule" placeholder="0 2 * * * (每天凌晨2点)" />
          <div class="form-tip">留空则不启用定时任务</div>
        </el-form-item>
        <el-form-item label="启用监控">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { getSites, createSite, updateSite, deleteSite, checkSiteSsl } from '../api/libra'

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
  HomePage_Scan: '首页扫描', SecondPage_Scan: '二级扫描', AllSite_Scan: '全站扫描'
}[t] || t)

const fetchSites = async () => {
  loading.value = true
  try {
    const r = await getSites()
    sites.value = r.data
  } catch (e) {
    ElMessage.error('获取站点列表失败')
  } finally { loading.value = false }
}

const handleEdit = (row) => {
  editingSite.value = row
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name || !form.value.url) {
    ElMessage.warning('请填写站点名称和 URL')
    return
  }
  saving.value = true
  try {
    if (editingSite.value) {
      await updateSite(editingSite.value.id, form.value)
      ElMessage.success('站点已更新')
    } else {
      await createSite(form.value)
      ElMessage.success('站点已添加')
    }
    dialogVisible.value = false
    fetchSites()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally { saving.value = false }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确定删除站点"${row.name}"？`, '确认删除', { type: 'warning' })
  try {
    await deleteSite(row.id)
    ElMessage.success('已删除')
    fetchSites()
  } catch { ElMessage.error('删除失败') }
}

const handleScan = (row) => {
  ElMessage.info(`跳转至扫描页面对 ${row.url} 发起扫描`)
  window.location.href = `/scan?url=${encodeURIComponent(row.url)}&type=${row.scan_type}`
}

const handleSslCheck = async (row) => {
  try {
    const r = await checkSiteSsl(row.id)
    const ssl = r.data.ssl || {}
    if (ssl.error) {
      ElMessage.error('SSL 检测失败：' + ssl.error)
    } else {
      ElMessage.success({
        message: `域名: ${ssl.domain}\n颁发机构: ${ssl.issuer}\n有效期: ${ssl.valid_from} ~ ${ssl.valid_until}\n剩余: ${ssl.days_left} 天`,
        duration: 6000
      })
    }
    fetchSites()
  } catch { ElMessage.error('SSL 检测请求失败') }
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
