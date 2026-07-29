<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">凭据</span>
        <el-button v-if="!isViewer" type="primary" :icon="Plus" @click="openDialog()">新增凭据</el-button>
      </div>
      <el-table v-loading="loading" :data="credentials" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.type === 'key' ? 'warning' : 'primary'">
              {{ row.type === 'key' ? 'SSH 私钥' : '密码' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="登录用户" width="120" />
        <el-table-column label="密钥/密码" width="130">
          <template #default>
            <span class="secret-tip">已加密存储</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column v-if="!isViewer" label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无凭据</template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑凭据' : '新增凭据'" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如:生产服务器root" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-radio-group v-model="form.type" :disabled="!!form.id">
            <el-radio value="password">密码</el-radio>
            <el-radio value="key">SSH 私钥</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="登录用户" prop="username">
          <el-input v-model="form.username" placeholder="如 root" />
        </el-form-item>
        <el-form-item v-if="form.type === 'password'" label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="form.id ? '留空表示不修改' : '请输入密码'"
          />
        </el-form-item>
        <el-form-item v-else label="私钥">
          <el-input
            v-model="form.ssh_key"
            type="textarea"
            :rows="7"
            :placeholder="form.id ? '留空表示不修改' : '粘贴 SSH 私钥内容(-----BEGIN ... 开头)'"
          />
        </el-form-item>
        <el-form-item v-if="form.id" label=" ">
          <span class="secret-tip">密钥已加密存储,出于安全考虑不会回显</span>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'
import { formatTime } from '../utils/format'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isViewer = computed(() => authStore.user?.role === 'viewer')

const loading = ref(false)
const credentials = ref([])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, name: '', type: 'password', username: '', password: '', ssh_key: '' })

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  username: [{ required: true, message: '请输入登录用户', trigger: 'blur' }],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!form.id && form.type === 'password' && !value) {
          callback(new Error('请输入密码'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/credentials')
    credentials.value = data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  if (row) {
    Object.assign(form, { id: row.id, name: row.name, type: row.type, username: row.username, password: '', ssh_key: '' })
  } else {
    Object.assign(form, { id: null, name: '', type: 'password', username: '', password: '', ssh_key: '' })
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  // 新增时 key 类型必须填私钥
  if (!form.id && form.type === 'key' && !form.ssh_key) {
    ElMessage.warning('请输入 SSH 私钥')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name, type: form.type, username: form.username }
    // 密码/私钥只在填写时提交,留空表示不修改
    if (form.type === 'password' && form.password) payload.password = form.password
    if (form.type === 'key' && form.ssh_key) payload.ssh_key = form.ssh_key

    if (form.id) {
      await api.put(`/credentials/${form.id}`, payload)
      ElMessage.success('凭据已更新')
    } else {
      await api.post('/credentials', payload)
      ElMessage.success('凭据已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定要删除凭据「${row.name}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/credentials/${row.id}`)
    ElMessage.success('凭据已删除')
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

onMounted(load)
</script>

<style scoped>
.secret-tip {
  font-size: 12px;
  color: #909399;
}
</style>
