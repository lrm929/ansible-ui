<template>
  <div class="page-container">
    <el-card shadow="never" class="page-card">
      <div class="toolbar">
        <span class="title">定时任务</span>
        <el-button type="primary" :icon="Plus" @click="openDialog()">新增定时任务</el-button>
      </div>
      <el-table v-loading="loading" :data="schedules" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="template_name" label="任务模板" min-width="160" show-overflow-tooltip />
        <el-table-column label="Cron 表达式" width="150">
          <template #default="{ row }">
            <code class="cron">{{ row.cron }}</code>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              :loading="togglingId === row.id"
              @change="toggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="上次执行" width="170">
          <template #default="{ row }">{{ formatTime(row.last_run_at) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>暂无定时任务</template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑定时任务' : '新增定时任务'" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="任务模板" prop="template_id">
          <el-select v-model="form.template_id" placeholder="请选择任务模板" class="full-width">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron 表达式" prop="cron">
          <el-input v-model="form.cron" placeholder="5 段标准 cron,如 0 3 * * *" />
        </el-form-item>
        <el-form-item label=" ">
          <div class="cron-tips">
            <div>常用示例:</div>
            <div><code>0 3 * * *</code> 每天凌晨3点</div>
            <div><code>*/30 * * * *</code> 每30分钟</div>
            <div><code>0 0 * * 0</code> 每周日零点</div>
            <div><code>0 8 1 * *</code> 每月1号早上8点</div>
          </div>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.enabled" />
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'
import { formatTime } from '../utils/format'

const loading = ref(false)
const schedules = ref([])
const templates = ref([])
const togglingId = ref(null)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, template_id: null, cron: '', enabled: true })

const rules = {
  template_id: [{ required: true, message: '请选择任务模板', trigger: 'change' }],
  cron: [
    { required: true, message: '请输入 cron 表达式', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        const parts = (value || '').trim().split(/\s+/)
        if (parts.length !== 5) {
          callback(new Error('cron 表达式必须是 5 段,如 0 3 * * *'))
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
    const [schs, tpls] = await Promise.all([api.get('/schedules'), api.get('/templates')])
    schedules.value = schs.data
    templates.value = tpls.data
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  if (row) {
    Object.assign(form, { id: row.id, template_id: row.template_id, cron: row.cron, enabled: row.enabled })
  } else {
    Object.assign(form, { id: null, template_id: null, cron: '', enabled: true })
  }
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { template_id: form.template_id, cron: form.cron.trim(), enabled: form.enabled }
    if (form.id) {
      await api.put(`/schedules/${form.id}`, payload)
      ElMessage.success('定时任务已更新')
    } else {
      await api.post('/schedules', payload)
      ElMessage.success('定时任务已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function toggle(row) {
  togglingId.value = row.id
  try {
    await api.post(`/schedules/${row.id}/toggle`)
    ElMessage.success(row.enabled ? '已禁用' : '已启用')
    await load()
  } catch {
    // 错误提示由拦截器统一处理
  } finally {
    togglingId.value = null
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定要删除定时任务「${row.template_name}」吗?`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/schedules/${row.id}`)
    ElMessage.success('定时任务已删除')
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

.cron {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  background: #f4f4f5;
  padding: 2px 6px;
  border-radius: 3px;
}

.cron-tips {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
}

.cron-tips code {
  font-family: Consolas, 'Courier New', monospace;
  background: #f4f4f5;
  padding: 1px 5px;
  border-radius: 3px;
  margin-right: 6px;
}
</style>
