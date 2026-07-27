import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi, beforeAll } from 'vitest';
import type { NavigationDirection } from 'react-router-dom';

// 每个测试后自动清理 DOM
afterEach(() => {
  cleanup();
});

// ── jsdom 环境补丁 ──

// matchMedia polyfill（Ant Design 组件需要）
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });

  // IntersectionObserver polyfill（部分组件需要）
  class MockIntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error - polyfill
  window.IntersectionObserver = MockIntersectionObserver;

  // ResizeObserver polyfill
  class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error - polyfill
  window.ResizeObserver = MockResizeObserver;

  // scrollTo polyfill
  window.scrollTo = () => {};

  // react-router v7 的 navigate 在 jsdom 中需要 history 支持
  if (!window.history.scrollRestoration) {
    window.history.scrollRestoration = 'manual';
  }
});

// ── Mock antd message ──
// antd 的 message 和 notification 使用 DOM 操作，在测试中需要 mock
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
      loading: vi.fn(),
    },
  };
});
