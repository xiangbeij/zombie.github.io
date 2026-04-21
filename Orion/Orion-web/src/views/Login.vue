<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#4f8ef7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <h1>ORION</h1>
        <p class="login-sub">缃戠珯瀹夊叏宸℃绯荤粺</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="鐢ㄦ埛鍚?
            size="large"
            :prefix-icon="User"
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="瀵嗙爜"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="handleLogin">
            {{ loading ? '鐧诲綍涓?..' : '鐧?褰? }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-hint">
        <p>婕旂ず璐﹀彿: <code>admin</code> / <code>Qau_2026@%1</code></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '璇疯緭鍏ョ敤鎴峰悕', trigger: 'blur' }],
  password: [{ required: true, message: '璇疯緭鍏ュ瘑鐮?, trigger: 'blur' }],
}

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('璇疯緭鍏ョ敤鎴峰悕鍜屽瘑鐮?)
    return
  }
  loading.value = true
  try {
    let token = ''
    try {
      const res = await fetch('http://localhost:5188/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: form.username, password: form.password }),
      })
      const data = await res.json()
      token = data.token
    } catch {
      // Fallback: hardcoded check
      if (form.username === 'admin' && form.password === 'Qau_2026@%1') {
        token = 'Orion-token-' + btoa(form.username + ':' + Date.now())
      } else {
        throw new Error('invalid')
      }
    }
    localStorage.setItem('orion_token', token)
    localStorage.setItem('orion_user', form.username)
    ElMessage.success('鐧诲綍鎴愬姛')
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error('鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 48px 40px;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: #eef2ff;
  margin-bottom: 12px;
}

.login-header h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  background: linear-gradient(135deg, #4f8ef7, #6c5ce7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.login-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #8a94a6;
}

.login-hint {
  margin-top: 16px;
  padding: 10px;
  background: #f8f9fb;
  border-radius: 8px;
  text-align: center;
}

.login-hint p {
  margin: 0;
  font-size: 12px;
  color: #8a94a6;
}

.login-hint code {
  color: #4f8ef7;
  background: #eef2ff;
  padding: 1px 6px;
  border-radius: 4px;
}
</style>
