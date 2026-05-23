import type { GenerationRecord } from '../../types';
import { CandidateCard } from './CandidateCard';
import { EmptyState } from '../common/EmptyState';

export function CandidateGrid({ records, optimizedPrompt, selectedId, onSelect, onAddToLibrary, onRetry, onVariant }: { records: GenerationRecord[]; optimizedPrompt: string; selectedId: string | null; onSelect: (id: string) => void; onAddToLibrary: (id: string) => void; onRetry: () => void; onVariant: (id: string) => void }) {
  if (!records.length && !optimizedPrompt) {
    return <EmptyState title="Enter a description to start" description="Pick asset type, set parameters, and generate" />;
  }
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-3)' }}>
        <span style={{ font: '500 12px var(--font)', color: 'var(--text-2)' }}>Candidates ({records.length})</span>
        <button className="nq-btn nq-btn--sm" onClick={onRetry}>Retry</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--sp-3)' }}>
        {records.map((r) => (
          <CandidateCard key={r.id} record={r} selected={r.id === selectedId} onSelect={() => onSelect(r.id)} onAddToLibrary={() => onAddToLibrary(r.id)} onVariant={() => onVariant(r.id)} />
        ))}
      </div>
    </div>
  );
}
