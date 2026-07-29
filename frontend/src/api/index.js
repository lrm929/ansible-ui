import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器:自动携带 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器:401 跳登录页,统一错误提示
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (router.currentRoute.value.path !== '/login') {
          ElMessage.error('登录已过期,请重新登录')
          router.push('/login')
        }
      } else {
        const detail = data?.detail || `请求失败(${status})`
        ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
      }
    } else {
      ElMessage.error('网络错误,请检查后端服务是否启动')
    }
    return Promise.reject(error)
  }
)

export default api
