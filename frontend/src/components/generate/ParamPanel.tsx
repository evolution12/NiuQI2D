import type { AssetType, AssetSubtype, GenerateParams } from '../../types';

export function ParamPanel({ assetType, assetSubtype, params, onChange }: { assetType: AssetType; assetSubtype: AssetSubtype | null; params: GenerateParams; onChange: (p: GenerateParams) => void }) {
  const up = (partial: Partial<GenerateParams>) => onChange({ ...params, ...partial });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
      {/* Size */}
      <div className="form-row">
        <label className="form-label">Size</label>
        <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
          {([[16,16],[32,32],[64,64],[128,128],[256,256]] as [number,number][]).map(([w,h]) => (
            <button key={`${w}x${h}`} className={`nq-btn nq-btn--sm ${params.target_size[0]===w && params.target_size[1]===h ? 'nq-btn--accent' : ''}`}
              onClick={() => up({ target_size: [w, h] })}>{w}&times;{h}</button>
          ))}
        </div>
      </div>

      {/* Character animated specific */}
      {assetType === 'character' && assetSubtype === 'animated_spritesheet' && (
        <>
          <div className="form-row">
            <label className="form-label">Directions</label>
            <select className="nq-select" value={params.direction_count ?? 4} onChange={(e) => up({ direction_count: +e.target.value })} style={{ width: '100%' }}>
              <option value={1}>1</option><option value={2}>2 (left/right)</option><option value={4}>4</option><option value={8}>8</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">Frames per direction</label>
            <select className="nq-select" value={params.frame_count ?? 3} onChange={(e) => up({ frame_count: +e.target.value })} style={{ width: '100%' }}>
              <option value={2}>2</option><option value={3}>3</option><option value={4}>4</option><option value={6}>6</option><option value={8}>8</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">Actions</label>
            <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
              {['idle','walk','attack','hurt','die'].map((a) => {
                const on = params.actions?.includes(a);
                return <button key={a} className={`nq-btn nq-btn--sm ${on ? 'nq-btn--accent' : ''}`} onClick={() => { const c = params.actions ?? []; up({ actions: on ? c.filter((x) => x !== a) : [...c, a] }); }}>{a}</button>;
              })}
            </div>
          </div>
        </>
      )}

      {/* Tile specific */}
      {assetType === 'tile' && (
        <div className="form-row">
          <label className="form-label">Edge rule</label>
          <select className="nq-select" style={{ width: '100%' }}><option value="seamless">Seamless</option><option value="bordered">Bordered</option></select>
        </div>
      )}
    </div>
  );
}
