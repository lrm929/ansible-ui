<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">任务记录</span>
        <el-button :icon="Refresh" circle title="刷新" @click="load" />
      </div>
      <el-table v-loading="loading" :data="tasks" stripe @row-click="goDetail" row-class-name="task-row">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="template_name" label="任务模板" min-width="170" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="taskStatus(row.status).type">
              {{ taskStatus(row.status).text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="110" />
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="170">
          <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="110">
          <template #default="{ row }">{{ formatDuration(row.started_at, row.finished_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click.stop="goDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
        <template #empty>暂无任务记录</template>
      </el-table>
      <div class="pagination">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="onPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'
import { formatTime, formatDuration, taskStatus } from '../utils/format'

const router = useRouter()

const loading = ref(false)
const tasks = ref([])
const page = ref(1)
const pageSize = 50
const total = ref(0)

let timer = null

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/tasks', {
      params: { limit: pageSize, offset: (page.value - 1) * pageSize }
    })
    tasks.value = data
    // 接口返回数组,若返回数量达到 pageSize 说明可能还有下一页
    total.value = (page.value - 1) * pageSize + data.length + (data.length === pageSize ? 1 : 0)
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  load()
}

function goDetail(row) {
  router.push(`/tasks/${row.id}`)
}

// 有运行中/等待中的任务时每 3 秒轮询刷新
function setupPolling() {
  timer = setInterval(() => {
    const hasActive = tasks.value.some((t) => t.status === 'running' || t.status === 'pending')
    if (hasActive) load()
  }, 3000)
}

onMounted(() => {
  load()
  setupPolling()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

:deep(.task-row) {
  cursor: pointer;
}
</style>
