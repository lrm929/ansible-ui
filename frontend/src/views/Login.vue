<template>
  <div class="login-page" :style="bgStyle">
    <el-card class="login-card">
      <div class="login-header">
        <el-icon :size="36" color="#409eff"><Platform /></el-icon>
        <h1 class="login-title">{{ siteName }}</h1>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @keyup.enter="submit"
      >
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            class="login-btn"
            type="primary"
            :loading="loading"
            @click="submit"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const router = useRouter()
const auth = useAuthStore()

// 系统名称与登录背景(挂载时拉一次公开接口,失败静默用默认值)
const siteName = ref('Ansible 运维管理平台')
const hasLoginBg = ref(false)
const bgTs = Date.now()

const bgStyle = computed(() => {
  if (!hasLoginBg.value) return {}
  return {
    backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.55), rgba(0, 0, 0, 0.55)), url(/api/system/login-bg?t=${bgTs})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center'
  }
})

onMounted(async () => {
  try {
    const { data } = await api.get('/system/info')
    siteName.value = data.site_name
    hasLoginBg.value = data.has_login_bg
  } catch {
    // 静默用默认值
  }
})

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function submit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2b3a4d 100%);
}

.login-card {
  width: 400px;
  padding: 16px 12px;
  border-radius: 8px;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}

.login-title {
  font-size: 22px;
  color: #303133;
  font-weight: 600;
}

.login-btn {
  width: 100%;
}
</style>
