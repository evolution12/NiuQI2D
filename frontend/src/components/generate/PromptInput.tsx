import { useRef } from 'react';

export function PromptInput({ value, onChange, onSubmit, disabled }: { value: string; onChange: (v: string) => void; onSubmit: () => void; disabled?: boolean }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (!disabled && value.trim()) onSubmit(); }
  };
  return (
    <div>
      <div className="form-label" style={{ marginBottom: 'var(--sp-1)' }}>Description</div>
      <textarea ref={ref} className="nq-input" value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={handleKey}
        disabled={disabled} placeholder="Describe the asset you want to generate..." rows={3} style={{ width: '100%', minHeight: 72 }} />
      <div style={{ font: '400 10px var(--font)', color: 'var(--text-3)', marginTop: 'var(--sp-1)' }}>Enter to submit, Shift+Enter for newline</div>
    </div>
  );
}
