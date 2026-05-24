import { useState, useEffect } from 'react';
import { styleApi } from '../../services/api';
import type { AssetType, AssetSubtype, GenerateParams, StyleProfile } from '../../types';

const MAP_SIZE_PRESETS: [number, number][] = [
  [512, 512], [1024, 1024], [1536, 1024], [2048, 2048], [2048, 1536],
];
const MAP_MIN = 256;
const MAP_MAX = 4096;

export function ParamPanel({ assetType, assetSubtype, params, onChange }: { assetType: AssetType; assetSubtype: AssetSubtype | null; params: GenerateParams; onChange: (p: GenerateParams) => void }) {
  const up = (partial: Partial<GenerateParams>) => onChange({ ...params, ...partial });
  const [styles, setStyles] = useState<StyleProfile[]>([]);
  const [customW, setCustomW] = useState(params.target_size[0] < 256 ? '' : String(params.target_size[0]));
  const [customH, setCustomH] = useState(params.target_size[1] < 256 ? '' : String(params.target_size[1]));
  const [customError, setCustomError] = useState('');

  useEffect(() => {
    styleApi.list().then(setStyles).catch(() => {});
  }, []);

  const applyCustomSize = () => {
    const w = Number(customW);
    const h = Number(customH);
    if (!w || !h || w <= 0 || h <= 0) {
      setCustomError('请输入有效的宽高');
      return;
    }
    if (w < MAP_MIN || h < MAP_MIN) {
      setCustomError(`最小尺寸为 ${MAP_MIN}×${MAP_MIN}`);
      return;
    }
    if (w > MAP_MAX || h > MAP_MAX) {
      setCustomError(`最大尺寸为 ${MAP_MAX}×${MAP_MAX}`);
      return;
    }
    setCustomError('');
    up({ target_size: [w, h] });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
      {/* 风格选择 */}
      <div className="form-row">
        <label className="form-label">风格</label>
        <select
          className="nq-select"
          value={params.style_id ?? ''}
          onChange={(e) => up({ style_id: e.target.value || undefined })}
          style={{ width: '100%' }}
        >
          <option value="">自动（使用项目默认）</option>
          {styles.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {/* 尺寸 — 非地图类型 */}
      {assetType !== 'map' && (
        <div className="form-row">
          <label className="form-label">尺寸</label>
          <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
            {([[16,16],[32,32],[64,64],[128,128],[256,256]] as [number,number][]).map(([w,h]) => (
              <button key={`${w}x${h}`} className={`nq-btn nq-btn--sm ${params.target_size[0]===w && params.target_size[1]===h ? 'nq-btn--accent' : ''}`}
                onClick={() => up({ target_size: [w, h] })}>{w}&times;{h}</button>
            ))}
          </div>
        </div>
      )}

      {/* 角色动画专属 */}
      {assetType === 'character' && assetSubtype === 'animated_spritesheet' && (
        <>
          <div className="form-row">
            <label className="form-label">方向数</label>
            <select className="nq-select" value={params.direction_count ?? 4} onChange={(e) => up({ direction_count: +e.target.value })} style={{ width: '100%' }}>
              <option value={1}>1</option><option value={2}>2（左右）</option><option value={4}>4</option><option value={8}>8</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">每方向帧数</label>
            <select className="nq-select" value={params.frame_count ?? 3} onChange={(e) => up({ frame_count: +e.target.value })} style={{ width: '100%' }}>
              <option value={2}>2</option><option value={3}>3</option><option value={4}>4</option><option value={6}>6</option><option value={8}>8</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">动作</label>
            <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
              {['idle','walk','attack','hurt','die'].map((a) => {
                const on = params.actions?.includes(a);
                return <button key={a} className={`nq-btn nq-btn--sm ${on ? 'nq-btn--accent' : ''}`} onClick={() => { const c = params.actions ?? []; up({ actions: on ? c.filter((x) => x !== a) : [...c, a] }); }}>{a}</button>;
              })}
            </div>
          </div>
        </>
      )}

      {/* 地图专属 */}
      {assetType === 'map' && (
        <div className="form-row">
          <label className="form-label">地图尺寸</label>
          <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap', marginBottom: 'var(--sp-2)' }}>
            {MAP_SIZE_PRESETS.map(([w, h]) => (
              <button key={`${w}x${h}`} className={`nq-btn nq-btn--sm ${params.target_size[0]===w && params.target_size[1]===h ? 'nq-btn--accent' : ''}`}
                onClick={() => { up({ target_size: [w, h] }); setCustomW(String(w)); setCustomH(String(h)); setCustomError(''); }}>
                {w}&times;{h}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 'var(--sp-1)', alignItems: 'center' }}>
            <input
              className="nq-input"
              type="number"
              value={customW}
              onChange={(e) => { setCustomW(e.target.value); setCustomError(''); }}
              placeholder="宽"
              style={{ width: '80px' }}
            />
            <span style={{ color: 'var(--text-3)', fontSize: '12px' }}>&times;</span>
            <input
              className="nq-input"
              type="number"
              value={customH}
              onChange={(e) => { setCustomH(e.target.value); setCustomError(''); }}
              placeholder="高"
              style={{ width: '80px' }}
            />
            <button className="nq-btn nq-btn--sm nq-btn--accent" onClick={applyCustomSize}>
              设置
            </button>
          </div>
          {customError && (
            <div style={{ color: 'var(--danger)', fontSize: '11px', marginTop: '4px' }}>{customError}</div>
          )}
          <div style={{ color: 'var(--text-3)', fontSize: '11px', marginTop: '4px' }}>
            范围 {MAP_MIN}～{MAP_MAX} px
          </div>
        </div>
      )}

      {/* 图块专属 */}
      {assetType === 'tile' && (
        <>
          <div className="form-row">
            <label className="form-label">地块类型</label>
            <select
              className="nq-select"
              value={params.terrain_type ?? ''}
              onChange={(e) => up({ terrain_type: e.target.value || undefined })}
              style={{ width: '100%' }}
            >
              <option value="">通用</option>
              <option value="grass">草地</option>
              <option value="dirt">泥土</option>
              <option value="sand">沙地</option>
              <option value="water">水面</option>
              <option value="stone">石地</option>
              <option value="ice">冰面</option>
              <option value="lava">岩浆</option>
              <option value="swamp">沼泽</option>
              <option value="wood">木质</option>
              <option value="metal">金属</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">边缘规则</label>
            <select className="nq-select" style={{ width: '100%' }}><option value="seamless">无缝拼接</option><option value="bordered">有边框</option></select>
          </div>
        </>
      )}
    </div>
  );
}
