import { ImagePreview } from '../common/ImagePreview';
import type { GenerationRecord } from '../../types';

export function CandidateCard({ record, selected, onSelect, onAddToLibrary, onVariant }: { record: GenerationRecord; selected: boolean; onSelect: () => void; onAddToLibrary: () => void; onVariant: () => void }) {
  return (
    <div className={`nq-card`} onClick={onSelect} style={{ cursor: 'pointer', border: selected ? '1px solid var(--accent)' : undefined }}>
      <ImagePreview src={record.image_url} alt={record.user_prompt} style={{ width: '100%', height: 160 }} />
      <div style={{ padding: 'var(--sp-2)' }}>
        <div style={{ display: 'flex', gap: 'var(--sp-1)', marginBottom: 'var(--sp-1)' }}>
          <span className={`nq-tag nq-tag--${record.asset_type}`}>{record.asset_type}</span>
        </div>
        <div className="truncate" style={{ font: '400 11px var(--font)', color: 'var(--text-2)' }}>{record.user_prompt}</div>
        <div style={{ display: 'flex', gap: 'var(--sp-1)', marginTop: 'var(--sp-2)' }}>
          <button className="nq-btn nq-btn--sm nq-btn--accent" onClick={(e) => { e.stopPropagation(); onAddToLibrary(); }}>Add</button>
          <button className="nq-btn nq-btn--sm" onClick={(e) => { e.stopPropagation(); onVariant(); }}>Variant</button>
        </div>
      </div>
    </div>
  );
}
