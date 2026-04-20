<template>
  <div class="schedule-page">
    <div class="page-header">
      <h2 class="page-title">⏰ 定时扫描任务</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;添加定时任务
      </el-button>
    </div>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="showAddDialog" :title="editJob ? '编辑定时任务' : '添加定时任务'" width="560px" destroy-on-close>
      <el-form :model="scheduleForm" label-position="top">
        <el-form-item label="任务名称" required>
          <el-input v-model="scheduleForm.name" placeholder="例如：每周站群巡检" />
        </el-form-item>
        <el-form-item label="目标 URL" required>
          <el-input v-model="scheduleForm.url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="扫描模式">
          <el-select v-model="scheduleForm.scan_type" style="width: 100%">
            <el-option value="HomePage_Scan" label="首页扫描" />
            <el-option value="SecondPage_Scan" label="二级页面扫描" />
            <el-option value="AllSite_Scan" label="全站扫描" />
            <el-option value="CustomPage_Scan" label="自定义页面扫描" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行周期">
          <el-select v-model="scheduleForm.cron_expr" style="width: 100%">
            <el-option value="hourly" label="⏰ 每小时执行一次" />
            <el-option value="daily" label="📅 每天凌晨 00:00 执行" />
            <el-option value="weekly" label="📆 每周一凌晨 00:00 执行" />
            <el-option value="0 */6 * * *" label="🔄 每 6 小时执行" />
            <el-option value="0 */12 * * *" label="🕛 每 12 小时执行" />
            <el-option value="0 2 * * *" label="🌙 每天凌晨 2:00 执行" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false; editJob = null">取消</el-button>
        <el-button type="primary" @click="handleSaveSchedule" :loading="saving">
          {{ editJob ? '保存修改' : '创建任务' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 定时任务列表 -->
    <div v-if="scheduledJobs.length" class="jobs-list">
      <div v-for="job in scheduledJobs" :key="job.id" class="job-card" :class="{ disabled: !job.enabled }">
        <div class="job-header">
          <div class="job-info">
            <div class="job-name">
              {{ job.name }}
              <el-tag size="small" :type="job.enabled ? 'success' : 'info'" style="margin-left: 8px">
                {{ job.enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </div>
            <div class="job-meta">
              <span>🔗 {{ job.url }}</span>
              <span>⏱ {{ cronLabel(job.cron_expr) }}</span>
              <span>📋 {{ scanTypeLabel(job.scan_type) }}</span>
            </div>
          </div>
          <div class="job-actions">
            <el-button text type="primary" size="small" @click="triggerNow(job.id)">立即执行</el-button>
            <el-button text size="small" @click="toggleEnabled(job)">
              {{ job.enabled ? '暂停' : '启用' }}
            </el-button>
            <el-button text size="small" @click="editSchedule(job)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(job.id)">删除</el-button>
          </div>
        </div>

        <!-- 最近一次执行结果 -->
        <div v-if="job.last_run" class="job-last-run">
          <div class="last-run-header">
            <span>最近执行: {{ formatTime(job.last_run) }}</span>
            <span v-if="job.last_result">
              🔗 {{ job.last_result.blacklink_count || 0 }} ·
              🚪 {{ job.last_result.backdoor_count || 0 }} ·
              ⚠️ {{ job.last_result.violativelink_count || 0 }} ·
              💔 {{ job.last_result.diedlink_count || 0 }}
            </span>
          </div>
          <div v-if="job.last_task_id && job.last_result" class="last-run-actions">
            <el-button text type="primary" size="small" @click="exportLastResult(job.last_task_id, 'pdf')">📄 PDF</el-button>
            <el-button text type="primary" size="small" @click="exportLastResult(job.last_task_id, 'csv')">📊 CSV</el-button>
          </div>
        </div>
        <div v-else class="job-last-run">
          <span style="color: #8a94a6">尚未执行过</span>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无定时任务，点击右上角添加" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createSchedule, listSchedules, updateSchedule, deleteSchedule, triggerScheduleNow, getReportUrl } from '../api/libra'

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
    ElMessage.error('获取定时任务失败')
  }
}

const handleSaveSchedule = async () => {
  if (!scheduleForm.value.name || !scheduleForm.value.url) {
    ElMessage.warning('请填写名称和 URL')
    return
  }
  saving.value = true
  try {
    if (editJob.value) {
      await updateSchedule(editJob.value.id, scheduleForm.value)
      ElMessage.success('修改已保存')
    } else {
      await createSchedule(scheduleForm.value)
      ElMessage.success('定时任务已创建')
    }
    showAddDialog.value = false
    editJob.value = null
    scheduleForm.value = { name: '', url: '', scan_type: 'HomePage_Scan', cron_expr: 'daily' }
    fetchJobs()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const toggleEnabled = async (job) => {
  try {
    await updateSchedule(job.id, { enabled: !job.enabled })
    ElMessage.success(job.enabled ? '已暂停' : '已启用')
    fetchJobs()
  } catch {
    ElMessage.error('操作失败')
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
  await ElMessageBox.confirm('确定删除这个定时任务？', '提示', { type: 'warning' })
  await deleteSchedule(jobId)
  ElMessage.success('已删除')
  fetchJobs()
}

const triggerNow = async (jobId) => {
  try {
    await triggerScheduleNow(jobId)
    ElMessage.success('已触发执行')
    setTimeout(fetchJobs, 3000)
  } catch {
    ElMessage.error('触发失败')
  }
}

const exportLastResult = (taskId, fmt) => {
  window.open(getReportUrl(taskId, fmt), '_blank')
}

const cronLabel = (expr) => ({
  hourly: '每小时',
  daily: '每天',
  weekly: '每周',
  '0 */6 * * *': '每6小时',
  '0 */12 * * *': '每12小时',
  '0 2 * * *': '每天凌晨2点',
}[expr] || expr)

const scanTypeLabel = (t) => ({
  HomePage_Scan: '首页扫描',
  SecondPage_Scan: '二级扫描',
  AllSite_Scan: '全站扫描',
  CustomPage_Scan: '自定义扫描',
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
