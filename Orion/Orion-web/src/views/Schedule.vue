<template>
  <div class="schedule-page">
    <div class="page-header">
      <h2 class="page-title">鈴?瀹氭椂鎵弿浠诲姟</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;娣诲姞瀹氭椂浠诲姟
      </el-button>
    </div>

    <!-- 娣诲姞/缂栬緫寮圭獥 -->
    <el-dialog v-model="showAddDialog" :title="editJob ? '缂栬緫瀹氭椂浠诲姟' : '娣诲姞瀹氭椂浠诲姟'" width="560px" destroy-on-close>
      <el-form :model="scheduleForm" label-position="top">
        <el-form-item label="浠诲姟鍚嶇О" required>
          <el-input v-model="scheduleForm.name" placeholder="渚嬪锛氭瘡鍛ㄧ珯缇ゅ贰妫€" />
        </el-form-item>
        <el-form-item label="鐩爣 URL" required>
          <el-input v-model="scheduleForm.url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="鎵弿妯″紡">
          <el-select v-model="scheduleForm.scan_type" style="width: 100%">
            <el-option value="HomePage_Scan" label="棣栭〉鎵弿" />
            <el-option value="SecondPage_Scan" label="浜岀骇椤甸潰鎵弿" />
            <el-option value="AllSite_Scan" label="鍏ㄧ珯鎵弿" />
            <el-option value="CustomPage_Scan" label="鑷畾涔夐〉闈㈡壂鎻? />
          </el-select>
        </el-form-item>
        <el-form-item label="鎵ц鍛ㄦ湡">
          <el-select v-model="scheduleForm.cron_expr" style="width: 100%">
            <el-option value="hourly" label="鈴?姣忓皬鏃舵墽琛屼竴娆? />
            <el-option value="daily" label="馃搮 姣忓ぉ鍑屾櫒 00:00 鎵ц" />
            <el-option value="weekly" label="馃搯 姣忓懆涓€鍑屾櫒 00:00 鎵ц" />
            <el-option value="0 */6 * * *" label="馃攧 姣?6 灏忔椂鎵ц" />
            <el-option value="0 */12 * * *" label="馃暃 姣?12 灏忔椂鎵ц" />
            <el-option value="0 2 * * *" label="馃寵 姣忓ぉ鍑屾櫒 2:00 鎵ц" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false; editJob = null">鍙栨秷</el-button>
        <el-button type="primary" @click="handleSaveSchedule" :loading="saving">
          {{ editJob ? '淇濆瓨淇敼' : '鍒涘缓浠诲姟' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 瀹氭椂浠诲姟鍒楄〃 -->
    <div v-if="scheduledJobs.length" class="jobs-list">
      <div v-for="job in scheduledJobs" :key="job.id" class="job-card" :class="{ disabled: !job.enabled }">
        <div class="job-header">
          <div class="job-info">
            <div class="job-name">
              {{ job.name }}
              <el-tag size="small" :type="job.enabled ? 'success' : 'info'" style="margin-left: 8px">
                {{ job.enabled ? '宸插惎鐢? : '宸茬鐢? }}
              </el-tag>
            </div>
            <div class="job-meta">
              <span>馃敆 {{ job.url }}</span>
              <span>鈴?{{ cronLabel(job.cron_expr) }}</span>
              <span>馃搵 {{ scanTypeLabel(job.scan_type) }}</span>
            </div>
          </div>
          <div class="job-actions">
            <el-button text type="primary" size="small" @click="triggerNow(job.id)">绔嬪嵆鎵ц</el-button>
            <el-button text size="small" @click="toggleEnabled(job)">
              {{ job.enabled ? '鏆傚仠' : '鍚敤' }}
            </el-button>
            <el-button text size="small" @click="editSchedule(job)">缂栬緫</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(job.id)">鍒犻櫎</el-button>
          </div>
        </div>

        <!-- 鏈€杩戜竴娆℃墽琛岀粨鏋?-->
        <div v-if="job.last_run" class="job-last-run">
          <div class="last-run-header">
            <span>鏈€杩戞墽琛? {{ formatTime(job.last_run) }}</span>
            <span v-if="job.last_result">
              馃敆 {{ job.last_result.blacklink_count || 0 }} 路
              馃毆 {{ job.last_result.backdoor_count || 0 }} 路
              鈿狅笍 {{ job.last_result.violativelink_count || 0 }} 路
              馃挃 {{ job.last_result.diedlink_count || 0 }}
            </span>
          </div>
          <div v-if="job.last_task_id && job.last_result" class="last-run-actions">
            <el-button text type="primary" size="small" @click="exportLastResult(job.last_task_id, 'pdf')">馃搫 PDF</el-button>
            <el-button text type="primary" size="small" @click="exportLastResult(job.last_task_id, 'csv')">馃搳 CSV</el-button>
          </div>
        </div>
        <div v-else class="job-last-run">
          <span style="color: #8a94a6">灏氭湭鎵ц杩?/span>
        </div>
      </div>
    </div>

    <el-empty v-else description="鏆傛棤瀹氭椂浠诲姟锛岀偣鍑诲彸涓婅娣诲姞" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createSchedule, listSchedules, updateSchedule, deleteSchedule, triggerScheduleNow, getReportUrl } from '../api/Orion'

const scheduledJobs = ref([])
const showAddDialog = ref(false)
const editJob = ref(null)
const saving = ref(false)

const scheduleForm = ref({
  name: '',
  url: '',
  scan_type: 'HomePage_Scan',
  cron_expr: 'daily',
})

const fetchJobs = async () => {
  try {
    const res = await listSchedules()
    scheduledJobs.value = res.data.jobs || []
  } catch (e) {
    ElMessage.error('鑾峰彇瀹氭椂浠诲姟澶辫触')
  }
}

const handleSaveSchedule = async () => {
  if (!scheduleForm.value.name || !scheduleForm.value.url) {
    ElMessage.warning('璇峰～鍐欏悕绉板拰 URL')
    return
  }
  saving.value = true
  try {
    if (editJob.value) {
      await updateSchedule(editJob.value.id, scheduleForm.value)
      ElMessage.success('淇敼宸蹭繚瀛?)
    } else {
      await createSchedule(scheduleForm.value)
      ElMessage.success('瀹氭椂浠诲姟宸插垱寤?)
    }
    showAddDialog.value = false
    editJob.value = null
    scheduleForm.value = { name: '', url: '', scan_type: 'HomePage_Scan', cron_expr: 'daily' }
    fetchJobs()
  } catch (e) {
    ElMessage.error('淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

const toggleEnabled = async (job) => {
  try {
    await updateSchedule(job.id, { enabled: !job.enabled })
    ElMessage.success(job.enabled ? '宸叉殏鍋? : '宸插惎鐢?)
    fetchJobs()
  } catch {
    ElMessage.error('鎿嶄綔澶辫触')
  }
}

const editSchedule = (job) => {
  editJob.value = job
  scheduleForm.value = {
    name: job.name,
    url: job.url,
    scan_type: job.scan_type,
    cron_expr: job.cron_expr,
  }
  showAddDialog.value = true
}

const handleDelete = async (jobId) => {
  await ElMessageBox.confirm('纭畾鍒犻櫎杩欎釜瀹氭椂浠诲姟锛?, '鎻愮ず', { type: 'warning' })
  await deleteSchedule(jobId)
  ElMessage.success('宸插垹闄?)
  fetchJobs()
}

const triggerNow = async (jobId) => {
  try {
    await triggerScheduleNow(jobId)
    ElMessage.success('宸茶Е鍙戞墽琛?)
    setTimeout(fetchJobs, 3000)
  } catch {
    ElMessage.error('瑙﹀彂澶辫触')
  }
}

const exportLastResult = (taskId, fmt) => {
  window.open(getReportUrl(taskId, fmt), '_blank')
}

const cronLabel = (expr) => ({
  hourly: '姣忓皬鏃?,
  daily: '姣忓ぉ',
  weekly: '姣忓懆',
  '0 */6 * * *': '姣?灏忔椂',
  '0 */12 * * *': '姣?2灏忔椂',
  '0 2 * * *': '姣忓ぉ鍑屾櫒2鐐?,
}[expr] || expr)

const scanTypeLabel = (t) => ({
  HomePage_Scan: '棣栭〉鎵弿',
  SecondPage_Scan: '浜岀骇鎵弿',
  AllSite_Scan: '鍏ㄧ珯鎵弿',
  CustomPage_Scan: '鑷畾涔夋壂鎻?,
}[t] || t)

const formatTime = (iso) => iso ? new Date(iso).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '-'

onMounted(fetchJobs)
</script>

<style scoped>
.schedule-page { color: #1a1a2e; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 22px; font-weight: 600; color: #1a1a2e; }
.jobs-list { display: flex; flex-direction: column; gap: 16px; }
.job-card {
  background: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #e8eaed;
  transition: border-color 0.3s;
}
.job-card:hover { border-color: #4f8ef7; }
.job-card.disabled { opacity: 0.6; }
.job-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.job-name { font-size: 16px; font-weight: 600; color: #1a1a2e; margin-bottom: 8px; display: flex; align-items: center; }
.job-meta { display: flex; gap: 16px; font-size: 12px; color: #8a94a6; flex-wrap: wrap; }
.job-actions { display: flex; gap: 4px; flex-shrink: 0; }
.job-last-run {
  margin-top: 12px; padding-top: 12px; border-top: 1px solid #e8eaed;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
}
.last-run-header { font-size: 12px; color: #8a94a6; display: flex; gap: 12px; flex-wrap: wrap; }
.last-run-header span { display: flex; gap: 4px; }
.last-run-actions { display: flex; gap: 4px; }
</style>
