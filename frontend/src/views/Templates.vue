<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">任务模板</span>
        <el-button v-if="!isViewer" type="primary" :icon="Plus" @click="openDialog()">新增模板</el-button>
      </div>
      <el-table v-loading="loading" :data="templates" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="project_name" label="项目" width="130" show-overflow-tooltip />
        <el-table-column prop="playbook" label="Playbook" min-width="150" show-overflow-tooltip />
        <el-table-column prop="inventory_name" label="清单" width="110" show-overflow-tooltip />
        <el-table-column prop="credential_name" label="凭据" width="130" show-overflow-tooltip />
        <el-table-column v-if="!isViewer" label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button text type="success" size="small" :loading="runningId === row.id" @click="run(row)">
              运行
            </el-button>
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无任务模板</template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑模板' : '新增模板'" width="520px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如:部署web服务" />
        </el-form-item>
        <el-form-item label="项目" prop="project_id">
          <el-select v-model="form.project_id" placeholder="请选择项目" class="full-width" @change="onProjectChange">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Playbook" prop="playbook">
          <el-select
            v-model="form.playbook"
            placeholder="请先选择项目"
            class="full-width"
            :loading="playbooksLoading"
            :disabled="!form.project_id"
            filterable
          >
            <el-option v-for="pb in playbooks" :key="pb" :label="pb" :value="pb" />
          </el-select>
        </el-form-item>
        <el-form-item label="清单" prop="inventory_id">
          <el-select v-model="form.inventory_id" placeholder="请选择主机清单" class="full-width">
            <el-option v-for="inv in inventories" :key="inv.id" :label="inv.name" :value="inv.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="凭据">
          <el-select v-model="form.credential_id" placeholder="可选,不选则用清单凭据或清单默认账号" class="full-width" clearable>
            <el-option v-for="c in credentials" :key="c.id" :label="`${c.name} (${c.username})`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="额外变量">
          <el-input
            v-model="form.extra_vars"
            type="textarea"
            :rows="3"
            placeholder='JSON 格式,如 {"env": "prod"}(可选)'
          />
        </el-form-item>
        <el-form-item label="Limit">
          <el-input v-model="form.limit" placeholder="限制目标主机,如 web(可选)" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input v-model="form.tags" placeholder="只执行指定标签,逗号分隔(可选)" />
        </el-form-item>
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isViewer = computed(() => authStore.user?.role === 'viewer')

const router = useRouter()

const loading = ref(false)
const templates = ref([])
const projects = ref([])
const inventories = ref([])
const credentials = ref([])
const runningId = ref(null)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const playbooks = ref([])
const playbooksLoading = ref(false)

const form = reactive({
  id: null,
  name: '',
  project_id: null,
  playbook: '',
  inventory_id: null,
  credential_id: null,
  extra_vars: '',
  limit: '',
  tags: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  playbook: [{ required: true, message: '请选择 Playbook', trigger: 'change' }],
  inventory_id: [{ required: true, message: '请选择清单', trigger: 'change' }]
}

async function load() {
  loading.value = true
  try {
    const [tpls, projs, invs, creds] = await Promise.all([
      api.get('/templates'),
      api.get('/projects'),
      api.get('/inventories'),
      api.get('/credentials')
    ])
    templates.value = tpls.data
    projects.value = projs.data
    inventories.value = invs.data
    credentials.value = creds.data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function loadPlaybooks(projectId) {
  if (!projectId) {
    playbooks.value = []
    return
  }
  playbooksLoading.value = true
  try {
    const { data } = await api.get(`/projects/${projectId}/playbooks`)
    playbooks.value = data.playbooks || []
  } catch {
    playbooks.value = []
  } finally {
    playbooksLoading.value = false
  }
}

function onProjectChange() {
  form.playbook = ''
  loadPlaybooks(form.project_id)
}

function openDialog(row) {
  if (row) {
    Object.assign(form, {
      id: row.id,
      name: row.name,
      project_id: row.project_id,
      playbook: row.playbook,
      inventory_id: row.inventory_id,
      credential_id: row.credential_id,
      extra_vars: row.extra_vars || '',
      limit: row.limit || '',
      tags: row.tags || ''
    })
    loadPlaybooks(row.project_id)
  } else {
    Object.assign(form, {
      id: null,
      name: '',
      project_id: null,
      playbook: '',
      inventory_id: null,
      credential_id: null,
      extra_vars: '',
      limit: '',
      tags: ''
    })
    playbooks.value = []
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  // 校验 extra_vars 为合法 JSON
  if (form.extra_vars && form.extra_vars.trim()) {
    try {
      JSON.parse(form.extra_vars)
    } catch {
      ElMessage.warning('额外变量必须是合法的 JSON 格式')
      return
    }
  }
  saving.value = true
  try {
    const payload = {
      name: form.name,
      project_id: form.project_id,
      playbook: form.playbook,
      inventory_id: form.inventory_id,
      credential_id: form.credential_id,
      extra_vars: form.extra_vars || '',
      limit: form.limit || '',
      tags: form.tags || ''
    }
    if (form.id) {
      await api.put(`/templates/${form.id}`, payload)
      ElMessage.success('模板已更新')
    } else {
      await api.post('/templates', payload)
      ElMessage.success('模板已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function run(row) {
  runningId.value = row.id
  try {
    const { data } = await api.post('/tasks', { template_id: row.id })
    ElMessage.success(`任务 #${data.id} 已启动`)
    router.push(`/tasks/${data.id}`)
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    runningId.value = null
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定要删除模板「${row.name}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/templates/${row.id}`)
    ElMessage.success('模板已删除')
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

onMounted(load)
</script>

<style scoped>
.full-width {
  width: 100%;
}
</style>
