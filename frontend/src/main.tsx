import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/global.css';
import { initLogger, reportError } from './utils/logger';

// 初始化前端日志（生产环境关闭 console.debug/log）
initLogger();

// 全局未捕获错误
window.addEventListener('error', (event) => {
  reportError({
    message: event.message || '未知错误',
    stack: event.error?.stack,
    url: event.filename ? `${event.filename}:${event.lineno}` : undefined,
  });
});

// 全局未处理的 Promise rejection
window.addEventListener('unhandledrejection', (event) => {
  reportError({
    message: event.reason?.message || String(event.reason),
    stack: event.reason?.stack,
  });
});

createRoot(document.getElementById('root')!).render(<App />);
