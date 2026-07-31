import axios from 'axios';
import { message } from 'antd';
import { traceIdManager, reportError } from '../utils/logger';
import { useAuthStore } from '../stores/authStore';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: 注入 trace_id + JWT token
client.interceptors.request.use((config) => {
  const traceId = traceIdManager.get();
  if (traceId) {
    config.headers['X-Trace-Id'] = traceId;
  }
  // 自动附加 Authorization header
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: 提取 trace_id + 错误上报 + 401 重定向
client.interceptors.response.use(
  (response) => {
    const traceId = response.headers['x-trace-id'];
    if (traceId) {
      traceIdManager.set(traceId);
    }
    return response;
  },
  (error) => {
    const traceId = error.response?.headers?.['x-trace-id'];
    if (traceId) {
      traceIdManager.set(traceId);
    }

    // 401 Unauthorized — 清除 token 并重定向到登录页
    if (error.response?.status === 401) {
      const authStore = useAuthStore.getState();
      if (authStore.isAuthenticated) {
        authStore.logout();
        message.warning('登录已过期，请重新登录');
        // 使用 setTimeout 确保 message 先渲染
        setTimeout(() => {
          window.location.hash = '#/login';
        }, 100);
      }
      return Promise.reject(error);
    }

    const msg = error.response?.data?.detail || error.response?.data?.message || error.message || '请求失败';

    if (error.response?.status >= 500) {
      reportError({
        message: `HTTP ${error.response.status}: ${msg}`,
        url: error.config?.url,
      });
    }

    if (!error.config?.skipErrorMessage) {
      message.error(msg);
    }
    return Promise.reject(error);
  }
);

export default client;
