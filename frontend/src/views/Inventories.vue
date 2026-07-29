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
            <el-table-column label="名称" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag :type="row.os_type === 'windows' ? 'primary' : 'success'" size="small" class="os-tag">
                  {{ row.os_type === 'windows' ? 'Windows' : 'Linux' }}
                </el-tag>
                {{ row.name }}
                <div v-if="row.credential_name" class="cred-name">凭证:{{ row.credential_name }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="host_count" label="主机数" width="70" />
            <el-table-column label="自动拉取" width="150">
              <template #default="{ row }">
                <template v-if="row.source_url">
                  <el-tag :type="syncTagType(row.sync_status)" size="small">
                    {{ syncStatusText(row.sync_status) }}
                  </el-tag>
                  <div v-if="row.last_sync_at" class="sync-time">{{ formatTime(row.last_sync_at) }}</div>
                </template>
                <span v-else>-</span>
              </template>
            </el-table-column>
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
            <div class="host-actions">
              <el-upload
                :show-file-list="false"
                accept=".csv,text/csv"
                :http-request="uploadCsv"
                class="csv-upload"
              >
                <el-button size="small" :icon="Upload" :disabled="!currentInv">上传 CSV</el-button>
              </el-upload>
              <el-button
                size="small"
                :icon="Refresh"
                :disabled="!currentInv?.source_url"
                :loading="syncing"
                @click="syncInv"
              >
                同步
              </el-button>
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
    <el-dialog v-model="invDialogVisible" :title="invForm.id ? '编辑清单' : '新增清单'" width="560px" :close-on-click-modal="false">
      <el-form ref="invFormRef" :model="invForm" :rules="invRules" label-width="110px">
        <el-form-item label="清单名称" prop="name">
          <el-input v-model="invForm.name" placeholder="请输入清单名称" />
        </el-form-item>
        <el-form-item label="系统类型" prop="os_type">
          <el-select v-model="invForm.os_type" class="full-width" @change="onOsTypeChange">
            <el-option label="Linux (SSH)" value="linux" />
            <el-option label="Windows (WinRM)" value="windows" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="invForm.description" type="textarea" :rows="2" placeholder="请输入描述(可选)" />
        </el-form-item>
        <el-form-item label="资产接口 URL">
          <el-input v-model="invForm.source_url" type="textarea" :rows="2" placeholder="如 http://资产平台/api/hosts,返回 JSON 或 CSV" clearable />
        </el-form-item>
        <el-form-item label="本地资产文件">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".csv,.txt,text/csv,text/plain"
            :on-change="onCsvSelected"
            :on-remove="onCsvRemoved"
            class="csv-select"
          >
            <el-button size="small" :icon="Upload">选择文件</el-button>
            <template #tip>
              <div class="upload-tip">保存清单后自动导入;支持 CSV(带表头)或资产 TXT(每行:昵称 IP 组名)</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="排除规则">
          <el-input v-model="invForm.exclude_rules" type="textarea" :rows="3" placeholder="每行一条,主机名或分组包含即排除,如 Web" />
        </el-form-item>
        <el-form-item label="选择凭证">
          <el-select v-model="invForm.credential_id" placeholder="可选" class="full-width" clearable>
            <el-option v-for="c in credentials" :key="c.id" :label="`${c.name} (${c.username})`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认账号">
          <el-input
            v-model="invForm.default_username"
            :disabled="!!invForm.credential_id"
            :placeholder="invForm.credential_id ? '已选择凭证,无需填写' : '如 root / Administrator(可选)'"
          />
        </el-form-item>
        <el-form-item label="默认密码">
          <el-input
            v-model="invForm.default_password"
            type="password"
            show-password
            :disabled="!!invForm.credential_id"
            :placeholder="defaultPasswordPlaceholder"
          />
        </el-form-item>
        <el-form-item label="默认端口">
          <el-input-number v-model="invForm.default_port" :min="1" :max="65535" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Upload } from '@element-plus/icons-vue'
import api from '../api'
import { formatTime } from '../utils/format'

const inventories = ref([])
const hosts = ref([])
const credentials = ref([])
const currentInv = ref(null)
const invLoading = ref(false)
const hostLoading = ref(false)
const syncing = ref(false)

// 清单对话框
const invDialogVisible = ref(false)
const invSaving = ref(false)
const invFormRef = ref(null)
const invForm = reactive({
  id: null,
  name: '',
  os_type: 'linux',
  description: '',
  source_url: '',
  exclude_rules: '',
  credential_id: null,
  default_username: '',
  default_password: '',
  default_port: 22
})
const invRules = {
  name: [{ required: true, message: '请输入清单名称', trigger: 'blur' }],
  os_type: [{ required: true, message: '请选择系统类型', trigger: 'change' }]
}
// 对话框里选中待导入的 CSV 原始文件(保存清单成功后才真正上传)
const pendingCsv = ref(null)

