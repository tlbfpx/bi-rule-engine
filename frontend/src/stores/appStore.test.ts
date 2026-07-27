import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '../stores/appStore';

describe('appStore (Zustand)', () => {
  beforeEach(() => {
    // 重置 store 到初始状态
    useAppStore.setState({ sidebarCollapsed: false });
  });

  describe('初始状态', () => {
    it('sidebarCollapsed 默认为 false', () => {
      expect(useAppStore.getState().sidebarCollapsed).toBe(false);
    });
  });

  describe('toggleSidebar', () => {
    it('从 false 切换到 true', () => {
      useAppStore.getState().toggleSidebar();
      expect(useAppStore.getState().sidebarCollapsed).toBe(true);
    });

    it('从 true 切换回 false', () => {
      useAppStore.setState({ sidebarCollapsed: true });
      useAppStore.getState().toggleSidebar();
      expect(useAppStore.getState().sidebarCollapsed).toBe(false);
    });

    it('多次切换状态正确交替', () => {
      const store = useAppStore.getState;
      store().toggleSidebar();
      expect(store().sidebarCollapsed).toBe(true);
      store().toggleSidebar();
      expect(store().sidebarCollapsed).toBe(false);
      store().toggleSidebar();
      expect(store().sidebarCollapsed).toBe(true);
      store().toggleSidebar();
      expect(store().sidebarCollapsed).toBe(false);
    });
  });

  describe('通过 getState 访问', () => {
    it('能获取 sidebarCollapsed 状态', () => {
      expect(useAppStore.getState().sidebarCollapsed).toBe(false);
    });

    it('能获取 toggleSidebar 函数', () => {
      expect(typeof useAppStore.getState().toggleSidebar).toBe('function');
    });

    it('能通过 setState 直接设置状态', () => {
      useAppStore.setState({ sidebarCollapsed: true });
      expect(useAppStore.getState().sidebarCollapsed).toBe(true);
    });

    it('setState 不影响 toggleSidebar 函数引用', () => {
      const toggle = useAppStore.getState().toggleSidebar;
      useAppStore.setState({ sidebarCollapsed: true });
      toggle();
      expect(useAppStore.getState().sidebarCollapsed).toBe(false);
    });
  });
});
