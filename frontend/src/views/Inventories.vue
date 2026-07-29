<template>
  <div class="page-container">
    <el-row :gutter="16">
      <!-- 左侧:清单列表 -->
      <el-col :span="8">
        <el-card shadow="never" class="page-card">
          <div class="toolbar">
            <span class="title">清单</span>
            <el-button type="primary" size="small" :icon="Plus" @click="openInvDialog()">新增清单</el-button>
          </div>
          <el-table
            v-loading="invLoading"
            :data="inventories"
            highlight-current-row
            @current-change="onSelectInv"
          >
            <el-table-column prop="name" label="名称" min-width="110" show-overflow-tooltip />
            <el-table-column prop="host_count" label="主机数" width="70" />
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click.stop="openInvDialog(row)">编辑</el-button>
                <el-button text type="danger" size="small" @click.stop="deleteInv(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty>暂无清单,请先新增</template>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧:当前清单的主机 -->
      <el-col :span="16">
        <el-card shadow="never" class="page-card">
          <div class="toolbar">
            <span class="title">
              主机{{ currentInv ? ` - ${currentInv.name}` : '' }}
              <span v-if="currentInv?.description" class="inv-desc">{{ currentInv.description }}</span>
            </span>
            <el-button
              type="primary"
              size="small"
              :icon="Plus"
              :disabled="!currentInv"
              @click="openHostDialog()"
            >
              新增主机
            </el-button>
          </div>
          <el-table v-loading="hostLoading" :data="hosts" stripe>
            <el-table-column prop="hostname" label="主机地址" min-width="140" show-overflow-tooltip />
            <el-table-column prop="port" label="端口" width="70" />
            <el-table-column prop="group_name" label="分组" width="100">
              <template #default="{ row }">{{ row.group_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="vars" label="变量" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">{{ row.vars || '-' }}</template>
            </el-table-column>
            <el-table-column prop="comment" label="备注" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.comment || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="openHostDialog(row)">编辑</el-button>
                <el-button text type="danger" size="small" @click="deleteHost(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty>{{ currentInv ? '该清单下暂无主机' : '请先选择左侧清单' }}</template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 清单新增/编辑对话框 -->
    <el-dialog v-model="invDialogVisible" :title="invForm.id ? '编辑清单' : '新增清单'" width="440px" :close-on-click-modal="false">
      <el-form ref="invFormRef" :model="invForm" :rules="invRules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="invForm.name" placeholder="请输入清单名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="invForm.description" type="textarea" :rows="2" placeholder="请输入描述(可选)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="invDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="invSaving" @click="saveInv">确定</el-button>
      </template>
    </el-dialog>

    <!-- 主机新增/编辑对话框 -->
    <el-dialog v-model="hostDialogVisible" :title="hostForm.id ? '编辑主机' : '新增主机'" width="480px" :close-on-click-modal="false">
      <el-form ref="hostFormRef" :model="hostForm" :rules="hostRules" label-width="90px">
        <el-form-item label="主机地址" prop="hostname">
          <el-input v-model="hostForm.hostname" placeholder="IP 或域名,如 192.168.1.10" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="hostForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="hostForm.group_name" placeholder="如 web / db(可选)" />
        </el-form-item>
        <el-form-item label="变量">
          <el-input v-model="hostForm.vars" placeholder="如 ansible_user=root(可选)" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="hostForm.comment" placeholder="备注信息(可选)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="hostDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="hostSaving" @click="saveHost">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'

const inventories = ref([])
const hosts = ref([])
const currentInv = ref(null)
const invLoading = ref(false)
const hostLoading = ref(false)

// 清单对话框
const invDialogVisible = ref(false)
const invSaving = ref(false)
const invFormRef = ref(null)
const invForm = reactive({ id: null, name: '', description: '' })
const invRules = {
  name: [{ required: true, message: '请输入清单名称', trigger: 'blur' }]
}

// 主机对话框
const hostDialogVisible = ref(false)
const hostSaving = ref(false)
const hostFormRef = ref(null)
const hostForm = reactive({ id: null, hostname: '', port: 22, group_name: '', vars: '', comment: '' })
const hostRules = {
  hostname: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }]
}

async function loadInventories(keepSelection = true) {
  invLoading.value = true
  try {
    const { data } = await api.get('/inventories')
    inventories.value = data
    if (keepSelection && currentInv.value) {
      const found = data.find((i) => i.id === currentInv.value.id)
      currentInv.value = found || null
    }
    if (!currentInv.value && data.length > 0) {
      currentInv.value = data[0]
    }
    if (currentInv.value) {
      await loadHosts()
    } else {
      hosts.value = []
    }
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    invLoading.value = false
  }
}

async function loadHosts() {
  if (!currentInv.value) return
  hostLoading.value = true
  try {
    const { data } = await api.get(`/inventories/${currentInv.value.id}/hosts`)
    hosts.value = data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    hostLoading.value = false
  }
}

function onSelectInv(row) {
  if (!row) return
  currentInv.value = row
  loadHosts()
}

function openInvDialog(row) {
  if (row) {
    Object.assign(invForm, { id: row.id, name: row.name, description: row.description || '' })
  } else {
    Object.assign(invForm, { id: null, name: '', description: '' })
  }
  invDialogVisible.value = true
}

async function saveInv() {
  await invFormRef.value.validate()
  invSaving.value = true
  try {
    const payload = { name: invForm.name, description: invForm.description }
    if (invForm.id) {
      await api.put(`/inventories/${invForm.id}`, payload)
      ElMessage.success('清单已更新')
    } else {
      await api.post('/inventories', payload)
      ElMessage.success('清单已创建')
    }
    invDialogVisible.value = false
    await loadInventories()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    invSaving.value = false
  }
}

async function deleteInv(row) {
  try {
    await ElMessageBox.confirm(`确定要删除清单「${row.name}」吗?其下主机将一并删除。`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/inventories/${row.id}`)
    ElMessage.success('清单已删除')
    if (currentInv.value?.id === row.id) currentInv.value = null
    await loadInventories(false)
  } catch {
    // 错误提示由拦截器统一处理
  }
}

function openHostDialog(row) {
  if (row) {
    Object.assign(hostForm, {
      id: row.id,
      hostname: row.hostname,
      port: row.port,
      group_name: row.group_name || '',
      vars: row.vars || '',
      comment: row.comment || ''
    })
  } else {
    Object.assign(hostForm, { id: null, hostname: '', port: 22, group_name: '', vars: '', comment: '' })
  }
  hostDialogVisible.value = true
}

async function saveHost() {
  await hostFormRef.value.validate()
  hostSaving.value = true
  try {
    const payload = {
      hostname: hostForm.hostname,
      port: hostForm.port,
      group_name: hostForm.group_name,
      vars: hostForm.vars,
      comment: hostForm.comment
    }
    if (hostForm.id) {
      await api.put(`/hosts/${hostForm.id}`, payload)
      ElMessage.success('主机已更新')
    } else {
      await api.post(`/inventories/${currentInv.value.id}/hosts`, payload)
      ElMessage.success('主机已添加')
    }
    hostDialogVisible.value = false
    await loadHosts()
    await loadInventories()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    hostSaving.value = false
  }
}

async function deleteHost(row) {
  try {
    await ElMessageBox.confirm(`确定要删除主机「${row.hostname}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/hosts/${row.id}`)
    ElMessage.success('主机已删除')
    await loadHosts()
    await loadInventories()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

onMounted(() => loadInventories(false))
</script>

<style scoped>
.inv-desc {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
  margin-left: 8px;
}
</style>
