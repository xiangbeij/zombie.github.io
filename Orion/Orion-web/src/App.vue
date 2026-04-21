<template>
  <div class="app-layout">
    <!-- 鐧诲綍椤典笉浣跨敤渚ц竟鏍?-->
    <template v-if="$route.path !== '/login'">
      <!-- 椤堕儴瀵艰埅 -->
      <header class="topbar">
        <div class="topbar-brand">
          <span class="brand-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4f8ef7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </span>
          <span class="brand-name">ORION</span>
          <span class="brand-sub">缃戠珯瀹夊叏宸℃绯荤粺</span>
        </div>
        <div class="topbar-right">
          <div class="api-indicator">
            <span :class="['dot', apiOnline ? 'online' : 'offline']"></span>
            <span class="api-text">{{ apiOnline ? '绯荤粺姝ｅ父' : 'API 绂荤嚎' }}</span>
          </div>
          <el-button type="primary" size="default" @click="$router.push('/scan')" round>
            馃攳 鎵弿浠诲姟
          </el-button>
        </div>
      </header>

      <div class="app-body">
        <!-- 宸︿晶鑿滃崟 -->
        <nav class="sidebar">
          <el-menu :default-active="$route.path" router class="sidebar-menu" :collapse="false">
            <el-menu-item index="/dashboard">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              </span>
              <template #title>鐩戞帶闈㈡澘</template>
            </el-menu-item>
            <el-menu-item index="/scan">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              </span>
              <template #title>鍙戣捣鎵弿</template>
            </el-menu-item>

            <el-menu-item index="/schedule">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              </span>
              <template #title>瀹氭椂浠诲姟</template>
            </el-menu-item>
            <el-menu-item index="/history">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              </span>
              <template #title>鎵弿鍘嗗彶</template>
            </el-menu-item>
            <el-menu-item index="/assets">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg>
              </span>
              <template #title>璧勪骇鍙戠幇</template>
            </el-menu-item>
            <el-menu-item index="/monitor">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              </span>
              <template #title>缃戠珯鐩戞帶</template>
            </el-menu-item>
            <el-menu-item index="/rules">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14"/></svg>
              </span>
              <template #title>瑙勫垯绠＄悊</template>
            </el-menu-item>
            <el-menu-item index="/sites">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>
              </span>
              <template #title>璧勪骇绠＄悊</template>
            </el-menu-item>
            <el-menu-item index="/notifications">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
              </span>
              <template #title>閫氱煡璁剧疆</template>
            </el-menu-item>
            <el-menu-item index="/settings">
              <span class="nav-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
              </span>
              <template #title>绯荤粺璁剧疆</template>
            </el-menu-item>
          </el-menu>
        </nav>

        <!-- 涓诲唴瀹?-->
        <main class="main-content">
          <router-view />
        </main>
      </div>
    </template>

    <!-- 鐧诲綍椤靛叏灞忔樉绀?-->
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { healthCheck } from './api/Orion'

const apiOnline = ref(false)
const checkApi = async () => {
  try {
    const res = await healthCheck()
    apiOnline.value = res.data.status === 'ok'
  } catch { apiOnline.value = false }
}
onMounted(() => { checkApi(); setInterval(checkApi, 30000) })
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f0f2f5;
}

/* 鈹€鈹€ 椤堕儴瀵艰埅 鈹€鈹€ */
.topbar {
  height: 60px;
  background: #ffffff;
  border-bottom: 1px solid #e8eaed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon { display: flex; align-items: center; }
.nav-icon { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; }

.brand-name {
  font-size: 20px;
  font-weight: 800;
  background: linear-gradient(135deg, #4f8ef7, #6c5ce7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-sub {
  font-size: 12px;
  color: #3c4a5c;  /* 娣辫壊锛屼笉鍐嶆槸娴呯伆 */
  padding-left: 10px;
  border-left: 1px solid #e0e4ec;
  font-weight: 500;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.api-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #3c4a5c;  /* 娣辫壊 */
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot.online { background: #00c853; box-shadow: 0 0 6px #00c853; }
.dot.offline { background: #ff1744; }

/* 鈹€鈹€ 涓讳綋 鈹€鈹€ */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 鈹€鈹€ 渚ц竟鏍?鈹€鈹€ */
.sidebar {
  width: 200px;
  background: #ffffff;
  border-right: 1px solid #e8eaed;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-menu {
  border: none;
  padding: 12px 0;
}

.sidebar-menu:not(.el-menu--collapse) { width: 200px; }

.sidebar-menu .el-menu-item {
  height: 46px;
  line-height: 46px;
  font-size: 14px;
  color: #3c4a5c;  /* 娣辫壊鏂囧瓧锛屼笉鍐嶆槸娴呯伆 */
  margin: 2px 8px;
  border-radius: 10px;
  transition: all 0.2s;
}

.sidebar-menu .el-menu-item:hover {
  background: #f0f4ff !important;
  color: #4f8ef7;
}

.sidebar-menu .el-menu-item.is-active {
  background: #f0f4ff !important;
  color: #4f8ef7 !important;
  font-weight: 600;
}

/* 鈹€鈹€ 涓诲唴瀹?鈹€鈹€ */
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
