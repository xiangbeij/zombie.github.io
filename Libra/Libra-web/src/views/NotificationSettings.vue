<template>
  <div class="notify-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">🔔 通知设置</h2>
        <p class="page-desc">配置告警通知渠道，发现威胁时自动推送通知</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog()">
          <el-icon><Plus /></el-icon> 添加通知渠道
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8"><div class="stat-card">
        <div class="stat-icon blue">📡</div>
        <div class="stat-body">
          <div class="stat-num blue">{{ channels.length }}</div>
          <div class="stat-label">已配置渠道</div>
        </div>
      </div></el-col>
      <el-col :span="8"><div class="stat-card">
        <div class="stat-icon green">✅</div>
        <div class="stat-body">
          <div class="stat-num green">{{ activeCount }}</div>
          <div class="stat-label">已启用</div>
        </div>
      </div></el-col>
      <el-col :span="8"><div class="stat-card">
        <div class="stat-icon orange">🚨</div>
        <div class="stat-body">
          <div class="stat-num orange">{{ failedCount }}</div>
          <div class="stat-label">本周失败通知</div>
        </div>
      </div></el-col>
    </el-row>

    <!-- 全局通知开关 -->
    <div class="white-card global-toggle">
      <div class="toggle-row">
        <div class="toggle-info">
          <h3>📣 全局通知总开关</h3>
          <p>关闭后将暂停所有渠道的通知推送</p>
        </div>
        <el-switch v-model="globalEnabled" @change="saveGlobal" />
      </div>
    </div>

    <!-- 通知渠道列表 -->
    <div class="section-title">📡 通知渠道</div>

    <div v-if="channels.length === 0" class="empty-state">
      <div class="empty-icon">📡</div>
      <div class="empty-title">暂无通知渠道</div>
      <div class="empty-desc">添加飞书或钉钉机器人，扫描发现威胁时自动推送通知</div>
      <el-button type="primary" @click="showAddDialog()">立即添加</el-button>
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
            <el-button text type="primary" size="small" @click="testChannel(ch)">🧪 测试</el-button>
            <el-button text type="primary" size="small" @click="showEditDialog(ch)">✏️ 编辑</el-button>
            <el-button text type="danger" size="small" @click="deleteChannel(ch.id)">🗑️ 删除</el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 支持场景 -->
    <div class="section-title" style="margin-top:24px">📋 支持的通知场景</div>
    <div class="white-card scene-grid">
      <div class="scene-item">
        <span class="scene-icon">🔗</span>
        <div class="scene-text">
          <div class="scene-title">发现暗链</div>
          <div class="scene-desc">扫描到隐藏的黑链、赌博/色情外链</div>
        </div>
      </div>
      <div class="scene-item">
        <span class="scene-icon">🐚</span>
        <div class="scene-text">
          <div class="scene-title">发现后门</div>
          <div class="scene-desc">检测到 WebShell 或可疑后门文件</div>
        </div>
      </div>
      <div class="scene-item">
        <span class="scene-icon">🚫</span>
        <div class="scene-text">
          <div class="scene-title">违规内容</div>
          <div class="scene-desc">发现敏感词或违规内容</div>
        </div>
      </div>
      <div class="scene-item">
        <span class="scene-icon">🏢</span>
        <div class="scene-text">
          <div class="scene-title">主页篡改</div>
          <div class="scene-desc">资产页面内容发生异常变化</div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑渠道弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑渠道' : '添加通知渠道'" width="520px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="渠道名称" required>
          <el-input v-model="form.name" placeholder="例如：运维告警飞书群" clearable />
        </el-form-item>

        <el-form-item label="渠道类型" required>
          <div class="type-grid">
            <div class="type-option" :class="{selected: form.channel_type === 'feishu'}" @click="form.channel_type = 'feishu'">
              <span class="type-icon">💬</span>
              <span class="type-name">飞书群</span>
            </div>
            <div class="type-option" :class="{selected: form.channel_type === 'dingtalk'}" @click="form.channel_type = 'dingtalk'">
              <span class="type-icon">🔔</span>
              <span class="type-name">钉钉群</span>
            </div>
            <div class="type-option" :class="{selected: form.channel_type === 'wecom'}" @click="form.channel_type = 'wecom'">
              <span class="type-icon">💬</span>
              <span class="type-name">企业微信</span>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="Webhook URL" required>
          <el-input v-model="form.webhook_url" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx" clearable />
          <div class="field-hint">
            💡 在{{ form.channel_type === 'feishu' ? '飞书' : form.channel_type === 'dingtalk' ? '钉钉' : '企业微信' }}群设置 → 智能群助手 → 添加机器人 → 复制 Webhook 地址
          </div>
        </el-form-item>

        <el-form-item label="加签密钥（可选）">
          <el-input v-model="form.secret" placeholder="机器人安全设置中的加签密钥" clearable />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.enabled">创建后立即启用</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChannel" :loading="saving">{{ editing ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api/libra'

const channels = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const saving = ref(false)
const globalEnabled = ref(true)
const form = ref({ name: '', channel_type: 'feishu', webhook_url: '', secret: '', enabled: true })
const editingId = ref(null)
const failedCount = ref(0)

const activeCount = computed(() => channels.value.filter(c => c.enabled).length)

const channelIcon = (t) => ({ feishu: '💬', dingtalk: '🔔', wecom: '💬', email: '📧', webhook: '🔗' }[t] || '📡')
const channelTypeLabel = (t) => ({ feishu: '飞书群机器人', dingtalk: '钉钉群机器人', wecom: '企业微信机器人', email: '邮件', webhook: '通用 Webhook' }[t] || t)
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
  if (!form.value.name.trim()) { ElMessage.warning('请输入渠道名称'); return }
  if (!form.value.webhook_url.trim()) { ElMessage.warning('请输入 Webhook URL'); return }
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
    ElMessage.success(editing.value ? '已保存' : '添加成功')
    dialogVisible.value = false
    fetchChannels()
  }).catch(e => ElMessage.error('保存失败: ' + (e.message || '')))
  .finally(() => { saving.value = false })
}

const toggleChannel = (ch) => {
  api.put('/notifications/channels/' + ch.id, { enabled: ch.enabled })
    .then(() => ElMessage.success(ch.enabled ? '已启用' : '已禁用'))
    .catch(() => { ch.enabled = !ch.enabled; ElMessage.error('操作失败') })
}

const testChannel = (ch) => {
  api.post('/notifications/channels/' + ch.id + '/test')
    .then(() => ElMessage.success('测试通知已发送，请检查是否收到'))
    .catch(() => ElMessage.error('发送失败，请检查配置是否正确'))
}

const deleteChannel = (id) => {
  ElMessageBox.confirm('确认删除该通知渠道？', '删除渠道').then(() => {
    api.delete('/notifications/channels/' + id)
      .then(() => { ElMessage.success('已删除'); channels.value = channels.value.filter(c => c.id !== id) })
      .catch(() => ElMessage.error('删除失败'))
  }).catch(() => {})
}

const saveGlobal = () => {
  api.put('/notifications/global', { enabled: globalEnabled.value })
    .then(() => ElMessage.success(globalEnabled.value ? '通知已启用' : '通知已暂停'))
    .catch(() => ElMessage.error('保存失败'))
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
