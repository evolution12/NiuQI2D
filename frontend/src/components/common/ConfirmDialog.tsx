import { useEffect, useCallback } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger, onConfirm, onCancel }: ConfirmDialogProps) {
  const handleKey = useCallback((e: KeyboardEvent) => { if (e.key === 'Escape') onCancel(); }, [onCancel]);
  useEffect(() => {
    if (open) { document.addEventListener('keydown', handleKey); return () => document.removeEventListener('keydown', handleKey); }
  }, [open, handleKey]);

  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-panel">
        <div className="modal-header">
          <span className="modal-title">{title}</span>
        </div>
        <div className="modal-body">
          <p style={{ font: '400 12px var(--font)', color: 'var(--text-2)', lineHeight: 1.6 }}>{message}</p>
        </div>
        <div className="modal-footer">
          <button className="nq-btn nq-btn--sm" onClick={onCancel}>{cancelLabel}</button>
          <button className={`nq-btn nq-btn--sm ${danger ? 'nq-btn--danger' : 'nq-btn--accent'}`} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
