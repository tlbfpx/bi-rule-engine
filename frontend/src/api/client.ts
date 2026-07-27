import axios from 'axios';
import { message } from 'antd';
import { traceIdManager, reportError } from '../utils/logger';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: 注入 trace_id
client.interceptors.request.use((config) => {
  const traceId = traceIdManager.get();
  if (traceId) {
    config.headers['X-Trace-Id'] = traceId;
  }
  return config;
});

// Response interceptor: 提取 trace_id + 错误上报
client.interceptors.response.use(
  (response) => {
    // 从响应头提取 trace_id 并缓存（后端首次返回时建立关联）
    const traceId = response.headers['x-trace-id'];
    if (traceId) {
      traceIdManager.set(traceId);
    }
    return response;
  },
  (error) => {
    // 即使出错也提取 trace_id
    const traceId = error.response?.headers?.['x-trace-id'];
    if (traceId) {
      traceIdManager.set(traceId);
    }

    const msg = error.response?.data?.detail || error.message || '请求失败';

    // 5xx 服务端错误：自动上报
    if (error.response?.status >= 500) {
      reportError({
        message: `HTTP ${error.response.status}: ${msg}`,
        url: error.config?.url,
      });
    }

    message.error(msg);
    return Promise.reject(error);
  }
);

export default client;
