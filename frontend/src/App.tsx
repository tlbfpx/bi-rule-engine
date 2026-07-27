import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/Layout/AppLayout';
import RuleList from './pages/RuleList';
import LookupTables from './pages/LookupTables';
import TaskCenter from './pages/TaskCenter';
import DependencyDAG from './pages/DependencyDAG';
import DataSources from './pages/DataSources';
import TargetTables from './pages/TargetTables';
import ETLJobs from './pages/ETLJobs';
import RuleSetManager from './pages/RuleSetManager';
import RuleSetDetail from './pages/RuleSetDetail';
import { ErrorBoundary } from './components/ErrorBoundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

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
              <Routes>
                <Route element={<AppLayout />}>
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
            </HashRouter>
          </ErrorBoundary>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
