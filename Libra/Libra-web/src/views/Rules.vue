<template>
  <div class="rules-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">🛡️ 规则管理</h2>
        <p class="page-desc">配置暗链、后门、违规内容检测规则</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog" plain>
          <el-icon><Plus /></el-icon> 新增规则
        </el-button>
      </div>
    </div>

    <!-- 统计概览 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6"><div class="stat-card">
        <div class="stat-icon">⛓️</div>
        <div class="stat-body">
          <div class="stat-num danger">{{ rulesSummary.blacklink_rules || 0 }}</div>
          <div class="stat-label">暗链规则</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card">
        <div class="stat-icon">🐚</div>
        <div class="stat-body">
          <div class="stat-num danger">{{ rulesSummary.backdoor_rules || 0 }}</div>
          <div class="stat-label">后门规则</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card">
        <div class="stat-icon">🚫</div>
        <div class="stat-body">
          <div class="stat-num warn">{{ rulesSummary.violativelink_rules || 0 }}</div>
          <div class="stat-label">违规规则</div>
        </div>
      </div></el-col>
      <el-col :span="6"><div class="stat-card">
        <div class="stat-icon">🛤️</div>
        <div class="stat-body">
          <div class="stat-num">{{ rulesSummary.backdoor_paths || 0 }}</div>
          <div class="stat-label">后门路径</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- Tab 切换规则类型 -->
    <el-tabs v-model="activeTab" @tab-change="fetchRules" class="rules-tabs">
      <el-tab-pane label="🔗 暗链规则" name="blacklink">
        <div class="tab-toolbar">
          <el-input v-model="blSearch" placeholder="搜索规则" clearable size="default" style="width:220px" @input="debounceBlSearch">
            <template #prefix><span>🔍</span></template>
          </el-input>
        </div>
        <el-table :data="blRules" v-loading="blLoading" stripe size="small" class="rules-table">
          <el-table-column label="规则内容" min-width="300" prop="pattern">
            <template #default="{ row }">
              <span class="rule-pattern">{{ row.pattern }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100" prop="type" />
          <el-table-column label="风险等级" width="100">
            <template #default="{ row }">
              <el-tag :type="riskTagType(row.risk_level)" size="small">{{ row.risk_level || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="命中次数" width="100" align="center" prop="hit_count" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="editRule(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="deleteRule(row.id, 'blacklink')">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="blRules.length === 0 && !blLoading" class="empty-state">暂无暗链规则</div>
      </el-tab-pane>

      <el-tab-pane label="🐚 后门规则" name="backdoor">
        <div class="tab-toolbar">
          <el-input v-model="bdSearch" placeholder="搜索规则" clearable size="default" style="width:220px" @input="debounceBdSearch">
            <template #prefix><span>🔍</span></template>
          </el-input>
        </div>
        <el-table :data="bdRules" v-loading="bdLoading" stripe size="small" class="rules-table">
          <el-table-column label="规则内容" min-width="300" prop="pattern">
            <template #default="{ row }">
              <span class="rule-pattern">{{ row.pattern }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100" prop="type" />
          <el-table-column label="命中次数" width="100" align="center" prop="hit_count" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="editRule(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="deleteRule(row.id, 'backdoor')">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="bdRules.length === 0 && !bdLoading" class="empty-state">暂无后门规则</div>
      </el-tab-pane>

      <el-tab-pane label="🚫 违规规则" name="violativelink">
        <div class="tab-toolbar">
          <el-input v-model="vlSearch" placeholder="搜索规则" clearable size="default" style="width:220px" @input="debounceVlSearch">
            <template #prefix><span>🔍</span></template>
          </el-input>
        </div>
        <el-table :data="vlRules" v-loading="vlLoading" stripe size="small" class="rules-table">
          <el-table-column label="规则内容" min-width="300" prop="pattern">
            <template #default="{ row }">
              <span class="rule-pattern">{{ row.pattern }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100" prop="type" />
          <el-table-column label="命中次数" width="100" align="center" prop="hit_count" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="editRule(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="deleteRule(row.id, 'violativelink')">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="vlRules.length === 0 && !vlLoading" class="empty-state">暂无违规规则</div>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="500px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="规则类型" required>
          <el-select v-model="form.rule_type" style="width:100%">
            <el-option value="blacklink" label="暗链规则" />
            <el-option value="backdoor" label="后门规则" />
            <el-option value="violativelink" label="违规规则" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则内容（正则表达式）" required>
          <el-input v-model="form.pattern" placeholder="例如: gamble|pharma|sex" clearable />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="form.risk_level" style="width:100%">
            <el-option value="high" label="高风险" />
            <el-option value="medium" label="中风险" />
            <el-option value="low" label="低风险" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRule" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api/libra'

const activeTab = ref('blacklink')
const rulesSummary = ref({})
const blRules = ref([])
const bdRules = ref([])
const vlRules = ref([])
const blLoading = ref(false)
const bdLoading = ref(false)
const vlLoading = ref(false)
const blSearch = ref('')
const bdSearch = ref('')
const vlSearch = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = ref({ rule_type: 'blacklink', pattern: '', risk_level: 'medium' })

const fetchRules = () => {
  if (activeTab.value === 'blacklink') fetchBlacklink()
  else if (activeTab.value === 'backdoor') fetchBackdoor()
  else fetchViolativelink()
}

const fetchSummary = () => {
  api.get('/rules').then(r => {
    rulesSummary.value = r.data || {}
    // Also fetch actual rule lists for display
    fetchBlacklink()
    fetchBackdoor()
    fetchViolativelink()
  }).catch(() => {})
}

const fetchBlacklink = () => {
  blLoading.value = true
  api.get('/rules/blacklink').then(r => {
    const data = Array.isArray(r.data) ? r.data : (r.data?.rules || [])
    blRules.value = data
  }).catch(() => { blRules.value = [] }).finally(() => { blLoading.value = false })
}

const fetchBackdoor = () => {
  bdLoading.value = true
  api.get('/rules/backdoor').then(r => {
    const data = Array.isArray(r.data) ? r.data : (r.data?.rules || [])
    bdRules.value = data
  }).catch(() => { bdRules.value = [] }).finally(() => { bdLoading.value = false })
}

const fetchViolativelink = () => {
  vlLoading.value = true
  api.get('/rules/violativelink').then(r => {
    const data = Array.isArray(r.data) ? r.data : (r.data?.rules || [])
    vlRules.value = data
  }).catch(() => { vlRules.value = [] }).finally(() => { vlLoading.value = false })
}

let blTimer = null, bdTimer = null, vlTimer = null
const debounceBlSearch = () => { clearTimeout(blTimer); blTimer = setTimeout(fetchBlacklink, 300) }
const debounceBdSearch = () => { clearTimeout(bdTimer); bdTimer = setTimeout(fetchBackdoor, 300) }
const debounceVlSearch = () => { clearTimeout(vlTimer); vlTimer = setTimeout(fetchViolativelink, 300) }

const showAddDialog = () => {
  editingId.value = null
  form.value = { rule_type: activeTab.value === 'blacklink' ? 'blacklink' : activeTab.value === 'backdoor' ? 'backdoor' : 'violativelink', pattern: '', risk_level: 'medium' }
  dialogVisible.value = true
}

const editRule = (row) => {
  editingId.value = row.id
  form.value = { rule_type: row.type || activeTab.value, pattern: row.pattern || '', risk_level: row.risk_level || 'medium' }
  dialogVisible.value = true
}

const saveRule = () => {
  if (!form.value.pattern.trim()) { ElMessage.warning('请输入规则内容'); return }
  saving.value = true
  const payload = { pattern: form.value.pattern, type: form.value.rule_type, risk_level: form.value.risk_level }
  const req = editingId.value ? api.put('/rules/' + editingId.value, payload) : api.post('/rules', payload)
  req.then(() => {
    ElMessage.success(editingId.value ? '已保存' : '已添加')
    dialogVisible.value = false
    fetchSummary()
  }).catch(e => ElMessage.error('保存失败: ' + (e.message || ''))).finally(() => { saving.value = false })
}

const deleteRule = (id, type) => {
  ElMessageBox.confirm('确认删除该规则？', '删除').then(() => {
    api.delete('/rules/' + id).then(() => {
      ElMessage.success('已删除')
      fetchSummary()
    }).catch(() => ElMessage.error('删除失败'))
  }).catch(() => {})
}

const riskTagType = (r) => ({ high: 'danger', medium: 'warning', low: 'success' }[r] || 'info')

onMounted(fetchSummary)
</script>

<style scoped>
.rules-page { color: #1a1a2e; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: #8a94a6; }
.header-actions { display: flex; gap: 8px; }
.stat-row { margin-bottom: 20px; }
.stat-card {
  display: flex; align-items: center; gap: 14px;
  background: #ffffff; border-radius: 14px; padding: 18px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  min-height: 80px;
}
.stat-icon { font-size: 26px; }
.stat-body { flex: 1; }
.stat-num { font-size: 24px; font-weight: 800; color: #4f8ef7; line-height: 1; min-height: 29px; display: flex; align-items: center; }
.stat-num.danger { color: #f44; }
.stat-num.warn { color: #ff9800; }
.stat-label { font-size: 12px; color: #8a94a6; margin-top: 4px; }
.rules-tabs { background: #ffffff; border-radius: 14px; padding: 20px; border: 1px solid #e8eaed; }
.tab-toolbar { margin-bottom: 12px; }
.rules-table { margin-top: 4px; }
.rule-pattern { font-family: 'Courier New', monospace; font-size: 13px; color: #1a1a2e; }
.empty-state { text-align: center; padding: 40px; color: #8a94a6; font-size: 14px; }
</style>