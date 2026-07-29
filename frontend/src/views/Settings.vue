<template>
  <div class="page-container">
    <el-alert
      class="tip"
      type="info"
      :closable="false"
      title="如何获取企业微信群机器人 Webhook:群聊 → 群机器人 → 添加 → 复制 Webhook 地址"
    />
    <el-card shadow="never" class="page-card" v-loading="loading">
      <div class="toolbar">
        <span class="title">通知设置(企业微信)</span>
      </div>
      <el-form :model="form" label-width="140px" class="settings-form">
        <el-form-item label="Webhook 地址">
          <el-input
            v-model="form.webhook_url"
            placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx"
            clearable
          />
        </el-form-item>
        <el-form-item label="启用通知">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="成功时通知">
          <el-switch v-model="form.notify_on_success" />
        </el-form-item>
        <el-form-item label="失败/停止时通知">
          <el-switch v-model="form.notify_on_failure" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button :loading="testing" @click="sendTest">发送测试消息</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const form = reactive({
  webhook_url: '',
  enabled: false,
  notify_on_success: true,
  notify_on_failure: true
})
const savedSnapshot = ref('')

const dirty = computed(() => JSON.stringify(form) !== savedSnapshot.value)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/settings/webhook')
    Object.assign(form, data)
    savedSnapshot.value = JSON.stringify(form)
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const { data } = await api.put('/settings/webhook', { ...form })
    Object.assign(form, data)
    savedSnapshot.value = JSON.stringify(form)
    ElMessage.success('通知设置已保存')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function sendTest() {
  if (dirty.value) {
    ElMessage.warning('配置已修改,请先保存再发送测试消息')
    return
  }
  if (!form.webhook_url) {
    ElMessage.warning('请先填写并保存 Webhook 地址')
    return
  }
  testing.value = true
  try {
    await api.post('/settings/webhook/test')
    ElMessage.success('测试消息已发送,请到企业微信群查看')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.tip {
  margin-bottom: 12px;
}

.settings-form {
  max-width: 720px;
  margin-top: 8px;
}
</style>
