// 时间格式化与状态映射工具

function pad(n) {
  return n < 10 ? '0' + n : '' + n
}

// ISO 时间字符串 → 本地时间 'YYYY-MM-DD HH:mm:ss'
export function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 计算耗时
export function formatDuration(startIso, endIso) {
  if (!startIso) return '-'
  const start = new Date(startIso).getTime()
  const end = endIso ? new Date(endIso).getTime() : Date.now()
  if (Number.isNaN(start) || Number.isNaN(end)) return '-'
  const sec = Math.max(0, Math.round((end - start) / 1000))
  if (sec < 60) return `${sec}秒`
  const min = Math.floor(sec / 60)
  const remSec = sec % 60
  if (min < 60) return `${min}分${remSec}秒`
  const hour = Math.floor(min / 60)
  return `${hour}时${min % 60}分${remSec}秒`
}

// 任务状态 → 中文 + el-tag 类型
export const taskStatusMap = {
  success: { text: '成功', type: 'success' },
  failed: { text: '失败', type: 'danger' },
  running: { text: '运行中', type: 'primary' },
  pending: { text: '等待中', type: 'info' },
  stopped: { text: '已停止', type: 'warning' }
}

export function taskStatus(status) {
  return taskStatusMap[status] || { text: status || '未知', type: 'info' }
}

// 项目同步状态 → 中文 + el-tag 类型
export const syncStatusMap = {
  ok: { text: '同步成功', type: 'success' },
  error: { text: '同步失败', type: 'danger' },
  never: { text: '从未同步', type: 'info' }
}

export function syncStatus(status) {
  return syncStatusMap[status] || { text: status || '未知', type: 'info' }
}

// 去掉日志文本中的 ANSI 颜色控制序列(\x1b[...m)
// eslint-disable-next-line no-control-regex
const ansiPattern = /\x1b\[[0-9;]*m/g

export function stripAnsi(text) {
  if (!text) return ''
  return text.replace(ansiPattern, '')
}
