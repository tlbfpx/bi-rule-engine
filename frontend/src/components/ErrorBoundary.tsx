import React from 'react';
import { Result, Button } from 'antd';
import { reportError } from '../utils/logger';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React 错误边界组件
 * - 捕获子组件树中的渲染错误
 * - 展示友好的错误页面（可自定义）
 * - 自动上报错误到后端
 */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    reportError({
      message: error.message,
      stack: error.stack,
    });
    // 开发环境输出到 console 辅助调试
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary]', error, info.componentStack);
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Result
          status="error"
          title="页面发生错误"
          subTitle={this.state.error?.message || '未知错误'}
          extra={
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              <Button type="primary" onClick={this.handleReset}>
                重试
              </Button>
              <Button onClick={() => window.location.reload()}>
                刷新页面
              </Button>
            </div>
          }
        />
      );
    }
    return this.props.children;
  }
}
