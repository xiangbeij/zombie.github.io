<template>
  <div class="settings-page">
    <div class="page-header">
      <h2 class="page-title">⚙️ 系统设置</h2>
    </div>

    <!-- AI 分析设置 -->
    <div class="white-card">
      <div class="section-title">🤖 AI 分析设置</div>

      <el-form label-position="top" size="large">
        <el-form-item label="AI 模式">
          <el-radio-group v-model="aiMode" @change="onAiModeChange">
            <el-radio-button value="local">本地 Ollama</el-radio-button>
            <el-radio-button value="cloud">云端 AI</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="aiMode === 'local'">
          <el-form-item label="Ollama 服务地址">
            <el-input v-model="localEndpoint" placeholder="http://localhost:11434" size="large" />
            <div class="field-hint">本地部署的 Ollama 服务地址，默认 http://localhost:11434</div>
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="localModel" placeholder="qwen2.5:7b" size="large" />
            <div class="field-hint">在 Ollama 中运行的模型名称</div>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="API 接口地址">
            <el-input v-model="cloudEndpoint" placeholder="https://api.example.com/v1/chat/completions" size="large" />
            <div class="field-hint">云端大模型 API 地址（如 OpenAI、Claude 等）</div>
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="cloudApiKey" type="password" placeholder="sk-..." size="large" show-password />
            <div class="field-hint">云端 AI 服务的 API Key（将安全存储）</div>
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="cloudModel" placeholder="gpt-4o-mini" size="large" />
            <div class="field-hint">云端模型名称，如 gpt-4o-mini、claude-3-haiku 等</div>
          </el-form-item>
        </template>

        <el-form-item>
          <el-button type="primary" size="large" @click="saveAISettings" :loading="saving">
            保存 AI 设置
          </el-button>
          <el-button size="large" @click="testAIConnection" :loading="testing">
            测试连接
          </el-button>
        </el-form-item>
      </el-form>

      <div class="ai-status">
        <div class="status-row">
          <span class="status-label">当前模式</span>
          <el-tag :type="aiMode === 'local' ? 'success' : 'primary'" size="small">
            {{ aiMode === 'local' ? '本地 Ollama' : '云端 AI' }}
          </el-tag>
        </div>
        <div class="status-row" v-if="aiMode === 'local'">
          <span class="status-label">服务地址</span>
          <code>{{ localEndpoint }}</code>
        </div>
        <div class="status-row" v-else>
          <span class="status-label">API 地址</span>
          <code>{{ cloudEndpoint || '未配置' }}</code>
        </div>
      </div>
    </div>

    <!-- 扫描参数设置 -->
    <div class="white-card">
      <div class="section-title">🔍 扫描参数设置</div>
      <el-form label-position="top" size="large">
        <el-form-item label="最大并发扫描数">
          <el-input-number v-model="maxConcurrent" :min="1" :max="50" size="large" />
          <div class="field-hint">同时进行的最大扫描任务数，建议不超过 20</div>
        </el-form-item>
        <el-form-item label="扫描超时时间（秒）">
          <el-input-number v-model="scanTimeout" :min="30" :max="600" :step="30" size="large" />
          <div class="field-hint">单次扫描任务的最大等待时间</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" @click="saveScanSettings" :loading="saving">
            保存扫描参数
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 账号信息 -->
    <div class="white-card">
      <div class="section-title">👤 账号信息</div>
      <div class="account-info">
        <div class="account-row">
          <span class="account-label">当前用户</span>
          <span class="account-value">{{ currentUser }}</span>
        </div>
        <div class="account-row">
          <span class="account-label">登录状态</span>
          <el-tag type="success" size="small">已登录</el-tag>
        </div>
      </div>
      <el-button type="danger" size="default" @click="handleLogout" plain style="margin-top:16px">
        退出登录
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const saving = ref(false)
const testing = ref(false)

