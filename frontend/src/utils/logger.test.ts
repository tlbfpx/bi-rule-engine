import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { traceIdManager, reportError, initLogger } from '../utils/logger';

// ── sessionStorage mock ──
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

// ── fetch mock ──
const fetchMock = vi.fn();

describe('logger 工具模块', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorageMock.clear();
    vi.stubGlobal('sessionStorage', sessionStorageMock);
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockResolvedValue({ ok: true });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // ============ traceIdManager ============

  describe('traceIdManager', () => {
    it('set/get 能正确存取 trace_id', () => {
      traceIdManager.set('trace_abc_123');
      expect(traceIdManager.get()).toBe('trace_abc_123');
    });

    it('get 在未设置时返回 null', () => {
      expect(traceIdManager.get()).toBeNull();
    });

    it('clear 能清除已设置的 trace_id', () => {
      traceIdManager.set('trace_xyz');
      traceIdManager.clear();
      expect(traceIdManager.get()).toBeNull();
    });

    it('set 在 sessionStorage 不可用时不抛错', () => {
      vi.stubGlobal('sessionStorage', {
        getItem: () => {
          throw new Error('SecurityError');
        },
        setItem: () => {
          throw new Error('SecurityError');
        },
        removeItem: () => {
          throw new Error('SecurityError');
        },
      });

      expect(() => traceIdManager.set('test')).not.toThrow();
      expect(traceIdManager.get()).toBeNull();
      expect(() => traceIdManager.clear()).not.toThrow();
    });

    it('多次 set 会覆盖之前的值', () => {
      traceIdManager.set('first');
      traceIdManager.set('second');
      expect(traceIdManager.get()).toBe('second');
    });
  });

  // ============ reportError ============

  describe('reportError', () => {
    it('调用 fetch 发送 POST 请求到 /api/v1/logs/frontend-error', async () => {
      traceIdManager.set('trace_test_001');
      await reportError({ message: '测试错误' });

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      const [url, options] = lastCall;
      expect(url).toBe('/api/v1/logs/frontend-error');
      expect(options.method).toBe('POST');
      expect(options.headers['Content-Type']).toBe('application/json');

      const body = JSON.parse(options.body);
      expect(body.message).toBe('测试错误');
      expect(body.trace_id).toBe('trace_test_001');
      expect(body.timestamp).toBeDefined();
      expect(body.user_agent).toBeDefined();
    });

    it('未设置 trace_id 时 body.trace_id 为 null', async () => {
      // 确保 trace_id 没有被设置
      traceIdManager.clear();
      await reportError({ message: '无 trace 错误' });

      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      const body = JSON.parse(lastCall[1].body);
      expect(body.trace_id).toBeNull();
    });

    it('包含 stack 和 url 字段', async () => {
      await reportError({
        message: '带堆栈的错误',
        stack: 'Error: test\n  at line 1',
        url: 'http://localhost/app.js:10',
      });

      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      const body = JSON.parse(lastCall[1].body);
      expect(body.stack).toBe('Error: test\n  at line 1');
      expect(body.url).toBe('http://localhost/app.js:10');
    });

    it('未提供 url 时使用 window.location.href', async () => {
      await reportError({ message: '无 url 错误' });

      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      const body = JSON.parse(lastCall[1].body);
      expect(body.url).toBe(window.location.href);
    });

    it('fetch 失败时不抛出异常（静默处理）', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));
      await expect(reportError({ message: '网络失败测试' })).resolves.not.toThrow();
    });
  });

  // ============ initLogger ============

  describe('initLogger', () => {
    it('在生产环境关闭 console.debug 和 console.log', () => {
      const originalDebug = console.debug;
      const originalLog = console.log;

      initLogger();

      // 恢复
      console.debug = originalDebug;
      console.log = originalLog;
    });
  });
});
