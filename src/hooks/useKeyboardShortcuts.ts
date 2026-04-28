'use client';

import { useEffect } from 'react';

interface ShortcutHandlers {
  onUndo?: () => void;
  onRedo?: () => void;
  onSave?: () => void;
  onResetCamera?: () => void;
  onToggleGrid?: () => void;
  onToggleSidebar?: () => void;
  onSwitchTab?: (index: number) => void;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      const isCtrl = e.ctrlKey || e.metaKey;

      // Ctrl+Z → Undo
      if (isCtrl && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handlers.onUndo?.();
        return;
      }

      // Ctrl+Shift+Z or Ctrl+Y → Redo
      if (isCtrl && ((e.key === 'z' && e.shiftKey) || e.key === 'y')) {
        e.preventDefault();
        handlers.onRedo?.();
        return;
      }

      // Ctrl+S → Save version
      if (isCtrl && e.key === 's') {
        e.preventDefault();
        handlers.onSave?.();
        return;
      }

      // Non-modifier shortcuts
      if (isCtrl || e.altKey) return;

      switch (e.key.toLowerCase()) {
        case 'r':
          handlers.onResetCamera?.();
          break;
        case 'g':
          handlers.onToggleGrid?.();
          break;
        case 's':
          handlers.onToggleSidebar?.();
          break;
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6':
          handlers.onSwitchTab?.(parseInt(e.key) - 1);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlers]);
}
