import type { AssetType, AssetSubtype } from '../../types';

export function AssetTypeSelector({ value, subtype, onChange }: { value: AssetType; subtype: AssetSubtype | null; onChange: (type: AssetType, subtype: AssetSubtype | null) => void }) {
  return (
    <div>
      <div className="form-label" style={{ marginBottom: 'var(--sp-2)' }}>素材类型</div>
      <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
        {([['character', '角色'], ['tile', '图块']] as [AssetType, string][]).map(([type, label]) => (
          <button key={type} className={`nq-btn ${value === type ? 'nq-btn--accent' : ''}`} style={{ flex: 1 }}
            onClick={() => onChange(type, type === 'character' ? (subtype ?? 'animated_spritesheet') : null)}>
            {label}
          </button>
        ))}
      </div>
      {value === 'character' && (
        <div style={{ display: 'flex', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
          {([['animated_spritesheet', '动画精灵表'], ['static_image', '静态图片']] as [AssetSubtype, string][]).map(([st, label]) => (
            <button key={st} className={`nq-btn nq-btn--sm ${subtype === st ? 'nq-btn--accent' : ''}`} style={{ flex: 1 }}
              onClick={() => onChange(value, st)}>{label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
