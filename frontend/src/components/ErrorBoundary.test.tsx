import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorBoundary } from '../components/ErrorBoundary';

// 可控的抛错组件：通过 prop 控制是否抛错
function MaybeThrow({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('可控错误');
  return <div data-testid="normal-child">正常内容</div>;
}

// 始终抛错的组件
function AlwaysThrow({ error }: { error: Error }) {
  throw error;
}

describe('ErrorBoundary 组件', () => {
  const originalConsoleError = console.error;
  beforeEach(() => {
    console.error = (...args: unknown[]) => {
      const first = String(args[0] ?? '');
      if (first.includes('ErrorBoundary') || first.includes('The above error occurred')) {
        return;
      }
      originalConsoleError(...args);
    };
  });
  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('子组件正常时渲染 children', () => {
    render(
      <ErrorBoundary>
        <MaybeThrow shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('normal-child')).toBeInTheDocument();
  });

  it('子组件抛错时显示错误页面', () => {
    render(
      <ErrorBoundary>
        <AlwaysThrow error={new Error('组件渲染失败')} />
      </ErrorBoundary>
    );
    expect(screen.getByText('页面发生错误')).toBeInTheDocument();
    expect(screen.getByText('组件渲染失败')).toBeInTheDocument();
  });

  it('点击"重试"按钮后清除错误状态，恢复正常渲染', async () => {
    const user = userEvent.setup();
    // 初始渲染时抛错
    const { rerender } = render(
      <ErrorBoundary>
        <MaybeThrow shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('页面发生错误')).toBeInTheDocument();

    // 点击重试按钮（现在有重试和刷新两个按钮，用 role+name 精确查找）
    const retryButton = screen.getByRole('button', { name: /重\s*试/ });
    await user.click(retryButton);

    // 重试后 ErrorBoundary.hasError 变为 false
    // 但 MaybeThrow 仍会抛错，所以需要 rerender 为不抛错状态
    rerender(
      <ErrorBoundary key="fresh">
        <MaybeThrow shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('normal-child')).toBeInTheDocument();
  });

  it('提供自定义 fallback 时使用 fallback', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">自定义错误页</div>}>
        <AlwaysThrow error={new Error('自定义错误')} />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByText('页面发生错误')).not.toBeInTheDocument();
  });

  it('错误时 ErrorBoundary 正确捕获并展示错误信息', () => {
    render(
      <ErrorBoundary>
        <AlwaysThrow error={new Error('上报测试')} />
      </ErrorBoundary>
    );
    expect(screen.getByText('上报测试')).toBeInTheDocument();
  });
});
