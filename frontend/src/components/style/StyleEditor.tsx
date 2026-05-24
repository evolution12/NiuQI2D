import { useState } from 'react';
import type { ArtStyle, Perspective, CreateStyleRequest } from '../../types';

interface StyleEditorProps {
  initial?: CreateStyleRequest & { id?: string; extra_params?: Record<string, unknown> | null };
  onSave: (data: CreateStyleRequest) => void;
  onCancel: () => void;
}

const artStyleOptions: { value: ArtStyle; label: string }[] = [
  { value: 'pixel', label: '像素风' },
  { value: 'hand_drawn', label: '手绘风' },
  { value: 'cartoon', label: '卡通风' },
  { value: 'realistic', label: '写实风' },
  { value: 'custom', label: '自定义' },
];

const perspectiveOptions: { value: Perspective; label: string }[] = [
  { value: 'top_down', label: '俯视' },
  { value: 'side_scroller', label: '横版' },
  { value: 'isometric', label: '等距' },
];

export function StyleEditor({ initial, onSave, onCancel }: StyleEditorProps) {
  const [name, setName] = useState(initial?.name ?? '');
  const [artStyle, setArtStyle] = useState<ArtStyle>(initial?.art_style ?? 'pixel');
  const [width, setWidth] = useState(initial?.default_size?.w ?? 64);
  const [height, setHeight] = useState(initial?.default_size?.h ?? 64);
  const [perspective, setPerspective] = useState<Perspective>(
    initial?.perspective ?? 'top_down',
  );
  const [colorPalette, setColorPalette] = useState(
    initial?.color_palette?.join(', ') ?? '',
  );
  const [extraParams, setExtraParams] = useState(
    initial?.extra_params ? JSON.stringify(initial.extra_params, null, 2) : '',
  );

  const handleSave = () => {
    if (!name.trim()) return;
    const parsedParams: Record<string, unknown> | null = (() => {
      if (!extraParams.trim()) return null;
      try { return JSON.parse(extraParams); }
      catch { return null; }
    })();
    onSave({
      name: name.trim(),
      art_style: artStyle,
      default_size: { w: width, h: height },
      perspective,
      color_palette: colorPalette
        ? colorPalette.split(',').map((c) => c.trim()).filter(Boolean)
        : null,
      extra_params: parsedParams,
    });
  };

  return (
    <div className="modal-body">
      <div className="modal-header">
        <span className="modal-title">
          {initial?.id ? '编辑风格' : '创建风格'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        <div className="form-row">
          <label className="form-label">名称</label>
          <input
            className="nq-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="风格名称"
            style={{ width: '100%' }}
          />
        </div>

        <div className="form-row">
          <label className="form-label">画风</label>
          <select
            className="nq-select"
            value={artStyle}
            onChange={(e) => setArtStyle(e.target.value as ArtStyle)}
            style={{ width: '100%' }}
          >
            {artStyleOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <label className="form-label">视角</label>
          <select
            className="nq-select"
            value={perspective}
            onChange={(e) => setPerspective(e.target.value as Perspective)}
            style={{ width: '100%' }}
          >
            {perspectiveOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <label className="form-label">色板（逗号分隔 Hex 值）</label>
          <input
            className="nq-input"
            value={colorPalette}
            onChange={(e) => setColorPalette(e.target.value)}
            placeholder="#2d1b00, #4a8c3f, ..."
            style={{ width: '100%' }}
          />
        </div>

        <div className="form-row">
          <label className="form-label">额外参数（JSON，可选）</label>
          <textarea
            className="nq-input"
            value={extraParams}
            onChange={(e) => setExtraParams(e.target.value)}
            placeholder='{"color_count": 16, "outline": true}'
            style={{ width: '100%', minHeight: '80px', resize: 'vertical' }}
            spellCheck={false}
          />
        </div>
      </div>

      <div className="modal-footer" style={{ marginTop: 'var(--sp-3)' }}>
        <button className="nq-btn nq-btn--sm" onClick={onCancel}>取消</button>
        <button className="nq-btn nq-btn--sm nq-btn--accent" onClick={handleSave} disabled={!name.trim()}>
          保存
        </button>
      </div>
    </div>
  );
}
