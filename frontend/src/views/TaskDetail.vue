<template>
  <div class="page-container">
    <!-- 任务信息 -->
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">任务详情 #{{ task?.id ?? id }}</span>
        <div>
          <el-button :icon="Refresh" circle title="刷新" @click="loadTask" />
          <el-button
            v-if="isRunning && !isViewer"
            type="danger"
            :loading="stopping"
            @click="stopTask"
          >
            停止
          </el-button>
        </div>
      </div>
      <el-descriptions v-if="task" :column="3" border>
        <el-descriptions-item label="任务模板">{{ task.template_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="taskStatus(task.status).type">{{ taskStatus(task.status).text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建人">{{ task.created_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatTime(task.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ formatTime(task.finished_at) }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ formatDuration(task.started_at, task.finished_at) }}</el-descriptions-item>
        <el-descriptions-item label="执行命令" :span="3">
          <code class="command">{{ task.command || '-' }}</code>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 日志区 -->
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">执行日志</span>
        <span class="ws-status">{{ wsStatusText }}</span>
      </div>
      <pre ref="logRef" class="log-viewer">{{ output || '暂无日志' }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'
import { formatTime, formatDuration, taskStatus, stripAnsi } from '../utils/format'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isViewer = computed(() => authStore.user?.role === 'viewer')

const route = useRoute()
const id = route.params.id

const task = ref(null)
const output = ref('')
const stopping = ref(false)
const logRef = ref(null)
const wsConnected = ref(false)

let ws = null

const isRunning = computed(() => task.value && (task.value.status === 'running' || task.value.status === 'pending'))

const wsStatusText = computed(() => {
  if (isRunning.value) return wsConnected.value ? '实时输出中' : '正在连接实时日志...'
  return '任务已结束'
})

async function loadTask() {
  try {
    const { data } = await api.get(`/tasks/${id}`)
    task.value = data
    if (data.status === 'running' || data.status === 'pending') {
      connectWs()
    } else {
      closeWs()
      await loadOutput()
    }
  } catch {
    // 错误提示由拦截器统一处理
  }
}

// 已结束任务:全量拉取日志
async function loadOutput() {
  try {
    const { data } = await api.get(`/tasks/${id}/output`)
    output.value = stripAnsi(data.output || '')
    scrollToBottom()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

// 运行中任务:WebSocket 实时推送
function connectWs() {
  if (ws) return
  const token = localStorage.getItem('token') || ''
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const url = `${protocol}://${location.host}/api/ws/tasks/${id}?token=${encodeURIComponent(token)}`
  ws = new WebSocket(url)

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    let msg
    try {
      msg = JSON.parse(event.data)
    } catch {
      return
    }
    if (msg.type === 'log') {
      output.value += stripAnsi(msg.line) + '\n'
      scrollToBottom()
    } else if (msg.type === 'status') {
      if (task.value) task.value.status = msg.status
    } else if (msg.type === 'end') {
      closeWs()
      loadTask()
    }
  }

  ws.onclose = () => {
    ws = null
    wsConnected.value = false
  }

  ws.onerror = () => {
    // 连接失败时退化为轮询输出
    closeWs()
  }
}

function closeWs() {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

function scrollToBottom() {
  nextTick(() => {
    if (logRef.value) {
      logRef.value.scrollTop = logRef.value.scrollHeight
    }
  })
}

async function stopTask() {
  try {
    await ElMessageBox.confirm('确定要停止该任务吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  stopping.value = true
  try {
    const { data } = await api.post(`/tasks/${id}/stop`)
    task.value = data
    ElMessage.success('已发送停止指令')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    stopping.value = false
  }
}

onMounted(loadTask)

onUnmounted(closeWs)
</script>

<style scoped>
.command {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  color: #606266;
  word-break: break-all;
}

.ws-status {
  font-size: 13px;
  color: #909399;
}
</style>
