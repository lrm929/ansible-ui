<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <el-tabs v-model="activeTab">
        <!-- 用户管理(仅 admin) -->
        <el-tab-pane v-if="isAdmin" label="用户管理" name="users">
          <div class="toolbar">
            <span class="title">用户</span>
            <el-button type="primary" size="small" :icon="Plus" @click="openUserDialog()">新增用户</el-button>
          </div>
          <el-table v-loading="usersLoading" :data="users" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" label="用户名" min-width="140" />
            <el-table-column label="角色" width="120">
              <template #default="{ row }">
                <el-tag :type="roleTagType(row.role)">{{ roleText(row.role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="openUserDialog(row)">编辑</el-button>
                <el-button text type="danger" size="small" @click="removeUser(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty>暂无用户</template>
          </el-table>
        </el-tab-pane>

        <!-- 权限管理(只读矩阵) -->
        <el-tab-pane label="权限管理" name="roles">
          <el-table :data="roleMatrix" border class="matrix-table">
            <el-table-column prop="role" label="角色" width="140">
              <template #default="{ row }">
                <el-tag :type="row.tagType">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="用户管理" width="120" align="center">
              <template #default="{ row }">{{ row.userMgmt }}</template>
            </el-table-column>
            <el-table-column label="清单/凭据/项目管理" min-width="160" align="center">
              <template #default="{ row }">{{ row.resourceMgmt }}</template>
            </el-table-column>
            <el-table-column label="执行任务" width="120" align="center">
              <template #default="{ row }">{{ row.runTask }}</template>
            </el-table-column>
            <el-table-column label="查看" width="120" align="center">
              <template #default>{{
                '✓'
              }}</template>
            </el-table-column>
          </el-table>
          <el-alert
            class="matrix-tip"
            type="info"
            :closable="false"
            title="管理员拥有全部权限;操作员除用户管理外全部;只读仅查看。角色在用户管理中分配,修改角色后用户需重新登录生效。"
          />
        </el-tab-pane>

        <!-- 通知设置(企业微信 webhook) -->
        <el-tab-pane label="通知设置" name="webhook">
          <el-alert
            class="tab-tip"
            type="info"
            :closable="false"
            title="如何获取企业微信群机器人 Webhook:群聊 → 群机器人 → 添加 → 复制 Webhook 地址"
          />
          <el-form :model="webhookForm" label-width="140px" class="settings-form" v-loading="webhookLoading">
            <el-form-item label="Webhook 地址">
              <el-input
                v-model="webhookForm.webhook_url"
                placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx"
                clearable
              />
            </el-form-item>
            <el-form-item label="启用通知">
              <el-switch v-model="webhookForm.enabled" />
            </el-form-item>
            <el-form-item label="成功时通知">
              <el-switch v-model="webhookForm.notify_on_success" />
            </el-form-item>
            <el-form-item label="失败/停止时通知">
              <el-switch v-model="webhookForm.notify_on_failure" />
            </el-form-item>
            <el-form-item>
              <el-button v-if="!isViewer" type="primary" :loading="webhookSaving" @click="saveWebhook">保存</el-button>
              <el-button v-if="!isViewer" :loading="webhookTesting" @click="sendWebhookTest">发送测试消息</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 系统偏好 -->
        <el-tab-pane label="系统偏好" name="prefs">
          <el-form label-width="140px" class="settings-form">
            <el-form-item label="系统名称">
              <el-input v-model="siteName" placeholder="显示在登录页和主菜单标题" />
            </el-form-item>
            <el-form-item>
              <el-button v-if="!isViewer" type="primary" :loading="siteSaving" @click="saveSiteName">保存</el-button>
            </el-form-item>
            <el-divider />
            <el-form-item label="登录背景图">
              <div class="bg-area">
                <img v-if="hasLoginBg" :src="bgUrl" class="bg-preview" alt="登录背景" />
                <span v-else class="bg-empty">未设置(默认渐变背景)</span>
                <div class="bg-actions">
                  <el-upload
                    v-if="!isViewer"
                    :show-file-list="false"
                    accept=".jpg,.jpeg,.png,.webp"
                    :http-request="uploadBg"
                    class="bg-upload"
                  >
                    <el-button size="small" :loading="bgUploading">上传图片</el-button>
                  </el-upload>
                  <el-button
                    v-if="!isViewer && hasLoginBg"
                    size="small"
                    type="danger"
                    :loading="bgDeleting"
                    @click="removeBg"
                  >
                    删除背景
                  </el-button>
                </div>
                <div class="bg-tip">支持 jpg / png / webp,不超过 2MB;上传后刷新登录页生效</div>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 用户新增/编辑对话框 -->
    <el-dialog v-model="userDialogVisible" :title="userForm.id ? '编辑用户' : '新增用户'" width="440px" :close-on-click-modal="false">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="!!userForm.id" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" class="full-width">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="只读" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item :label="userForm.id ? '重置密码' : '密码'" prop="password">
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
            :placeholder="userForm.id ? '留空表示不修改密码' : '请输入密码'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="userSaving" @click="saveUser">确定</el-button>
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
const isAdmin = computed(() => authStore.user?.role === 'admin')
const isViewer = computed(() => authStore.user?.role === 'viewer')

const activeTab = ref(isAdmin.value ? 'users' : 'roles')

// ---------- 用户管理 ----------
const usersLoading = ref(false)
const users = ref([])
const userDialogVisible = ref(false)
const userSaving = ref(false)
const userFormRef = ref(null)
const userForm = reactive({ id: null, username: '', role: 'operator', password: '' })

const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!userForm.id && !value) {
          callback(new Error('请输入密码'))
        } else if (value && value.length < 6) {
          callback(new Error('密码长度不能少于6位'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

async function loadUsers() {
  if (!isAdmin.value) return
  usersLoading.value = true
  try {
    const { data } = await api.get('/users')
    users.value = data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    usersLoading.value = false
  }
}

function openUserDialog(row) {
  if (row) {
    Object.assign(userForm, { id: row.id, username: row.username, role: row.role, password: '' })
  } else {
    Object.assign(userForm, { id: null, username: '', role: 'operator', password: '' })
  }
  userDialogVisible.value = true
}

async function saveUser() {
  await userFormRef.value.validate()
  userSaving.value = true
  try {
    if (userForm.id) {
      const payload = { role: userForm.role }
      if (userForm.password) payload.password = userForm.password
      await api.put(`/users/${userForm.id}`, payload)
      ElMessage.success('用户已更新')
    } else {
      await api.post('/users', {
        username: userForm.username.trim(),
        password: userForm.password,
        role: userForm.role
      })
      ElMessage.success('用户已创建')
    }
    userDialogVisible.value = false
    await loadUsers()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    userSaving.value = false
  }
}

async function removeUser(row) {
  try {
    await ElMessageBox.confirm(`确定要删除用户「${row.username}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/users/${row.id}`)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch {
    // 错误提示由拦截器统一处理
  }
}

function roleTagType(role) {
  if (role === 'admin') return 'danger'
  if (role === 'operator') return 'primary'
  return 'info'
}

function roleText(role) {
  if (role === 'admin') return '管理员'
  if (role === 'operator') return '操作员'
  return '只读'
}

// ---------- 权限矩阵(静态只读) ----------
const roleMatrix = [
  { role: '管理员', tagType: 'danger', userMgmt: '✓', resourceMgmt: '✓', runTask: '✓' },
  { role: '操作员', tagType: 'primary', userMgmt: '✗', resourceMgmt: '✓', runTask: '✓' },
  { role: '只读', tagType: 'info', userMgmt: '✗', resourceMgmt: '✗', runTask: '✗' }
]

// ---------- 通知设置 ----------
const webhookLoading = ref(false)
const webhookSaving = ref(false)
const webhookTesting = ref(false)
const webhookForm = reactive({
  webhook_url: '',
  enabled: false,
  notify_on_success: true,
  notify_on_failure: true
})
const webhookSnapshot = ref('')

const webhookDirty = computed(() => JSON.stringify(webhookForm) !== webhookSnapshot.value)

async function loadWebhook() {
  webhookLoading.value = true
  try {
    const { data } = await api.get('/settings/webhook')
    Object.assign(webhookForm, data)
    webhookSnapshot.value = JSON.stringify(webhookForm)
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    webhookLoading.value = false
  }
}

async function saveWebhook() {
  webhookSaving.value = true
  try {
    const { data } = await api.put('/settings/webhook', { ...webhookForm })
    Object.assign(webhookForm, data)
    webhookSnapshot.value = JSON.stringify(webhookForm)
    ElMessage.success('通知设置已保存')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    webhookSaving.value = false
  }
}

async function sendWebhookTest() {
  if (webhookDirty.value) {
    ElMessage.warning('配置已修改,请先保存再发送测试消息')
    return
  }
  if (!webhookForm.webhook_url) {
    ElMessage.warning('请先填写并保存 Webhook 地址')
    return
  }
  webhookTesting.value = true
  try {
    await api.post('/settings/webhook/test')
    ElMessage.success('测试消息已发送,请到企业微信群查看')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    webhookTesting.value = false
  }
}

// ---------- 系统偏好 ----------
const siteName = ref('')
const siteSaving = ref(false)
const hasLoginBg = ref(false)
const bgTs = ref(Date.now())
const bgUploading = ref(false)
const bgDeleting = ref(false)

const bgUrl = computed(() => `/api/system/login-bg?t=${bgTs.value}`)

async function loadSystemInfo() {
  try {
    const { data } = await api.get('/system/info')
    siteName.value = data.site_name
    hasLoginBg.value = data.has_login_bg
  } catch {
    // 公开接口失败时静默用默认值
  }
}

async function saveSiteName() {
  if (!siteName.value.trim()) {
    ElMessage.warning('系统名称不能为空')
    return
  }
  siteSaving.value = true
  try {
    await api.put('/system/info', { site_name: siteName.value.trim() })
    ElMessage.success('系统名称已保存,刷新页面生效')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    siteSaving.value = false
  }
}

async function uploadBg({ file }) {
  const okTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!okTypes.includes(file.type)) {
    ElMessage.warning('仅支持 jpg / png / webp 图片')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 2MB')
    return
  }
  bgUploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await api.post('/system/login-bg', fd)
    ElMessage.success('登录背景已更新,刷新页面生效')
    hasLoginBg.value = true
    bgTs.value = Date.now()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    bgUploading.value = false
  }
}

async function removeBg() {
  bgDeleting.value = true
  try {
    await api.delete('/system/login-bg')
    ElMessage.success('登录背景已删除')
    hasLoginBg.value = false
    bgTs.value = Date.now()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    bgDeleting.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadWebhook()
  loadSystemInfo()
})
</script>

<style scoped>
.full-width {
  width: 100%;
}

.settings-form {
  max-width: 720px;
  margin-top: 8px;
}

.tab-tip {
  margin-bottom: 12px;
}

.matrix-table {
  max-width: 860px;
}

.matrix-tip {
  margin-top: 12px;
  max-width: 860px;
}

.bg-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bg-preview {
  width: 320px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.bg-empty {
  color: #909399;
  font-size: 13px;
}

.bg-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bg-tip {
  font-size: 12px;
  color: #909399;
}
</style>
