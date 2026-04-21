<template>
  <div class="notify-page">
    <!-- 椤甸潰鏍囬 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">馃敂 閫氱煡璁剧疆</h2>
        <p class="page-desc">閰嶇疆鍛婅閫氱煡娓犻亾锛屽彂鐜板▉鑳佹椂鑷姩鎺ㄩ€侀€氱煡</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog()">
          <el-icon><Plus /></el-icon> 娣诲姞閫氱煡娓犻亾
        </el-button>
      </div>
    </div>

    <!-- 缁熻鍗＄墖 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8"><div class="stat-card">
        <div class="stat-icon blue">馃摗</div>
        <div class="stat-body">
          <div class="stat-num blue">{{ channels.length }}</div>
          <div class="stat-label">宸查厤缃笭閬?/div>
        </div>
      </div></el-col>
      <el-col :span="8"><div class="stat-card">
        <div class="stat-icon green">鉁?/div>
        <div class="stat-body">
          <div class="stat-num green">{{ activeCount }}</div>
          <div class="stat-label">宸插惎鐢?/div>
        </div>
      </div></el-col>
      <el-col :span="8"><div class="stat-card">
        <div class="stat-icon orange">馃毃</div>
        <div class="stat-body">
          <div class="stat-num orange">{{ failedCount }}</div>
          <div class="stat-label">鏈懆澶辫触閫氱煡</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 鍏ㄥ眬閫氱煡寮€鍏?-->
    <div class="white-card global-toggle">
      <div class="toggle-row">
        <div class="toggle-info">
          <h3>馃摚 鍏ㄥ眬閫氱煡鎬诲紑鍏?/h3>
          <p>鍏抽棴鍚庡皢鏆傚仠鎵€鏈夋笭閬撶殑閫氱煡鎺ㄩ€?/p>
        </div>
        <el-switch v-model="globalEnabled" @change="saveGlobal" />
      </div>
    </div>

    <!-- 閫氱煡娓犻亾鍒楄〃 -->
    <div class="section-title">馃摗 閫氱煡娓犻亾</div>

    <div v-if="channels.length === 0" class="empty-state">
      <div class="empty-icon">馃摗</div>
      <div class="empty-title">鏆傛棤閫氱煡娓犻亾</div>
      <div class="empty-desc">娣诲姞椋炰功鎴栭拤閽夋満鍣ㄤ汉锛屾壂鎻忓彂鐜板▉鑳佹椂鑷姩鎺ㄩ€侀€氱煡</div>
      <el-button type="primary" @click="showAddDialog()">绔嬪嵆娣诲姞</el-button>
    </div>

    <el-row :gutter="16" v-else>
      <el-col :span="12" v-for="ch in channels" :key="ch.id">
        <div class="channel-card" :class="{disabled: !ch.enabled}">
          <div class="channel-top">
            <div class="channel-info">
              <span class="channel-icon-lg">{{ channelIcon(ch.channel_type) }}</span>
              <div>
                <div class="channel-name-lg">{{ ch.name }}</div>
                <div class="channel-type-label">{{ channelTypeLabel(ch.channel_type) }}</div>
              </div>
            </div>
            <el-switch v-model="ch.enabled" @change="toggleChannel(ch)" />
          </div>

          <div class="channel-url" v-if="ch.config?.webhook_url">
            {{ maskUrl(ch.config.webhook_url) }}
          </div>

          <div class="channel-actions">
            <el-button text type="primary" size="small" @click="testChannel(ch)">馃И 娴嬭瘯</el-button>
            <el-button text type="primary" size="small" @click="showEditDialog(ch)">鉁忥笍 缂栬緫</el-button>
            <el-button text type="danger" size="small" @click="deleteChannel(ch.id)">馃棏锔?鍒犻櫎</el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 鏀寔鍦烘櫙 -->
    <div class="section-title" style="margin-top:24px">馃搵 鏀寔鐨勯€氱煡鍦烘櫙</div>
    <div class="white-card scene-grid">
      <div class="scene-item">
        <span class="scene-icon">馃敆</span>
        <div class="scene-text">
          <div class="scene-title">鍙戠幇鏆楅摼</div>
          <div class="scene-desc">鎵弿鍒伴殣钘忕殑榛戦摼銆佽祵鍗?鑹叉儏澶栭摼</div>
        </div>
      </div>
      <div class="scene-item">
        <span class="scene-icon">馃悮</span>
        <div class="scene-text">
          <div class="scene-title">鍙戠幇鍚庨棬</div>
          <div class="scene-desc">妫€娴嬪埌 WebShell 鎴栧彲鐤戝悗闂ㄦ枃浠?/div>
        </div>
      </div>
      <div class="scene-item">
        <span class="scene-icon">馃毇</span>
        <div class="scene-text">
          <div class="scene-title">杩濊鍐呭</div>
          <div class="scene-desc">鍙戠幇鏁忔劅璇嶆垨杩濊鍐呭</div>
        </div>
      </div>
      <div class="scene-item">
        <span class="scene-icon">馃彚</span>
        <div class="scene-text">
          <div class="scene-title">涓婚〉绡℃敼</div>
          <div class="scene-desc">璧勪骇椤甸潰鍐呭鍙戠敓寮傚父鍙樺寲</div>
        </div>
      </div>
    </div>

    <!-- 娣诲姞/缂栬緫娓犻亾寮圭獥 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '缂栬緫娓犻亾' : '娣诲姞閫氱煡娓犻亾'" width="520px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="娓犻亾鍚嶇О" required>
          <el-input v-model="form.name" placeholder="渚嬪锛氳繍缁村憡璀﹂涔︾兢" clearable />
        </el-form-item>

        <el-form-item label="娓犻亾绫诲瀷" required>
          <div class="type-grid">
            <div class="type-option" :class="{selected: form.channel_type === 'feishu'}" @click="form.channel_type = 'feishu'">
              <span class="type-icon">馃挰</span>
              <span class="type-name">椋炰功缇?/span>
            </div>
            <div class="type-option" :class="{selected: form.channel_type === 'dingtalk'}" @click="form.channel_type = 'dingtalk'">
              <span class="type-icon">馃敂</span>
              <span class="type-name">閽夐拤缇?/span>
            </div>
            <div class="type-option" :class="{selected: form.channel_type === 'wecom'}" @click="form.channel_type = 'wecom'">
              <span class="type-icon">馃挰</span>
              <span class="type-name">浼佷笟寰俊</span>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="Webhook URL" required>
          <el-input v-model="form.webhook_url" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx" clearable />
          <div class="field-hint">
            馃挕 鍦▄{ form.channel_type === 'feishu' ? '椋炰功' : form.channel_type === 'dingtalk' ? '閽夐拤' : '浼佷笟寰俊' }}缇よ缃?鈫?鏅鸿兘缇ゅ姪鎵?鈫?娣诲姞鏈哄櫒浜?鈫?澶嶅埗 Webhook 鍦板潃
          </div>
        </el-form-item>

        <el-form-item label="鍔犵瀵嗛挜锛堝彲閫夛級">
          <el-input v-model="form.secret" placeholder="鏈哄櫒浜哄畨鍏ㄨ缃腑鐨勫姞绛惧瘑閽? clearable />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.enabled">鍒涘缓鍚庣珛鍗冲惎鐢?/el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">鍙栨秷</el-button>
        <el-button type="primary" @click="saveChannel" :loading="saving">{{ editing ? '淇濆瓨' : '娣诲姞' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api/Orion'

const channels = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const saving = ref(false)
const globalEnabled = ref(true)
const form = ref({ name: '', channel_type: 'feishu', webhook_url: '', secret: '', enabled: true })
const editingId = ref(null)
const failedCount = ref(0)

const activeCount = computed(() => channels.value.filter(c => c.enabled).length)

const channelIcon = (t) => ({ feishu: '馃挰', dingtalk: '馃敂', wecom: '馃挰', email: '馃摟', webhook: '馃敆' }[t] || '馃摗')
const channelTypeLabel = (t) => ({ feishu: '椋炰功缇ゆ満鍣ㄤ汉', dingtalk: '閽夐拤缇ゆ満鍣ㄤ汉', wecom: '浼佷笟寰俊鏈哄櫒浜?, email: '閭欢', webhook: '閫氱敤 Webhook' }[t] || t)
const maskUrl = (url) => {
  if (!url) return ''
  const idx = url.indexOf('hook/')
  if (idx < 0) return url.substring(0, 30) + '...'
  return url.substring(0, idx + 5) + '/***/***'
}

const showAddDialog = () => {
  editing.value = false
  editingId.value = null
  form.value = { name: '', channel_type: 'feishu', webhook_url: '', secret: '', enabled: true }
  dialogVisible.value = true
}

const showEditDialog = (ch) => {
  editing.value = true
  editingId.value = ch.id
  form.value = {
    name: ch.name,
    channel_type: ch.channel_type,
    webhook_url: ch.config?.webhook_url || '',
    secret: ch.config?.secret || '',
    enabled: ch.enabled,
  }
  dialogVisible.value = true
}

const saveChannel = () => {
  if (!form.value.name.trim()) { ElMessage.warning('璇疯緭鍏ユ笭閬撳悕绉?); return }
  if (!form.value.webhook_url.trim()) { ElMessage.warning('璇疯緭鍏?Webhook URL'); return }
  saving.value = true

  const payload = {
    name: form.value.name.trim(),
    channel_type: form.value.channel_type,
    enabled: form.value.enabled,
    config: {
      webhook_url: form.value.webhook_url.trim(),
      secret: form.value.secret.trim(),
    }
  }

  const req = editing.value
    ? api.put('/notifications/channels/' + editingId.value, payload)
    : api.post('/notifications/channels', payload)

  req.then(() => {
    ElMessage.success(editing.value ? '宸蹭繚瀛? : '娣诲姞鎴愬姛')
    dialogVisible.value = false
    fetchChannels()
  }).catch(e => ElMessage.error('淇濆瓨澶辫触: ' + (e.message || '')))
  .finally(() => { saving.value = false })
}

const toggleChannel = (ch) => {
  api.put('/notifications/channels/' + ch.id, { enabled: ch.enabled })
    .then(() => ElMessage.success(ch.enabled ? '宸插惎鐢? : '宸茬鐢?))
    .catch(() => { ch.enabled = !ch.enabled; ElMessage.error('鎿嶄綔澶辫触') })
}

const testChannel = (ch) => {
  api.post('/notifications/channels/' + ch.id + '/test')
    .then(() => ElMessage.success('娴嬭瘯閫氱煡宸插彂閫侊紝璇锋鏌ユ槸鍚︽敹鍒?))
    .catch(() => ElMessage.error('鍙戦€佸け璐ワ紝璇锋鏌ラ厤缃槸鍚︽纭?))
}

const deleteChannel = (id) => {
  ElMessageBox.confirm('纭鍒犻櫎璇ラ€氱煡娓犻亾锛?, '鍒犻櫎娓犻亾').then(() => {
    api.delete('/notifications/channels/' + id)
      .then(() => { ElMessage.success('宸插垹闄?); channels.value = channels.value.filter(c => c.id !== id) })
      .catch(() => ElMessage.error('鍒犻櫎澶辫触'))
  }).catch(() => {})
}

const saveGlobal = () => {
  api.put('/notifications/global', { enabled: globalEnabled.value })
    .then(() => ElMessage.success(globalEnabled.value ? '閫氱煡宸插惎鐢? : '閫氱煡宸叉殏鍋?))
    .catch(() => ElMessage.error('淇濆瓨澶辫触'))
}

const fetchChannels = () => {
  api.get('/notifications/channels').then(r => {
    channels.value = r.data.channels || []
  }).catch(() => {})
}

onMounted(() => {
  fetchChannels()
})
</script>

<style scoped>
.notify-page { color: #1a1a2e; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: #8a94a6; }
.header-actions { display: flex; gap: 8px; }

.white-card {
  background: #ffffff; border-radius: 14px; padding: 20px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 14px; }

.stat-row { margin-bottom: 16px; }
.stat-card {
  display: flex; align-items: center; gap: 14px;
  background: #ffffff; border-radius: 14px; padding: 18px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.stat-icon { font-size: 28px; }
.stat-body { flex: 1; }
.stat-num { font-size: 28px; font-weight: 800; color: #4f8ef7; line-height: 1; }
.stat-num.green { color: #00c853; }
.stat-num.orange { color: #ff9800; }
.stat-label { font-size: 12px; color: #8a94a6; margin-top: 4px; }

.global-toggle { margin-bottom: 16px; }
.toggle-row { display: flex; justify-content: space-between; align-items: center; }
.toggle-info h3 { margin: 0 0 2px; font-size: 15px; font-weight: 600; }
.toggle-info p { margin: 0; font-size: 12px; color: #8a94a6; }

.section-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }

.empty-state {
  text-align: center; padding: 48px; background: #ffffff;
  border-radius: 14px; border: 1px solid #e8eaed;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-title { font-size: 16px; font-weight: 600; color: #1a1a2e; margin-bottom: 6px; }
.empty-desc { font-size: 13px; color: #8a94a6; margin-bottom: 20px; }

.channel-card {
  background: #ffffff; border-radius: 14px; padding: 18px;
  border: 1px solid #e8eaed; margin-bottom: 16px;
  transition: all 0.2s;
}
.channel-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.channel-card.disabled { opacity: 0.6; }
.channel-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.channel-info { display: flex; align-items: center; gap: 12px; }
.channel-icon-lg { font-size: 32px; }
.channel-name-lg { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.channel-type-label { font-size: 12px; color: #8a94a6; }
.channel-url { font-size: 12px; color: #8a94a6; margin-bottom: 10px; font-family: 'Courier New', monospace; background: #f8f9fb; padding: 4px 8px; border-radius: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.channel-actions { display: flex; gap: 8px; }

.scene-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.scene-item {
  display: flex; align-items: center; gap: 12px;
  background: #f8f9fb; border-radius: 10px; padding: 14px;
}
.scene-icon { font-size: 24px; }
.scene-title { font-size: 13px; font-weight: 600; color: #1a1a2e; }
.scene-desc { font-size: 11px; color: #8a94a6; }

.type-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.type-option {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 14px; border-radius: 10px; border: 2px solid #e8eaed; cursor: pointer;
  transition: all 0.15s;
}
.type-option:hover { border-color: #4f8ef7; background: #f0f4ff; }
.type-option.selected { border-color: #4f8ef7; background: #eef2ff; }
.type-icon { font-size: 24px; }
.type-name { font-size: 12px; font-weight: 500; color: #1a1a2e; }

.field-hint { font-size: 12px; color: #8a94a6; margin-top: 4px; line-height: 1.5; }
</style>
