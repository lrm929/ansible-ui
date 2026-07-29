<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">Playbook 管理</span>
        <div class="toolbar-right">
          <el-select
            v-model="currentProjectId"
            placeholder="请选择项目"
            class="project-select"
            @change="onProjectChange"
          >
            <el-option
              v-for="p in projects"
              :key="p.id"
              :label="p.source_type === 'git' ? `${p.name} (Git 只读)` : p.name"
              :value="p.id"
            />
          </el-select>
          <el-button
            v-if="!isViewer"
            type="primary"
            :icon="Plus"
            :disabled="!canWrite"
            @click="openEditor()"
          >
            新建 Playbook
          </el-button>
        </div>
      </div>
      <el-table v-loading="loading" :data="playbooks" stripe>
        <el-table-column prop="path" label="文件路径" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="path-code">{{ row.path }}</code>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canWrite && !isViewer" text type="primary" size="small" @click="openEditor(row)">编辑</el-button>
            <el-button v-else text type="primary" size="small" @click="openViewer(row)">查看</el-button>
            <el-button v-if="canWrite && !isViewer" text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>{{ currentProjectId ? '该项目下暂无 playbook' : '请先选择项目' }}</template>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="editorVisible" :title="editorForm.isNew ? '新建 Playbook' : `编辑 - ${editorForm.path}`" width="720px" :close-on-click-modal="false">
      <el-form ref="editorFormRef" :model="editorForm" :rules="editorRules" label-width="90px">
        <el-form-item v-if="editorForm.isNew" label="文件名" prop="path">
          <el-input v-model="editorForm.path" placeholder="如 deploy.yml 或 roles/web/main.yml(自动补 .yml)" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="editorForm.content"
            type="textarea"
            :rows="20"
            class="code-input"
            :placeholder="playbookPlaceholder"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 只读查看对话框(git 项目) -->
    <el-dialog v-model="viewerVisible" :title="`查看 - ${viewerPath}`" width="720px">
      <el-input v-model="viewerContent" type="textarea" :rows="20" class="code-input" readonly />
      <template #footer>
        <el-button @click="viewerVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isViewer = computed(() => authStore.user?.role === 'viewer')

const projects = ref([])
const playbooks = ref([])
const currentProjectId = ref(null)
const loading = ref(false)

const currentProject = computed(() => projects.value.find((p) => p.id === currentProjectId.value) || null)
const canWrite = computed(() => currentProject.value?.source_type === 'local')

const editorVisible = ref(false)
const saving = ref(false)
const editorFormRef = ref(null)
const editorForm = reactive({ isNew: true, path: '', content: '' })
const editorRules = {
  path: [{ required: true, message: '请输入文件名', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

const viewerVisible = ref(false)
const viewerPath = ref('')
const viewerContent = ref('')

const playbookPlaceholder = `- hosts: all
  gather_facts: yes
  tasks:
    - name: 示例任务
      debug:
        msg: "Hello Ansible"
`

async function loadProjects() {
  try {
    const { data } = await api.get('/projects')
    projects.value = data
    if (!currentProjectId.value && data.length > 0) {
      currentProjectId.value = data[0].id
      await loadPlaybooks()
    }
  } catch {
    // 错误提示由拦截器统一处理
  }
}

async function loadPlaybooks() {
  if (!currentProjectId.value) return
  loading.value = true
  try {
    const { data } = await api.get(`/projects/${currentProjectId.value}/playbooks`)
    playbooks.value = data.playbooks.map((p) => ({ path: p }))
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function onProjectChange() {
  playbooks.value = []
  loadPlaybooks()
}

function normalizePath(path) {
  let p = (path || '').trim().replace(/^\/+/, '')
  if (p && !p.endsWith('.yml') && !p.endsWith('.yaml')) p += '.yml'
  return p
}

async function openEditor(row) {
  if (row) {
    // 编辑:先读出原内容
    try {
      const { data } = await api.get(`/projects/${currentProjectId.value}/playbooks/${row.path}`)
      Object.assign(editorForm, { isNew: false, path: data.path, content: data.content })
    } catch {
      return // 错误提示由拦截器统一处理(如文件不存在)
    }
  } else {
    Object.assign(editorForm, { isNew: true, path: '', content: '' })
  }
  editorVisible.value = true
}

async function openViewer(row) {
  try {
    const { data } = await api.get(`/projects/${currentProjectId.value}/playbooks/${row.path}`)
    viewerPath.value = data.path
    viewerContent.value = data.content
    viewerVisible.value = true
  } catch {
    // 错误提示由拦截器统一处理
  }
}

async function save() {
  await editorFormRef.value.validate()
  saving.value = true
  try {
    if (editorForm.isNew) {
      const path = normalizePath(editorForm.path)
      await api.post(`/projects/${currentProjectId.value}/playbooks`, {
        path,
        content: editorForm.content
      })
      ElMessage.success('Playbook 已创建')
    } else {
      await api.put(`/projects/${currentProjectId.value}/playbooks/${editorForm.path}`, {
        path: editorForm.path,
        content: editorForm.content
      })
      ElMessage.success('Playbook 已保存')
    }
    editorVisible.value = false
    await loadPlaybooks()
  } catch {
    // 错误提示由拦截器统一处理(如文件已存在 409)
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定要删除「${row.path}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/projects/${currentProjectId.value}/playbooks/${row.path}`)
    ElMessage.success('已删除')
    await loadPlaybooks()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

onMounted(loadProjects)
</script>

<style scoped>
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-select {
  width: 260px;
}

.path-code {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
}

.code-input :deep(textarea) {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
