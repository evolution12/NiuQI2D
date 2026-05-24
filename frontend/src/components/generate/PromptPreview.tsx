import { useState } from 'react';

export function PromptPreview({ prompt }: { prompt: string }) {
  const [open, setOpen] = useState(false);
  if (!prompt) return null;
  return (
    <div className="nq-section" style={{ padding: 0, overflow: 'hidden' }}>
      <button onClick={() => setOpen(!open)} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--sp-2) var(--sp-3)', background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', font: '500 11px var(--font)' }}>
        <span>优化后的提示词</span>
        <span>{open ? '\u25B2' : '\u25BC'}</span>
      </button>
      {open && (
        <pre style={{ padding: '0 var(--sp-3) var(--sp-3)', font: '400 11px var(--mono)', color: 'var(--text-2)', lineHeight: 1.6, maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
          {prompt}
        </pre>
      )}
    </div>
  );
}
