<template>
  <div class="page-container">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col v-for="card in statCards" :key="card.label" :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card-body">
            <el-icon :size="34" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务状态统计 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-card-body">
            <span class="status-label">成功任务</span>
            <span class="status-value" style="color: #67c23a">{{ data.status_stats?.success ?? 0 }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-card-body">
            <span class="status-label">失败任务</span>
            <span class="status-value" style="color: #f56c6c">{{ data.status_stats?.failed ?? 0 }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-card-body">
            <span class="status-label">运行中任务</span>
            <span class="status-value" style="color: #409eff">{{ data.status_stats?.running ?? 0 }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近任务 -->
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <span>最近任务</span>
          <el-button text type="primary" @click="$router.push('/tasks')">查看全部</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="data.recent_tasks || []" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="template_name" label="任务模板" min-width="160" show-overflow-tooltip />
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
            <el-button text type="primary" size="small" @click="$router.push(`/tasks/${row.id}`)">
              详情
            </el-button>
          </template>
        </el-table-column>
        <template #empty>暂无任务记录</template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  Monitor,
  Files,
  FolderOpened,
  Document,
  Tickets,
  Calendar
} from '@element-plus/icons-vue'
import api from '../api'
import { formatTime, formatDuration, taskStatus } from '../utils/format'

const loading = ref(false)
const data = ref({})

const statCards = computed(() => [
  { label: '主机数', value: data.value.hosts ?? 0, icon: Monitor, color: '#409eff' },
  { label: '清单', value: data.value.inventories ?? 0, icon: Files, color: '#67c23a' },
  { label: '项目', value: data.value.projects ?? 0, icon: FolderOpened, color: '#e6a23c' },
  { label: '任务模板', value: data.value.templates ?? 0, icon: Document, color: '#909399' },
  { label: '任务总数', value: data.value.tasks_total ?? 0, icon: Tickets, color: '#b88230' },
  { label: '今日任务', value: data.value.tasks_today ?? 0, icon: Calendar, color: '#f56c6c' }
])

async function load() {
  loading.value = true
  try {
    const res = await api.get('/dashboard')
    data.value = res.data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}

.stat-card :deep(.el-card__body) {
  padding: 18px;
}

.stat-card-body {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.status-card :deep(.el-card__body) {
  padding: 14px 18px;
}

.status-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-label {
  font-size: 14px;
  color: #606266;
}

.status-value {
  font-size: 24px;
  font-weight: 700;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