const defaultPasswordPlaceholder = computed(() => {
  if (invForm.credential_id) return '已选择凭证,无需填写'
  return invForm.id ? '留空表示保持原密码不变' : '可选'
})

function onOsTypeChange(osType) {
  invForm.default_port = osType === 'windows' ? 5985 : 22
}

function onCsvSelected(uploadFile) {
  pendingCsv.value = uploadFile.raw
}

function onCsvRemoved() {
  pendingCsv.value = null
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
  pendingCsv.value = null
  if (row) {
    Object.assign(invForm, {
      id: row.id,
      name: row.name,
      os_type: row.os_type || 'linux',
      description: row.description || '',
      source_url: row.source_url || '',
      exclude_rules: row.exclude_rules || '',
      credential_id: row.credential_id,
      default_username: row.default_username || '',
      default_password: '',
      default_port: row.default_port || (row.os_type === 'windows' ? 5985 : 22)
    })
  } else {
    Object.assign(invForm, {
      id: null,
      name: '',
      os_type: 'linux',
      description: '',
      source_url: '',
      exclude_rules: '',
      credential_id: null,
      default_username: '',
      default_password: '',
      default_port: 22
    })
  }
  invDialogVisible.value = true
}

async function saveInv() {
  await invFormRef.value.validate()
  invSaving.value = true
  try {
    const payload = {
      name: invForm.name,
      os_type: invForm.os_type,
      description: invForm.description,
      source_url: invForm.source_url.trim(),
      exclude_rules: invForm.exclude_rules,
      credential_id: invForm.credential_id || 0, // 0 表示清除绑定
      default_username: invForm.credential_id ? '' : invForm.default_username,
      default_port: invForm.default_port
    }
    if (invForm.default_password) {
      payload.default_password = invForm.default_password
    }
    let savedId = invForm.id
    if (invForm.id) {
      await api.put(`/inventories/${invForm.id}`, payload)
      ElMessage.success('清单已更新')
    } else {
      const { data } = await api.post('/inventories', payload)
      savedId = data.id
      ElMessage.success('清单已创建')
    }
    invDialogVisible.value = false
    // 保存成功后若选了本地资产文件,立即导入
    if (pendingCsv.value && savedId) {
      const fd = new FormData()
      fd.append('file', pendingCsv.value)
      pendingCsv.value = null
      try {
        const { data } = await api.post(`/inventories/${savedId}/hosts/import`, fd)
        showImportResult(data)
      } catch {
        // 错误提示由拦截器统一处理
      }
    }
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

async function uploadCsv({ file }) {
  if (!currentInv.value) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const { data } = await api.post(`/inventories/${currentInv.value.id}/hosts/import`, fd)
    showImportResult(data)
    await loadHosts()
    await loadInventories()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

async function syncInv() {
  if (!currentInv.value?.source_url) return
  syncing.value = true
  try {
    const { data } = await api.post(`/inventories/${currentInv.value.id}/sync`)
    showImportResult(data)
    await loadHosts()
    await loadInventories()
  } catch {
    // 错误提示由拦截器统一处理;同步状态刷新出来
    await loadInventories()
  } finally {
    syncing.value = false
  }
}

function showImportResult(data) {
  let msg = `新增 ${data.added} 台,更新 ${data.updated} 台`
  if (data.excluded) msg += `,排除 ${data.excluded} 台`
  ElMessage.success(msg)
  if (data.errors && data.errors.length) {
    ElMessageBox.alert(data.errors.join('\n'), '部分行导入失败', {
      confirmButtonText: '知道了',
      type: 'warning'
    })
  }
}

function syncTagType(status) {
  if (status === 'ok') return 'success'
  if (status === 'error') return 'danger'
  return 'info'
}

function syncStatusText(status) {
  if (status === 'ok') return '同步成功'
  if (status === 'error') return '同步失败'
  return '未同步'
}

onMounted(async () => {
  loadInventories(false)
  try {
    const { data } = await api.get('/credentials')
    credentials.value = data
  } catch {
    // 错误提示由拦截器统一处理
  }
})
</script>

<style scoped>
.inv-desc {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
  margin-left: 8px;
}

.host-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.csv-upload {
  display: inline-block;
}

.sync-time {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.os-tag {
  margin-right: 6px;
}

.cred-name {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.full-width {
  width: 100%;
}

.csv-select {
  width: 100%;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
</style>
