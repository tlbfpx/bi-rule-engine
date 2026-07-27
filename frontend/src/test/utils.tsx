import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { MemoryRouter } from 'react-router-dom';
import { type ReactElement, type ReactNode } from 'react';

// 为每个测试创建独立的 QueryClient（避免缓存污染）
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface WrapperOptions {
  initialEntries?: string[];
}

function createWrapper(options: WrapperOptions = {}) {
  const queryClient = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={zhCN}>
          <AntApp>
            <MemoryRouter initialEntries={options.initialEntries ?? ['/']}>
              {children}
            </MemoryRouter>
          </AntApp>
        </ConfigProvider>
      </QueryClientProvider>
    );
  };
}

/**
 * 渲染组件并自动包裹 QueryClient / ConfigProvider / Router 等必需 Provider
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: WrapperOptions & RenderOptions,
) {
  const { initialEntries, ...renderOptions } = options ?? {};
  return render(ui, {
    wrapper: createWrapper({ initialEntries }),
    ...renderOptions,
  });
}

export { createTestQueryClient };
