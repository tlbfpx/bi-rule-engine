import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

/** 路由守卫 — 未登录时重定向到 /login */
export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
