import { useState } from 'react';
import type { CreateProjectRequest, StyleProfile } from '../../types';

export function ProjectCreateModal({ styles, onConfirm, onCancel }: { styles: StyleProfile[]; onConfirm: (d: CreateProjectRequest) => void; onCancel: () => void }) {
  const [name, setName] = useState('');
  const [styleId, setStyleId] = useState('');

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-panel">
        <div className="modal-header">
          <span className="modal-title">New Project</span>
        </div>
        <div className="modal-body">
          <div className="form-row">
            <label className="form-label">Name</label>
            <input className="nq-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Project name" autoFocus style={{ width: '100%' }} />
          </div>
          <div className="form-row">
            <label className="form-label">Default style (optional)</label>
            <select className="nq-select" value={styleId} onChange={(e) => setStyleId(e.target.value)} style={{ width: '100%' }}>
              <option value="">None</option>
              {styles.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <button className="nq-btn nq-btn--sm" onClick={onCancel}>Cancel</button>
          <button className="nq-btn nq-btn--sm nq-btn--accent" onClick={() => onConfirm({ name, style_id: styleId || null })} disabled={!name.trim()}>Create</button>
        </div>
      </div>
    </div>
  );
}
