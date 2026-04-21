<template>
  <div class="settings-page">
    <div class="page-header">
      <h2 class="page-title">鈿欙笍 绯荤粺璁剧疆</h2>
    </div>

    <!-- AI 鍒嗘瀽璁剧疆 -->
    <div class="white-card">
      <div class="section-title">馃 AI 鍒嗘瀽璁剧疆</div>

      <el-form label-position="top" size="large">
        <el-form-item label="AI 妯″紡">
          <el-radio-group v-model="aiMode" @change="onAiModeChange">
            <el-radio-button value="local">鏈湴 Ollama</el-radio-button>
            <el-radio-button value="cloud">浜戠 AI</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="aiMode === 'local'">
          <el-form-item label="Ollama 鏈嶅姟鍦板潃">
            <el-input v-model="localEndpoint" placeholder="http://localhost:11434" size="large" />
            <div class="field-hint">鏈湴閮ㄧ讲鐨?Ollama 鏈嶅姟鍦板潃锛岄粯璁?http://localhost:11434</div>
          </el-form-item>
          <el-form-item label="妯″瀷鍚嶇О">
            <el-input v-model="localModel" placeholder="qwen2.5:7b" size="large" />
            <div class="field-hint">鍦?Ollama 涓繍琛岀殑妯″瀷鍚嶇О</div>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="API 鎺ュ彛鍦板潃">
            <el-input v-model="cloudEndpoint" placeholder="https://api.example.com/v1/chat/completions" size="large" />
            <div class="field-hint">浜戠澶фā鍨?API 鍦板潃锛堝 OpenAI銆丆laude 绛夛級</div>
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="cloudApiKey" type="password" placeholder="sk-..." size="large" show-password />
            <div class="field-hint">浜戠 AI 鏈嶅姟鐨?API Key锛堝皢瀹夊叏瀛樺偍锛?/div>
          </el-form-item>
          <el-form-item label="妯″瀷鍚嶇О">
            <el-input v-model="cloudModel" placeholder="gpt-4o-mini" size="large" />
            <div class="field-hint">浜戠妯″瀷鍚嶇О锛屽 gpt-4o-mini銆乧laude-3-haiku 绛?/div>
          </el-form-item>
        </template>

        <el-form-item>
          <el-button type="primary" size="large" @click="saveAISettings" :loading="saving">
            淇濆瓨 AI 璁剧疆
          </el-button>
          <el-button size="large" @click="testAIConnection" :loading="testing">
            娴嬭瘯杩炴帴
          </el-button>
        </el-form-item>
      </el-form>

      <div class="ai-status">
        <div class="status-row">
          <span class="status-label">褰撳墠妯″紡</span>
          <el-tag :type="aiMode === 'local' ? 'success' : 'primary'" size="small">
            {{ aiMode === 'local' ? '鏈湴 Ollama' : '浜戠 AI' }}
          </el-tag>
        </div>
        <div class="status-row" v-if="aiMode === 'local'">
          <span class="status-label">鏈嶅姟鍦板潃</span>
          <code>{{ localEndpoint }}</code>
        </div>
        <div class="status-row" v-else>
          <span class="status-label">API 鍦板潃</span>
          <code>{{ cloudEndpoint || '鏈厤缃? }}</code>
        </div>
      </div>
    </div>

    <!-- 鎵弿鍙傛暟璁剧疆 -->
    <div class="white-card">
      <div class="section-title">馃攳 鎵弿鍙傛暟璁剧疆</div>
      <el-form label-position="top" size="large">
        <el-form-item label="鏈€澶у苟鍙戞壂鎻忔暟">
          <el-input-number v-model="maxConcurrent" :min="1" :max="50" size="large" />
          <div class="field-hint">鍚屾椂杩涜鐨勬渶澶ф壂鎻忎换鍔℃暟锛屽缓璁笉瓒呰繃 20</div>
        </el-form-item>
        <el-form-item label="鎵弿瓒呮椂鏃堕棿锛堢锛?>
          <el-input-number v-model="scanTimeout" :min="30" :max="600" :step="30" size="large" />
          <div class="field-hint">鍗曟鎵弿浠诲姟鐨勬渶澶х瓑寰呮椂闂?/div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" @click="saveScanSettings" :loading="saving">
            淇濆瓨鎵弿鍙傛暟
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 璐﹀彿淇℃伅 -->
    <div class="white-card">
      <div class="section-title">馃懁 璐﹀彿淇℃伅</div>
      <div class="account-info">
        <div class="account-row">
          <span class="account-label">褰撳墠鐢ㄦ埛</span>
          <span class="account-value">{{ currentUser }}</span>
        </div>
        <div class="account-row">
          <span class="account-label">鐧诲綍鐘舵€?/span>
          <el-tag type="success" size="small">宸茬櫥褰?/el-tag>
        </div>
      </div>
      <el-button type="danger" size="default" @click="handleLogout" plain style="margin-top:16px">
        閫€鍑虹櫥褰?      </el-button>
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

const currentUser = localStorage.getItem('orion_user') || 'admin'

onMounted(() => {
  // Load saved settings
  const saved = localStorage.getItem('orion_ai_settings')
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

  const scanSet = localStorage.getItem('orion_scan_settings')
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
    localStorage.setItem('orion_ai_settings', JSON.stringify(settings))
    ElMessage.success('AI 璁剧疆宸蹭繚瀛?)
  } catch {
    ElMessage.error('淇濆瓨澶辫触')
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
        ElMessage.success('Ollama 杩炴帴鎴愬姛')
      } else {
        ElMessage.error('Ollama 杩炴帴澶辫触')
      }
    } else {
      ElMessage.info('浜戠 API 娴嬭瘯闇€瑕佸疄闄呭彂閫佽姹傦紝寤鸿鍏堜繚瀛樿缃?)
    }
  } catch {
    ElMessage.error('杩炴帴澶辫触锛岃妫€鏌ユ湇鍔″湴鍧€')
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
    localStorage.setItem('orion_scan_settings', JSON.stringify(settings))
    ElMessage.success('鎵弿鍙傛暟宸蹭繚瀛?)
  } catch {
    ElMessage.error('淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('orion_token')
  localStorage.removeItem('orion_user')
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