// AI Settings
const aiMode = ref('local')
const localEndpoint = ref('http://localhost:11434')
const localModel = ref('qwen2.5:7b')
const cloudEndpoint = ref('')
const cloudApiKey = ref('')
const cloudModel = ref('')

// Scan Settings
const maxConcurrent = ref(10)
const scanTimeout = ref(300)

const currentUser = localStorage.getItem('libra_user') || 'admin'

onMounted(() => {
  // Load saved settings
  const saved = localStorage.getItem('libra_ai_settings')
  if (saved) {
    try {
      const s = JSON.parse(saved)
      aiMode.value = s.mode || 'local'
      localEndpoint.value = s.localEndpoint || 'http://localhost:11434'
      localModel.value = s.localModel || 'qwen2.5:7b'
      cloudEndpoint.value = s.cloudEndpoint || ''
      cloudApiKey.value = s.cloudApiKey || ''
      cloudModel.value = s.cloudModel || ''
    } catch {}
  }

  const scanSet = localStorage.getItem('libra_scan_settings')
  if (scanSet) {
    try {
      const s = JSON.parse(scanSet)
      maxConcurrent.value = s.maxConcurrent || 10
      scanTimeout.value = s.scanTimeout || 300
    } catch {}
  }
})

const onAiModeChange = () => {}

const saveAISettings = () => {
  saving.value = true
  try {
    const settings = {
      mode: aiMode.value,
      localEndpoint: localEndpoint.value,
      localModel: localModel.value,
      cloudEndpoint: cloudEndpoint.value,
      cloudApiKey: cloudApiKey.value,
      cloudModel: cloudModel.value,
    }
    localStorage.setItem('libra_ai_settings', JSON.stringify(settings))
    ElMessage.success('AI 设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const testAIConnection = async () => {
  testing.value = true
  try {
    // Test based on mode
    if (aiMode.value === 'local') {
      const res = await fetch(localEndpoint.value + '/api/tags')
      if (res.ok) {
        ElMessage.success('Ollama 连接成功')
      } else {
        ElMessage.error('Ollama 连接失败')
      }
    } else {
      ElMessage.info('云端 API 测试需要实际发送请求，建议先保存设置')
    }
  } catch {
    ElMessage.error('连接失败，请检查服务地址')
  } finally {
    testing.value = false
  }
}

const saveScanSettings = () => {
  saving.value = true
  try {
    const settings = {
      maxConcurrent: maxConcurrent.value,
      scanTimeout: scanTimeout.value,
    }
    localStorage.setItem('libra_scan_settings', JSON.stringify(settings))
    ElMessage.success('扫描参数已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('libra_token')
  localStorage.removeItem('libra_user')
  router.push('/login')
}
</script>

<style scoped>
.settings-page { color: #1a1a2e; max-width: 800px; }
.page-header { margin-bottom: 24px; }
.page-title { margin: 0; font-size: 22px; font-weight: 600; color: #1a1a2e; }
.white-card {
  background: #ffffff; border-radius: 16px; padding: 24px;
  border: 1px solid #e8eaed; box-shadow: 0 2px 12px rgba(0,0,0,0.04); margin-bottom: 20px;
}
.section-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 20px; }
.field-hint { font-size: 12px; color: #8a94a6; margin-top: 4px; }
.ai-status {
  margin-top: 20px;
  padding: 14px;
  background: #f8f9fb;
  border-radius: 10px;
  border: 1px solid #e8eaed;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.status-row:last-child { margin-bottom: 0; }
.status-label { font-size: 13px; color: #8a94a6; min-width: 70px; }
.status-row code { font-size: 12px; color: #4f8ef7; }
.account-info { display: flex; flex-direction: column; gap: 10px; }
.account-row { display: flex; align-items: center; gap: 12px; }
.account-label { font-size: 13px; color: #8a94a6; min-width: 70px; }
.account-value { font-size: 14px; font-weight: 600; color: #1a1a2e; }
</style>
