import { useState } from 'react';
import type { CreateProjectRequest, StyleProfile } from '../../types';
import { compactStyleOptions, getStyleDisplayName } from '../../utils/styleOptions';

export function ProjectCreateModal({ styles, onConfirm, onCancel }: { styles: StyleProfile[]; onConfirm: (d: CreateProjectRequest) => void; onCancel: () => void }) {
  const [name, setName] = useState('');
  const [styleId, setStyleId] = useState('');

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-panel">
        <div className="modal-header">
          <span className="modal-title">新建项目</span>
        </div>
        <div className="modal-body">
          <div className="form-row">
            <label className="form-label">名称</label>
            <input className="nq-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="输入项目名称" autoFocus style={{ width: '100%' }} />
          </div>
          <div className="form-row">
            <label className="form-label">默认风格（可选）</label>
            <select className="nq-select" value={styleId} onChange={(e) => setStyleId(e.target.value)} style={{ width: '100%' }}>
              <option value="">无</option>
              {compactStyleOptions(styles).map((s) => <option key={s.id} value={s.id}>{getStyleDisplayName(s)}</option>)}
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <button className="nq-btn nq-btn--sm" onClick={onCancel}>取消</button>
          <button className="nq-btn nq-btn--sm nq-btn--accent" onClick={() => onConfirm({ name, style_id: styleId || null })} disabled={!name.trim()}>创建</button>
        </div>
      </div>
    </div>
  );
}
