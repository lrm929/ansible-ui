<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">项目</span>
        <el-button v-if="!isViewer" type="primary" :icon="Plus" @click="openDialog()">新增项目</el-button>
      </div>
      <el-table v-loading="loading" :data="projects" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="来源类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.source_type === 'git' ? 'warning' : 'primary'">
              {{ row.source_type === 'git' ? 'Git' : '本地' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="路径 / 仓库地址" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.source_type === 'git'">{{ row.git_url }} ({{ row.git_branch || 'main' }})</span>
            <span v-else>{{ row.local_path }}</span>
          </template>
        </el-table-column>
        <el-table-column label="同步状态" width="100">
          <template #default="{ row }">
            <el-tooltip :content="row.sync_message" :disabled="!row.sync_message" placement="top">
              <el-tag :type="syncStatus(row.sync_status).type">
                {{ syncStatus(row.sync_status).text }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="最近同步" width="170">
          <template #default="{ row }">{{ formatTime(row.last_sync_at) }}</template>
        </el-table-column>
        <el-table-column v-if="!isViewer" label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="success"
              size="small"
              :loading="syncingId === row.id"
              @click="sync(row)"
            >
              同步
            </el-button>
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无项目</template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑项目' : '新增项目'" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如:运维playbook库" />
        </el-form-item>
        <el-form-item label="来源类型" prop="source_type">
          <el-radio-group v-model="form.source_type">
            <el-radio value="local">本地目录</el-radio>
            <el-radio value="git">Git 仓库</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.source_type === 'local'" label="本地路径" prop="local_path">
          <el-input v-model="form.local_path" placeholder="如 /opt/playbooks" />
        </el-form-item>
        <template v-else>
          <el-form-item label="仓库地址" prop="git_url">
            <el-input v-model="form.git_url" placeholder="https://github.com/xxx/playbooks.git" />
          </el-form-item>
          <el-form-item label="分支">
            <el-input v-model="form.git_branch" placeholder="默认 main" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'
import { formatTime, syncStatus } from '../utils/format'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isViewer = computed(() => authStore.user?.role === 'viewer')

const loading = ref(false)
const projects = ref([])
const syncingId = ref(null)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, name: '', source_type: 'local', local_path: '', git_url: '', git_branch: 'main' })

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择来源类型', trigger: 'change' }],
  local_path: [{ required: true, message: '请输入本地路径', trigger: 'blur' }],
  git_url: [{ required: true, message: '请输入仓库地址', trigger: 'blur' }]
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/projects')
    projects.value = data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  if (row) {
    Object.assign(form, {
      id: row.id,
      name: row.name,
      source_type: row.source_type,
      local_path: row.local_path || '',
      git_url: row.git_url || '',
      git_branch: row.git_branch || 'main'
    })
  } else {
    Object.assign(form, { id: null, name: '', source_type: 'local', local_path: '', git_url: '', git_branch: 'main' })
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { name: form.name, source_type: form.source_type }
    if (form.source_type === 'local') {
      payload.local_path = form.local_path
    } else {
      payload.git_url = form.git_url
      payload.git_branch = form.git_branch || 'main'
    }

    if (form.id) {
      await api.put(`/projects/${form.id}`, payload)
      ElMessage.success('项目已更新')
    } else {
      await api.post('/projects', payload)
      ElMessage.success('项目已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function sync(row) {
  syncingId.value = row.id
  try {
    await api.post(`/projects/${row.id}/sync`)
    ElMessage.success(`项目「${row.name}」同步完成`)
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    syncingId.value = null
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定要删除项目「${row.name}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/projects/${row.id}`)
    ElMessage.success('项目已删除')
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

onMounted(load)
</script>
