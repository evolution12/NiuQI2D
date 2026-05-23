import { useEffect } from 'react';

interface ShortcutMap {
  [key: string]: () => void;
}

/**
 * 全局快捷键 Hook
 *
 * 支持的快捷键：
 * - Enter: 生成页提交（焦点在输入框时，非 Shift+Enter）
 * - Escape: 关闭弹窗/模态
 * - Ctrl+N: 新建项目
 * - Ctrl+E: 导出选中资产
 * - Delete: 删除选中资产
 */
export function useShortcuts(shortcuts: ShortcutMap) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // 忽略在输入框中的组合键（避免与正常输入冲突）
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // 构建快捷键标识
      const parts: string[] = [];
      if (e.ctrlKey || e.metaKey) parts.push('ctrl');
      if (e.shiftKey) parts.push('shift');
      if (e.altKey) parts.push('alt');
      parts.push(e.key.toLowerCase());
      const combo = parts.join('+');

      // 特殊处理 Enter：输入框中 Shift+Enter 允许换行
      if (e.key === 'Enter' && isInput && !e.shiftKey) {
        // 输入框中普通 Enter 由组件自行处理
        return;
      }

      // Escape 总是处理（关闭弹窗）
      if (e.key === 'Escape') {
        const action = shortcuts['escape'];
        if (action) {
          e.preventDefault();
          action();
        }
        return;
      }

      // 输入框中不触发其他快捷键
      if (isInput) return;

      const action = shortcuts[combo];
      if (action) {
        e.preventDefault();
        action();
      }
    };

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [shortcuts]);
}
