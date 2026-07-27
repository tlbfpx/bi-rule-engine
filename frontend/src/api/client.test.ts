import { describe, it, expect, beforeEach, vi } from 'vitest';
import client from './client';
import { traceIdManager } from '../utils/logger';

// ── Mock antd message ──
vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    message: {
      ...actual.message,
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

describe('API Client (axios 实例)', () => {
  beforeEach(() => {
    traceIdManager.clear();
    vi.clearAllMocks();
  });

  // ============ 配置验证 ============

  it('baseURL 设置为 /api/v1', () => {
    expect(client.defaults.baseURL).toBe('/api/v1');
  });

  it('timeout 设置为 30000ms', () => {
    expect(client.defaults.timeout).toBe(30000);
  });

  it('Content-Type 设置为 application/json', () => {
    expect(client.defaults.headers['Content-Type']).toBe('application/json');
  });

  // ============ 请求拦截器 - trace_id 注入 ============

  it('请求拦截器在有 trace_id 时注入 X-Trace-Id 头', () => {
    traceIdManager.set('trace_integration_test');

    const config = {
      headers: {} as Record<string, string>,
      url: '/test',
      method: 'get',
    };

    // 获取请求拦截器的 fulfilled handler 并直接调用
    const handlers = client.interceptors.request.handlers;
    const handler = handlers.find((h: any) => h && typeof h.fulfilled === 'function');
    expect(handler).toBeDefined();
    const result = handler!.fulfilled(config);

    expect(result.headers['X-Trace-Id']).toBe('trace_integration_test');
  });

  it('请求拦截器在无 trace_id 时不注入 X-Trace-Id 头', () => {
    const config = {
      headers: {} as Record<string, string>,
      url: '/test',
      method: 'get',
    };

    const handlers = client.interceptors.request.handlers;
    const handler = handlers.find((h: any) => h && typeof h.fulfilled === 'function');
    const result = handler!.fulfilled(config);

    expect(result.headers['X-Trace-Id']).toBeUndefined();
  });

  it('请求拦截器保留 config 中的其他字段不变', () => {
    const config = {
      headers: {} as Record<string, string>,
      url: '/users',
      method: 'post' as const,
      data: { name: 'test' },
    };

    const handlers = client.interceptors.request.handlers;
    const handler = handlers.find((h: any) => h && typeof h.fulfilled === 'function');
    const result = handler!.fulfilled(config);

    expect(result.url).toBe('/users');
    expect(result.method).toBe('post');
    expect(result.data).toEqual({ name: 'test' });
  });

  // ============ 响应拦截器 - trace_id 提取 ============

  it('响应拦截器从响应头提取 trace_id', () => {
    const response = {
      headers: { 'x-trace-id': 'trace_from_server' },
      data: { ok: true },
      status: 200,
    };

    const handlers = client.interceptors.response.handlers;
    const handler = handlers.find((h: any) => h && typeof h.fulfilled === 'function');
    handler!.fulfilled(response);

    expect(traceIdManager.get()).toBe('trace_from_server');
  });

  it('响应拦截器在无 trace_id 头时不设置', () => {
    const response = {
      headers: {},
      data: { ok: true },
      status: 200,
    };

    const handlers = client.interceptors.response.handlers;
    const handler = handlers.find((h: any) => h && typeof h.fulfilled === 'function');
    handler!.fulfilled(response);

    expect(traceIdManager.get()).toBeNull();
  });

  it('响应拦截器返回原始 response 对象', () => {
    const response = {
      headers: {},
      data: { value: 42 },
      status: 200,
    };

    const handlers = client.interceptors.response.handlers;
    const handler = handlers.find((h: any) => h && typeof h.fulfilled === 'function');
    const result = handler!.fulfilled(response);

    expect(result).toBe(response);
  });

  // ============ 响应拦截器 - 错误处理 ============

  it('错误拦截器从错误响应头提取 trace_id', async () => {
    const error = {
      response: {
        headers: { 'x-trace-id': 'trace_from_error' },
        status: 500,
        data: { detail: '服务器内部错误' },
      },
      config: { url: '/test' },
      message: 'Request failed',
    };

    const handlers = client.interceptors.response.handlers;
    const handler = handlers.find((h: any) => h && typeof h.rejected === 'function');
    await expect(handler!.rejected(error)).rejects.toBe(error);
    expect(traceIdManager.get()).toBe('trace_from_error');
  });

  it('错误拦截器在没有 response 时（网络错误）reject', async () => {
    const error = {
      message: 'Network Error',
      config: { url: '/test' },
    };

    const handlers = client.interceptors.response.handlers;
    const handler = handlers.find((h: any) => h && typeof h.rejected === 'function');
    await expect(handler!.rejected(error)).rejects.toBe(error);
  });
});
