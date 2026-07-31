import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { lazy, Suspense } from 'react';
import AppLayout from './components/Layout/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';

// 路由级代码分割，减小首屏 bundle 体积
const LoginPage = lazy(() => import('./pages/Login'));
const RuleSetManager = lazy(() => import('./pages/RuleSetManager'));
const RuleSetDetail = lazy(() => import('./pages/RuleSetDetail'));
const RuleList = lazy(() => import('./pages/RuleList'));
const LookupTables = lazy(() => import('./pages/LookupTables'));
const TaskCenter = lazy(() => import('./pages/TaskCenter'));
const DependencyDAG = lazy(() => import('./pages/DependencyDAG'));
const DataSources = lazy(() => import('./pages/DataSources'));
const TargetTables = lazy(() => import('./pages/TargetTables'));
const ETLJobs = lazy(() => import('./pages/ETLJobs'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  },
});

const PageLoading = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
    <Spin size="large" />
  </div>
);

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
          },
        }}
      >
        <AntApp>
          <ErrorBoundary>
            <HashRouter>
              <Suspense fallback={<PageLoading />}>
                <Routes>
                  {/* 公开路由 */}
                  <Route path="/login" element={<LoginPage />} />

                  {/* 受保护路由 — 需要 JWT 认证 */}
                  <Route
                    element={
                      <ProtectedRoute>
                        <AppLayout />
                      </ProtectedRoute>
                    }
                  >
                    <Route path="/rule-sets" element={<RuleSetManager />} />
                    <Route path="/rule-sets/:id" element={<RuleSetDetail />} />
                    <Route path="/rules" element={<RuleList />} />
                    <Route path="/lookup-tables" element={<LookupTables />} />
                    <Route path="/tasks" element={<TaskCenter />} />
                    <Route path="/dag" element={<DependencyDAG />} />
                    <Route path="/data-sources" element={<DataSources />} />
                    <Route path="/target-tables" element={<TargetTables />} />
                    <Route path="/etl-jobs" element={<ETLJobs />} />
                    <Route path="*" element={<Navigate to="/rule-sets" replace />} />
                  </Route>
                </Routes>
              </Suspense>
            </HashRouter>
          </ErrorBoundary>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
