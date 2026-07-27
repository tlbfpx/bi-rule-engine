/**
 * 前端日志工具
 *
 * 功能：
 * 1. trace_id 缓存管理（sessionStorage，标签页级别隔离）
 * 2. 错误上报到后端 /api/v1/logs/frontend-error
 * 3. 生产环境 console 管理
 */

const TRACE_ID_KEY = '__bi_trace_id__';

// ── trace_id 管理 ──
export const traceIdManager = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TRACE_ID_KEY);
    } catch {
      return null;
    }
  },
  set(traceId: string): void {
    try {
      sessionStorage.setItem(TRACE_ID_KEY, traceId);
    } catch {
      // sessionStorage 不可用时静默
    }
  },
  clear(): void {
    try {
      sessionStorage.removeItem(TRACE_ID_KEY);
    } catch {
      // 静默
    }
  },
};

// ── 错误上报 ──
export async function reportError(error: {
  message: string;
  stack?: string;
  url?: string;
}): Promise<void> {
  const traceId = traceIdManager.get();
  try {
    // 使用原生 fetch（非 axios，避免循环依赖和拦截器干扰）
    await fetch('/api/v1/logs/frontend-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        url: error.url || window.location.href,
        user_agent: navigator.userAgent,
        trace_id: traceId,
        timestamp: new Date().toISOString(),
      }),
    });
  } catch {
    // 上报失败静默处理，避免雪崩
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn('[Logger] 错误上报失败（后端不可达）');
    }
  }
}

// ── 初始化 ──
export function initLogger(): void {
  if (import.meta.env.PROD) {
    // 生产环境：关闭 debug/log，保留 error/warn
    const noop = () => {};
    console.debug = noop;
    console.log = noop;
  }
}
